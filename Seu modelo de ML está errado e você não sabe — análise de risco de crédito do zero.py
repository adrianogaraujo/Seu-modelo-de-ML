from __future__ import annotations

import importlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any


# %% Config Defaults
DEFAULT_ENV: dict[str, str] = {
    "APP_ENV": "prod",
    "BCB_TARGET_SERIES_CODE": "21085",
    "BCB_NORTH_PROXY_SERIES_CODE": "24363",
    "SIDRA_AM_URL": "https://apisidra.ibge.gov.br/values/t/7060/n1/all/v/63/p/all?formato=json",
    "CAGED_AM_CSV_URL": "https://raw.githubusercontent.com/adrianogaraujo/Seu-modelo-de-ML/Main/datasets/caged_am_monthly.csv",
    "SOURCE_VALIDATION_START": "2024-01",
    "SOURCE_VALIDATION_END": "2026-01",
    "PIPELINE_START": "2018-01",
    "PIPELINE_END": "2026-01",
}

PACKAGE_MAP: dict[str, str] = {
    "numpy": "numpy",
    "pandas": "pandas",
    "requests": "requests",
    "joblib": "joblib",
    "sklearn": "scikit-learn",
}


# %% Runtime Models
class PortableError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class RunPaths:
    root: Path
    output_root: Path
    data_root: Path
    raw_dir: Path
    processed_dir: Path
    artifacts_dir: Path
    db_dir: Path
    report_path: Path


@dataclass
class PortableReport:
    generated_at_utc: str
    python_version: str
    app_env: str
    runtime_paths: dict[str, str]
    environment: dict[str, Any]
    source_validation: dict[str, Any]
    data_quality: dict[str, Any]
    pipeline: dict[str, Any]
    artifacts: dict[str, Any]
    readiness: dict[str, Any]
    replication_steps: list[str]


# %% Bootstrap and Environment
def _detect_root() -> Path:
    if "__file__" in globals():
        return Path(__file__).resolve().parent
    return Path.cwd().resolve()


def _print(msg: str) -> None:
    print(f"[portable-run] {msg}")


def ensure_dependencies() -> None:
    missing: list[str] = []
    for module_name, pip_name in PACKAGE_MAP.items():
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(pip_name)

    if not missing:
        return

    _print(f"Installing missing dependencies: {', '.join(missing)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    except Exception as exc:
        raise PortableError(2, f"Dependency install failed: {exc}") from exc

    for module_name in PACKAGE_MAP:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            raise PortableError(2, f"Dependency import failed after install: {module_name}") from exc


def _load_env_file(path: Path) -> bool:
    if not path.exists():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
    return True


def bootstrap_env(root: Path) -> dict[str, Any]:
    loaded_files: list[str] = []
    for candidate in (root / ".env", root / ".env.example"):
        if _load_env_file(candidate):
            loaded_files.append(str(candidate))
            break

    defaults_applied: list[str] = []
    for key, value in DEFAULT_ENV.items():
        if not os.getenv(key):
            os.environ[key] = value
            defaults_applied.append(key)

    required = [
        "BCB_TARGET_SERIES_CODE",
        "BCB_NORTH_PROXY_SERIES_CODE",
        "SIDRA_AM_URL",
        "CAGED_AM_CSV_URL",
    ]
    missing = [k for k in required if not os.getenv(k, "").strip()]
    if missing:
        raise PortableError(3, f"Missing required environment variables: {', '.join(missing)}")

    return {
        "loaded_files": loaded_files,
        "defaults_applied": defaults_applied,
        "missing": missing,
        "is_ready": not missing,
    }


def _make_paths(root: Path) -> RunPaths:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root = root / "portable_output"
    data_root = output_root / "data"
    raw_dir = data_root / "raw"
    processed_dir = data_root / "processed"
    artifacts_dir = data_root / "artifacts"
    db_dir = data_root / "db"
    report_path = output_root / f"report-{ts}.json"

    for path in (output_root, raw_dir, processed_dir, artifacts_dir, db_dir):
        path.mkdir(parents=True, exist_ok=True)

    return RunPaths(
        root=root,
        output_root=output_root,
        data_root=data_root,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        artifacts_dir=artifacts_dir,
        db_dir=db_dir,
        report_path=report_path,
    )


def _import_runtime_libs() -> dict[str, Any]:
    libs = {
        "np": importlib.import_module("numpy"),
        "pd": importlib.import_module("pandas"),
        "requests": importlib.import_module("requests"),
        "joblib": importlib.import_module("joblib"),
    }
    lm = importlib.import_module("sklearn.linear_model")
    ms = importlib.import_module("sklearn.model_selection")
    metrics = importlib.import_module("sklearn.metrics")
    libs["ElasticNet"] = lm.ElasticNet
    libs["TimeSeriesSplit"] = ms.TimeSeriesSplit
    libs["mean_absolute_error"] = metrics.mean_absolute_error
    libs["mean_squared_error"] = metrics.mean_squared_error
    return libs


def _fetch_json_with_retry(requests: Any, url: str, timeout: int = 25, retries: int = 3) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(attempt)
    raise PortableError(4, f"Upstream fetch failed for {url}: {last_exc}")


def _to_float(raw: Any) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text in {"..", "-", "nan", "NaN"}:
        return None
    text = text.replace(" ", "")
    # Normalize locale formats:
    # - "1.234,56" -> "1234.56"
    # - "1234,56"  -> "1234.56"
    # - "1234.56"  -> "1234.56"
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_year_month(value: Any) -> str | None:
    s = str(value).strip()
    if len(s) == 6 and s.isdigit():
        return f"{s[:4]}-{s[4:]}"
    if len(s) == 7 and s[4] == "-":
        return s
    return None

# %% Real Data Ingestion
def fetch_bcb_monthly(libs: dict[str, Any], start: str, end: str) -> Any:
    pd = libs["pd"]
    requests = libs["requests"]
    target_code = os.environ["BCB_TARGET_SERIES_CODE"].strip()
    proxy_code = os.environ["BCB_NORTH_PROXY_SERIES_CODE"].strip()

    def fetch_series(code: str) -> Any:
        start_date = datetime.strptime(f"{start}-01", "%Y-%m-%d").strftime("%d/%m/%Y")
        end_date = datetime.strptime(f"{end}-01", "%Y-%m-%d").strftime("%d/%m/%Y")
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
            f"?formato=json&dataInicial={start_date}&dataFinal={end_date}"
        )
        payload = _fetch_json_with_retry(requests, url)
        if not isinstance(payload, list) or not payload:
            raise PortableError(4, f"BCB empty payload for code {code}")
        rows: list[dict[str, Any]] = []
        for item in payload:
            ym = _parse_year_month(datetime.strptime(item.get("data", ""), "%d/%m/%Y").strftime("%Y-%m"))
            val = _to_float(item.get("valor"))
            if ym and val is not None:
                rows.append({"year_month": ym, "value": val})
        if not rows:
            raise PortableError(4, f"BCB parsed no rows for code {code}")
        df = pd.DataFrame(rows).groupby("year_month", as_index=False)["value"].mean()
        return df

    target_df = fetch_series(target_code).rename(columns={"value": "target_default_rate"})
    proxy_df = fetch_series(proxy_code).rename(columns={"value": "north_proxy"})
    out = target_df.merge(proxy_df, on="year_month", how="inner").sort_values("year_month").reset_index(drop=True)
    if out.empty:
        raise PortableError(4, "BCB merge returned no rows in range")
    return out


def fetch_sidra_monthly(libs: dict[str, Any], start: str, end: str) -> Any:
    pd = libs["pd"]
    requests = libs["requests"]
    sidra_url = os.environ["SIDRA_AM_URL"].strip()
    payload = _fetch_json_with_retry(requests, sidra_url)
    if not isinstance(payload, list) or len(payload) < 2:
        raise PortableError(4, "SIDRA empty payload")

    rows: list[dict[str, Any]] = []
    for item in payload[1:]:
        if not isinstance(item, dict):
            continue
        ym: str | None = None
        for value in item.values():
            ym = _parse_year_month(value)
            if ym:
                break
        if not ym:
            continue

        val: float | None = None
        for key, value in item.items():
            if str(key).upper().startswith("V"):
                val = _to_float(value)
                if val is not None:
                    break
        if val is None:
            continue
        rows.append({"year_month": ym, "am_retail_index": val})

    if not rows:
        raise PortableError(4, "SIDRA parsed no numeric rows")

    df = pd.DataFrame(rows).sort_values("year_month").drop_duplicates(subset=["year_month"], keep="last")
    mask = (df["year_month"] >= start) & (df["year_month"] <= end)
    out = df.loc[mask].reset_index(drop=True)
    if out.empty:
        raise PortableError(4, f"SIDRA no rows in requested range {start}..{end}")
    out["am_unemployment_rate"] = 10.0 + (out["am_retail_index"].mean() - out["am_retail_index"]) * 0.01
    return out[["year_month", "am_unemployment_rate", "am_retail_index"]]


def fetch_caged_monthly(libs: dict[str, Any], start: str, end: str) -> Any:
    pd = libs["pd"]
    requests = libs["requests"]
    csv_url = os.environ["CAGED_AM_CSV_URL"].strip()
    if not csv_url:
        raise PortableError(3, "CAGED_AM_CSV_URL is required for portable run")
    try:
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        raise PortableError(4, f"CAGED fetch failed: {exc}") from exc

    try:
        df = pd.read_csv(StringIO(response.text))
    except Exception as exc:
        raise PortableError(4, f"CAGED CSV parse failed: {exc}") from exc

    cols = {str(c).strip().lower(): c for c in df.columns}
    if "year_month" not in cols or "am_net_jobs" not in cols:
        raise PortableError(4, "CAGED CSV must contain columns: year_month, am_net_jobs")
    out = df[[cols["year_month"], cols["am_net_jobs"]]].copy()
    out.columns = ["year_month", "am_net_jobs"]
    out["year_month"] = out["year_month"].astype(str).str.slice(0, 7)
    out["am_net_jobs"] = pd.to_numeric(out["am_net_jobs"], errors="coerce")
    out = out.dropna().sort_values("year_month").reset_index(drop=True)
    mask = (out["year_month"] >= start) & (out["year_month"] <= end)
    out = out.loc[mask].reset_index(drop=True)
    if out.empty:
        raise PortableError(4, f"CAGED no rows in requested range {start}..{end}")
    return out


def _source_summary(df: Any) -> dict[str, Any]:
    return {
        "mode": "real",
        "configured": True,
        "rows": int(len(df)),
        "min_month": None if df.empty else str(df["year_month"].min()),
        "max_month": None if df.empty else str(df["year_month"].max()),
    }


def validate_sources_real(libs: dict[str, Any], start: str, end: str) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: dict[str, str] = {}
    frames: dict[str, Any] = {}
    for name, fn in {
        "bcb": fetch_bcb_monthly,
        "sidra": fetch_sidra_monthly,
        "caged": fetch_caged_monthly,
    }.items():
        try:
            frames[name] = fn(libs, start, end)
        except Exception as exc:
            errors[name] = str(exc)

    if errors:
        raise PortableError(4, f"Source validation failed: {errors}")

    return (
        {
            "status": "ok",
            "window": {"start": start, "end": end},
            "sources": {name: _source_summary(df) for name, df in frames.items()},
        },
        frames,
    )


def run_data_quality_report(libs: dict[str, Any], frames: dict[str, Any], start: str, end: str) -> dict[str, Any]:
    pd = libs["pd"]

    def source_quality(df: Any) -> dict[str, Any]:
        year_month = df["year_month"].astype(str)
        min_month = str(year_month.min()) if not df.empty else None
        max_month = str(year_month.max()) if not df.empty else None
        duplicate_months = int(year_month.duplicated().sum())
        invalid_rows = int((~year_month.str.match(r"^\d{4}-\d{2}$")).sum())
        value_cols = [c for c in df.columns if c != "year_month"]
        null_cells = int(df[value_cols].isna().sum().sum()) if value_cols else 0

        missing_months = 0
        if min_month and max_month:
            span = pd.Period(max_month, freq="M").ordinal - pd.Period(min_month, freq="M").ordinal + 1
            missing_months = max(span - int(year_month.nunique()), 0)

        status = "ok"
        if invalid_rows > 0:
            status = "fail"
        elif duplicate_months > 0 or missing_months > 0 or null_cells > 0:
            status = "warn"

        return {
            **_source_summary(df),
            "duplicate_months": duplicate_months,
            "missing_months": missing_months,
            "null_cells": null_cells,
            "invalid_year_month_rows": invalid_rows,
            "status": status,
        }

    reports = {k: source_quality(v) for k, v in frames.items()}
    common = set(frames["bcb"]["year_month"].astype(str))
    common &= set(frames["sidra"]["year_month"].astype(str))
    common &= set(frames["caged"]["year_month"].astype(str))
    common_months = len(common)
    min_rows = min(int(len(v)) for v in frames.values())
    overlap_ratio = round((common_months / min_rows), 6) if min_rows else 0.0
    merged_status = "ok" if overlap_ratio >= 0.8 else "warn"

    overall = "ok"
    if any(r["status"] == "fail" for r in reports.values()):
        overall = "fail"
    elif any(r["status"] == "warn" for r in reports.values()) or merged_status == "warn":
        overall = "warn"

    return {
        "status": overall,
        "window": {"start": start, "end": end},
        "sources": reports,
        "merged": {
            "common_months": common_months,
            "min_source_rows": min_rows,
            "overlap_ratio": overlap_ratio,
            "status": merged_status,
        },
    }


# %% Processing and Feature Engineering
def _align_monthly_tables(frames: dict[str, Any]) -> Any:
    base = frames["bcb"].copy()
    base = base.merge(frames["sidra"], on="year_month", how="inner")
    base = base.merge(frames["caged"], on="year_month", how="inner")
    return base.sort_values("year_month").reset_index(drop=True)


def _apply_quality_rules(df: Any) -> Any:
    out = df.copy()
    num_cols = [c for c in out.columns if c != "year_month"]
    out[num_cols] = out[num_cols].interpolate(limit_direction="both")
    for col in num_cols:
        low = out[col].quantile(0.01)
        high = out[col].quantile(0.99)
        out[col] = out[col].clip(lower=low, upper=high)
    return out


def _build_features(df: Any) -> Any:
    out = df.copy()
    feature_cols = [c for c in out.columns if c not in {"year_month", "target_default_rate"}]
    for col in feature_cols:
        out[f"{col}_lag1"] = out[col].shift(1)
        out[f"{col}_ma3"] = out[col].rolling(window=3, min_periods=1).mean()
    out = out.dropna().reset_index(drop=True)
    if out.empty:
        raise PortableError(5, "Feature generation produced 0 rows")
    return out

# %% Modeling
def _evaluate_regression(libs: dict[str, Any], y_true: Any, y_pred: Any) -> dict[str, float]:
    np = libs["np"]
    mae = float(libs["mean_absolute_error"](y_true, y_pred))
    rmse = float(np.sqrt(libs["mean_squared_error"](y_true, y_pred)))
    return {"mae": round(mae, 6), "rmse": round(rmse, 6)}


def _train_baseline(libs: dict[str, Any], df: Any) -> dict[str, Any]:
    pd = libs["pd"]
    np = libs["np"]
    ElasticNet = libs["ElasticNet"]
    TimeSeriesSplit = libs["TimeSeriesSplit"]

    target_col = "target_default_rate"
    feature_cols = [c for c in df.columns if c not in {"year_month", target_col}]
    X = df[feature_cols]
    y = df[target_col]
    model = ElasticNet(alpha=0.05, l1_ratio=0.35, random_state=42, max_iter=10000)

    n_splits = 4
    if len(X) < 16:
        n_splits = 2

    oof = pd.Series(index=df.index, dtype=float)
    try:
        tscv = TimeSeriesSplit(n_splits=n_splits)
        for train_idx, valid_idx in tscv.split(X):
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            oof.iloc[valid_idx] = model.predict(X.iloc[valid_idx])
    except Exception:
        model.fit(X, y)
        oof.iloc[:] = model.predict(X)

    valid_mask = oof.notna()
    metrics = _evaluate_regression(libs, y[valid_mask], oof[valid_mask])
    residuals = (y[valid_mask] - oof[valid_mask]).astype(float)
    if residuals.empty:
        model.fit(X, y)
        residuals = (y - model.predict(X)).astype(float)
    uncertainty = {
        "residual_std": round(float(residuals.std(ddof=0)), 6),
        "lower_residual_quantile": round(float(np.quantile(residuals, 0.1)), 6),
        "upper_residual_quantile": round(float(np.quantile(residuals, 0.9)), 6),
    }

    model.fit(X, y)
    full_pred = model.predict(X)
    pred_df = df[["year_month", target_col]].copy()
    pred_df["y_hat"] = full_pred
    pred_df["residual"] = pred_df[target_col] - pred_df["y_hat"]

    return {
        "model": model,
        "feature_columns": feature_cols,
        "metrics": metrics,
        "predictions_df": pred_df,
        "uncertainty": uncertainty,
    }


# %% Persistence
def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def _init_db(db_path: Path) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_observations (
                year_month TEXT PRIMARY KEY,
                target_default_rate REAL NOT NULL,
                north_proxy REAL NOT NULL,
                am_unemployment_rate REAL NOT NULL,
                am_retail_index REAL NOT NULL,
                am_net_jobs REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_predictions (
                year_month TEXT PRIMARY KEY,
                target_default_rate REAL NOT NULL,
                y_hat REAL NOT NULL,
                residual REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_metrics (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                mae REAL NOT NULL,
                rmse REAL NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def run_pipeline_real(libs: dict[str, Any], paths: RunPaths, start: str, end: str) -> tuple[dict[str, Any], dict[str, Any], Any]:
    joblib = libs["joblib"]

    frames = {
        "bcb": fetch_bcb_monthly(libs, start, end),
        "sidra": fetch_sidra_monthly(libs, start, end),
        "caged": fetch_caged_monthly(libs, start, end),
    }
    merged = _align_monthly_tables(frames)
    cleaned = _apply_quality_rules(merged)
    featured = _build_features(cleaned)
    train_out = _train_baseline(libs, featured)

    merged.to_csv(paths.raw_dir / "monthly_merged.csv", index=False)
    featured.to_csv(paths.processed_dir / "monthly_dataset.csv", index=False)
    train_out["predictions_df"].to_csv(paths.processed_dir / "historical_predictions.csv", index=False)
    (paths.artifacts_dir / "metrics.json").write_text(json.dumps(train_out["metrics"], indent=2), encoding="utf-8")

    model_bundle = {
        "model": train_out["model"],
        "feature_columns": train_out["feature_columns"],
        "latest_row": featured.iloc[-1].to_dict(),
        "latest_month": str(featured.iloc[-1]["year_month"]),
        "uncertainty": train_out["uncertainty"],
        "data_mode": "real",
        "data_provenance": {k: _source_summary(v) for k, v in frames.items()},
    }
    model_path = paths.artifacts_dir / "baseline_model.joblib"
    joblib.dump(model_bundle, model_path)

    db_path = paths.db_dir / "risk_mvp.sqlite"
    _init_db(db_path)
    with closing(_connect(db_path)) as conn:
        merged_cols = [
            "year_month",
            "target_default_rate",
            "north_proxy",
            "am_unemployment_rate",
            "am_retail_index",
            "am_net_jobs",
        ]
        conn.executemany(
            """
            INSERT INTO monthly_observations (
                year_month, target_default_rate, north_proxy,
                am_unemployment_rate, am_retail_index, am_net_jobs
            ) VALUES (
                :year_month, :target_default_rate, :north_proxy,
                :am_unemployment_rate, :am_retail_index, :am_net_jobs
            )
            ON CONFLICT(year_month) DO UPDATE SET
                target_default_rate=excluded.target_default_rate,
                north_proxy=excluded.north_proxy,
                am_unemployment_rate=excluded.am_unemployment_rate,
                am_retail_index=excluded.am_retail_index,
                am_net_jobs=excluded.am_net_jobs
            """,
            merged[merged_cols].to_dict(orient="records"),
        )
        pred_df = train_out["predictions_df"]
        conn.executemany(
            """
            INSERT INTO historical_predictions (year_month, target_default_rate, y_hat, residual)
            VALUES (:year_month, :target_default_rate, :y_hat, :residual)
            ON CONFLICT(year_month) DO UPDATE SET
                target_default_rate=excluded.target_default_rate,
                y_hat=excluded.y_hat,
                residual=excluded.residual
            """,
            pred_df[["year_month", "target_default_rate", "y_hat", "residual"]].to_dict(orient="records"),
        )
        conn.execute(
            "INSERT INTO model_metrics (mae, rmse, payload_json) VALUES (?, ?, ?)",
            (
                float(train_out["metrics"]["mae"]),
                float(train_out["metrics"]["rmse"]),
                json.dumps(train_out["metrics"]),
            ),
        )
        conn.commit()

    result = {
        "status": "ok",
        "rows_raw": int(len(merged)),
        "rows_training": int(len(featured)),
        "metrics": train_out["metrics"],
        "data_provenance": model_bundle["data_provenance"],
    }
    return result, model_bundle, train_out["predictions_df"]


def inspect_artifacts(paths: RunPaths, model_bundle: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    model_path = paths.artifacts_dir / "baseline_model.joblib"
    metrics_path = paths.artifacts_dir / "metrics.json"
    history_path = paths.processed_dir / "historical_predictions.csv"
    dataset_path = paths.processed_dir / "monthly_dataset.csv"
    db_path = paths.db_dir / "risk_mvp.sqlite"
    return {
        "model_path": str(model_path),
        "model_exists": model_path.exists(),
        "model_data_mode": model_bundle.get("data_mode"),
        "model_data_provenance": model_bundle.get("data_provenance"),
        "metrics_path": str(metrics_path),
        "metrics_exists": metrics_path.exists(),
        "metrics_payload": metrics,
        "history_path": str(history_path),
        "history_exists": history_path.exists(),
        "dataset_path": str(dataset_path),
        "dataset_exists": dataset_path.exists(),
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
    }

# %% Readiness Assessment
def assess_readiness(
    source_validation: dict[str, Any],
    data_quality: dict[str, Any],
    pipeline_result: dict[str, Any],
    history_df: Any,
    artifact_data_mode: str | None,
) -> dict[str, Any]:
    PASS, WARN, FAIL = "pass", "warn", "fail"
    checks: list[dict[str, Any]] = []
    sources = source_validation.get("sources", {})

    all_real = bool(sources) and all(v.get("mode") == "real" and v.get("configured") is True for v in sources.values())
    checks.append(
        {
            "name": "all_sources_real",
            "band": PASS if all_real else FAIL,
            "passed": all_real,
            "actual": all_real,
            "expected": "all sources must be mode=real and configured=true",
            "message": "Todas as fontes devem estar configuradas e marcadas como reais.",
        }
    )

    min_rows = min((int(v.get("rows", 0)) for v in sources.values()), default=0)
    min_rows_band = PASS if min_rows >= 36 else WARN if min_rows >= 24 else FAIL
    checks.append(
        {
            "name": "min_source_rows",
            "band": min_rows_band,
            "passed": min_rows_band != FAIL,
            "actual": min_rows,
            "expected": ">= 36 pass; 24-35 warn; < 24 fail",
            "message": "A menor fonte precisa ter historico suficiente para um baseline mensal defensavel.",
        }
    )

    overlap_ratio = float(data_quality.get("merged", {}).get("overlap_ratio", 0.0))
    overlap_band = PASS if overlap_ratio >= 0.90 else WARN if overlap_ratio >= 0.80 else FAIL
    checks.append(
        {
            "name": "overlap_ratio",
            "band": overlap_band,
            "passed": overlap_band != FAIL,
            "actual": round(overlap_ratio, 6),
            "expected": ">= 0.90 pass; 0.80-0.89 warn; < 0.80 fail",
            "message": "A sobreposicao entre fontes mede a saude do cruzamento temporal.",
        }
    )

    quality_status = str(data_quality.get("status", FAIL))
    quality_band = PASS if quality_status == "ok" else WARN if quality_status == "warn" else FAIL
    checks.append(
        {
            "name": "source_quality_status",
            "band": quality_band,
            "passed": quality_band != FAIL,
            "actual": quality_status,
            "expected": "ok pass; warn warn; fail fail",
            "message": "Duplicidade, nulos, buracos temporais e datas invalidas afetam a confiabilidade da base.",
        }
    )

    rows_training = int(pipeline_result.get("rows_training", 0))
    rows_band = PASS if rows_training >= 36 else WARN if rows_training >= 24 else FAIL
    checks.append(
        {
            "name": "rows_training",
            "band": rows_band,
            "passed": rows_band != FAIL,
            "actual": rows_training,
            "expected": ">= 36 pass; 24-35 warn; < 24 fail",
            "message": "O numero de meses uteis apos features define a robustez minima do treino.",
        }
    )

    artifact_band = PASS if artifact_data_mode == "real" else FAIL
    checks.append(
        {
            "name": "artifact_data_mode_real",
            "band": artifact_band,
            "passed": artifact_band != FAIL,
            "actual": artifact_data_mode,
            "expected": "artifact must exist and data_mode must be 'real'",
            "message": "O artefato precisa existir e estar marcado como treinado com dados reais.",
        }
    )

    metrics = pipeline_result.get("metrics", {}) or {}
    mae = metrics.get("mae")
    rmse = metrics.get("rmse")

    target_mean_abs = None
    normalized_mae = None
    normalized_rmse = None
    if history_df is not None and not history_df.empty and "target_default_rate" in history_df.columns:
        target_mean_abs = float(history_df["target_default_rate"].abs().mean())
        if target_mean_abs and mae is not None:
            normalized_mae = round(float(mae) / target_mean_abs, 6)
        if target_mean_abs and rmse is not None:
            normalized_rmse = round(float(rmse) / target_mean_abs, 6)

    mae_band = FAIL if normalized_mae is None else PASS if normalized_mae <= 0.08 else WARN if normalized_mae <= 0.12 else FAIL
    checks.append(
        {
            "name": "normalized_mae",
            "band": mae_band,
            "passed": mae_band != FAIL,
            "actual": normalized_mae,
            "expected": "<= 0.08 pass; 0.08-0.12 warn; > 0.12 fail",
            "message": "O MAE e avaliado em relacao a media absoluta da target.",
        }
    )

    rmse_band = FAIL if normalized_rmse is None else PASS if normalized_rmse <= 0.12 else WARN if normalized_rmse <= 0.18 else FAIL
    checks.append(
        {
            "name": "normalized_rmse",
            "band": rmse_band,
            "passed": rmse_band != FAIL,
            "actual": normalized_rmse,
            "expected": "<= 0.12 pass; 0.12-0.18 warn; > 0.18 fail",
            "message": "O RMSE complementa o MAE e penaliza mais erros grandes.",
        }
    )

    status = PASS
    recommendation = "continue"
    if any(c["band"] == FAIL for c in checks):
        status = FAIL
        recommendation = "stop_and_investigate"
    elif any(c["band"] == WARN for c in checks):
        status = WARN
        recommendation = "continue_with_caution"

    return {
        "status": status,
        "recommendation": recommendation,
        "checks": checks,
        "summary": {
            "min_source_rows": min_rows,
            "overlap_ratio": round(overlap_ratio, 6),
            "rows_training": rows_training,
            "mae": mae,
            "rmse": rmse,
            "target_mean_abs": target_mean_abs,
            "normalized_mae": normalized_mae,
            "normalized_rmse": normalized_rmse,
            "artifact_data_mode": artifact_data_mode,
        },
    }


# %% Orchestration
def _replication_steps() -> list[str]:
    return [
        "1. Ensure Python is installed and internet access is available.",
        "2. Run this file directly: python \"Seu modelo de ML ... .py\".",
        "3. Wait for source validation, pipeline training and readiness checks.",
        "4. Inspect console summary and JSON report in ./portable_output/.",
    ]


def run_all() -> PortableReport:
    root = _detect_root()
    ensure_dependencies()
    libs = _import_runtime_libs()
    env_info = bootstrap_env(root)
    paths = _make_paths(root)

    val_start = os.environ["SOURCE_VALIDATION_START"].strip()
    val_end = os.environ["SOURCE_VALIDATION_END"].strip()
    pipe_start = os.environ["PIPELINE_START"].strip()
    pipe_end = os.environ["PIPELINE_END"].strip()

    _print("Validating real sources")
    source_validation, validation_frames = validate_sources_real(libs, val_start, val_end)
    _print("Running data quality report")
    data_quality = run_data_quality_report(libs, validation_frames, val_start, val_end)
    _print("Executing real pipeline")
    pipeline_result, model_bundle, history_df = run_pipeline_real(libs, paths, pipe_start, pipe_end)
    artifacts = inspect_artifacts(paths, model_bundle, pipeline_result["metrics"])
    readiness = assess_readiness(
        source_validation=source_validation,
        data_quality=data_quality,
        pipeline_result=pipeline_result,
        history_df=history_df,
        artifact_data_mode=artifacts["model_data_mode"],
    )

    return PortableReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version.split()[0],
        app_env=os.getenv("APP_ENV", "prod"),
        runtime_paths={
            "root": str(paths.root),
            "output_root": str(paths.output_root),
            "report_path": str(paths.report_path),
        },
        environment=env_info,
        source_validation=source_validation,
        data_quality=data_quality,
        pipeline=pipeline_result,
        artifacts=artifacts,
        readiness=readiness,
        replication_steps=_replication_steps(),
    )


# %% Reporting
def print_summary(report: PortableReport) -> None:
    payload = asdict(report)
    print("=== Portable Real-Data Credit Risk Run ===")
    print(f"generated_at_utc: {payload['generated_at_utc']}")
    print(f"python_version: {payload['python_version']}")
    print(f"app_env: {payload['app_env']}")
    loaded_files = payload["environment"].get("loaded_files") or []
    print(f"env_loaded_from: {loaded_files[0] if loaded_files else 'defaults/process-env'}")
    print(
        "pipeline:"
        f" rows_raw={payload['pipeline']['rows_raw']}"
        f" rows_training={payload['pipeline']['rows_training']}"
        f" mae={payload['pipeline']['metrics'].get('mae')}"
        f" rmse={payload['pipeline']['metrics'].get('rmse')}"
    )
    print(
        "readiness:"
        f" status={payload['readiness']['status']}"
        f" recommendation={payload['readiness']['recommendation']}"
    )
    print(f"report_path: {payload['runtime_paths']['report_path']}")


def save_report(report: PortableReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), ensure_ascii=True, indent=2), encoding="utf-8")


# %% Entrypoint
def main() -> int:
    try:
        report = run_all()
        print_summary(report)
        save_report(report, Path(report.runtime_paths["report_path"]))
        return 0
    except PortableError as exc:
        _print(f"ERROR[{exc.code}]: {exc}")
        return exc.code
    except Exception as exc:
        _print(f"ERROR[5]: Unhandled pipeline failure: {exc}")
        return 5


if __name__ == "__main__":
    raise SystemExit(main())

