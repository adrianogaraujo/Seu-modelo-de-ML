from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.modeling.registry import load_model

PASS = "pass"
WARN = "warn"
FAIL = "fail"


def _band_from_thresholds(value: float, pass_min: float, warn_min: float) -> str:
    if value >= pass_min:
        return PASS
    if value >= warn_min:
        return WARN
    return FAIL


def _band_from_max_thresholds(value: float, pass_max: float, warn_max: float) -> str:
    if value <= pass_max:
        return PASS
    if value <= warn_max:
        return WARN
    return FAIL


def _make_check(
    name: str,
    band: str,
    actual: Any,
    expected: str,
    message: str,
) -> Dict[str, Any]:
    return {
        "name": name,
        "band": band,
        "passed": band != FAIL,
        "actual": actual,
        "expected": expected,
        "message": message,
    }


def _load_artifact_state(project_root: Path) -> Dict[str, Any]:
    artifacts_dir = project_root / "data" / "artifacts"
    processed_dir = project_root / "data" / "processed"
    model_path = artifacts_dir / "baseline_model.joblib"
    metrics_path = artifacts_dir / "metrics.json"
    dataset_path = processed_dir / "monthly_dataset.csv"
    history_path = processed_dir / "historical_predictions.csv"

    bundle = load_model(model_path) if model_path.exists() else None
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
    dataset = pd.read_csv(dataset_path) if dataset_path.exists() else None
    history = pd.read_csv(history_path) if history_path.exists() else None

    return {
        "model_path": model_path,
        "bundle": bundle,
        "metrics_path": metrics_path,
        "metrics": metrics,
        "dataset_path": dataset_path,
        "dataset": dataset,
        "history_path": history_path,
        "history": history,
    }


def _normalize_metric(metric_value: Any, history_df: pd.DataFrame | None) -> tuple[float | None, float | None]:
    if metric_value is None or history_df is None or history_df.empty:
        return None, None
    if "target_default_rate" not in history_df.columns:
        return None, None
    target_mean_abs = float(history_df["target_default_rate"].abs().mean())
    if target_mean_abs == 0.0:
        return None, 0.0
    return round(float(metric_value) / target_mean_abs, 6), round(target_mean_abs, 6)


def _summarize_status(checks: List[Dict[str, Any]]) -> tuple[str, str]:
    if any(check["band"] == FAIL for check in checks):
        return FAIL, "stop_and_investigate"
    if any(check["band"] == WARN for check in checks):
        return WARN, "continue_with_caution"
    return PASS, "continue"


def assess_readiness_from_run(
    source_validation: Dict[str, Any],
    data_quality: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    project_root: Path,
) -> Dict[str, Any]:
    artifact_state = _load_artifact_state(project_root)
    return _assess(
        source_validation=source_validation,
        data_quality=data_quality,
        pipeline_result=pipeline_result,
        artifact_state=artifact_state,
    )


def assess_readiness_from_artifacts(project_root: Path) -> Dict[str, Any]:
    artifact_state = _load_artifact_state(project_root)
    bundle = artifact_state["bundle"]
    if bundle is None:
        raise RuntimeError("Readiness unavailable: model artifact not found. Run /pipeline/run first.")
    if not artifact_state["metrics_path"].exists():
        raise RuntimeError("Readiness unavailable: metrics.json not found. Run /pipeline/run first.")
    if not artifact_state["dataset_path"].exists():
        raise RuntimeError("Readiness unavailable: monthly_dataset.csv not found. Run /pipeline/run first.")
    if not artifact_state["history_path"].exists():
        raise RuntimeError("Readiness unavailable: historical_predictions.csv not found. Run /pipeline/run first.")

    source_validation = {
        "status": "ok" if all(v.get("mode") == "real" for v in (bundle.get("data_provenance") or {}).values()) else "fail",
        "sources": bundle.get("data_provenance") or {},
    }
    dataset = artifact_state["dataset"]
    rows_training = int(len(dataset)) if dataset is not None else 0
    data_quality = {
        "status": "ok",
        "sources": {},
        "merged": {
            "common_months": rows_training,
            "min_source_rows": min((v.get("rows", 0) for v in source_validation["sources"].values()), default=0),
            "overlap_ratio": 1.0,
            "status": "ok",
        },
    }
    pipeline_result = {
        "status": "ok",
        "rows_raw": source_validation["sources"].get("bcb", {}).get("rows", rows_training),
        "rows_training": rows_training,
        "metrics": artifact_state["metrics"] or {},
        "data_provenance": source_validation["sources"],
    }
    return _assess(
        source_validation=source_validation,
        data_quality=data_quality,
        pipeline_result=pipeline_result,
        artifact_state=artifact_state,
    )


def _assess(
    source_validation: Dict[str, Any],
    data_quality: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    artifact_state: Dict[str, Any],
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    sources = source_validation.get("sources", {})
    all_sources_real = bool(sources) and all(
        source.get("mode") == "real" and source.get("configured") is True for source in sources.values()
    )
    checks.append(
        _make_check(
            name="all_sources_real",
            band=PASS if all_sources_real else FAIL,
            actual=all_sources_real,
            expected="all sources must be mode=real and configured=true",
            message="Todas as fontes devem estar configuradas e marcadas como reais.",
        )
    )

    min_source_rows = min((int(source.get("rows", 0)) for source in sources.values()), default=0)
    min_rows_band = _band_from_thresholds(min_source_rows, pass_min=36, warn_min=24)
    checks.append(
        _make_check(
            name="min_source_rows",
            band=min_rows_band,
            actual=min_source_rows,
            expected=">= 36 pass; 24-35 warn; < 24 fail",
            message="A menor fonte precisa ter historico suficiente para um baseline mensal defensavel.",
        )
    )

    overlap_ratio = float(data_quality.get("merged", {}).get("overlap_ratio", 0.0))
    if overlap_ratio >= 0.90:
        overlap_band = PASS
    elif overlap_ratio >= 0.80:
        overlap_band = WARN
    else:
        overlap_band = FAIL
    checks.append(
        _make_check(
            name="overlap_ratio",
            band=overlap_band,
            actual=round(overlap_ratio, 6),
            expected=">= 0.90 pass; 0.80-0.89 warn; < 0.80 fail",
            message="A sobreposicao entre fontes mede a saude do cruzamento temporal.",
        )
    )

    source_quality_status = str(data_quality.get("status", FAIL))
    quality_band = PASS if source_quality_status == "ok" else WARN if source_quality_status == "warn" else FAIL
    checks.append(
        _make_check(
            name="source_quality_status",
            band=quality_band,
            actual=source_quality_status,
            expected="ok pass; warn warn; fail fail",
            message="Duplicidade, nulos, buracos temporais e datas invalidas afetam a confiabilidade da base.",
        )
    )

    rows_training = int(pipeline_result.get("rows_training", 0))
    rows_training_band = _band_from_thresholds(rows_training, pass_min=36, warn_min=24)
    checks.append(
        _make_check(
            name="rows_training",
            band=rows_training_band,
            actual=rows_training,
            expected=">= 36 pass; 24-35 warn; < 24 fail",
            message="O numero de meses uteis apos features define a robustez minima do treino.",
        )
    )

    bundle = artifact_state["bundle"]
    artifact_data_mode = None if bundle is None else bundle.get("data_mode")
    artifact_band = PASS if artifact_data_mode == "real" else FAIL
    checks.append(
        _make_check(
            name="artifact_data_mode_real",
            band=artifact_band,
            actual=artifact_data_mode,
            expected="artifact must exist and data_mode must be 'real'",
            message="O artefato precisa existir e estar marcado como treinado com dados reais.",
        )
    )

    metrics = pipeline_result.get("metrics", {}) or {}
    mae = metrics.get("mae")
    rmse = metrics.get("rmse")
    history_df = artifact_state["history"]
    normalized_mae, target_mean_abs = _normalize_metric(mae, history_df)
    normalized_rmse, target_mean_abs_rmse = _normalize_metric(rmse, history_df)
    if target_mean_abs is None:
        target_mean_abs = target_mean_abs_rmse

    if normalized_mae is None:
        mae_band = FAIL
        mae_message = "Nao foi possivel normalizar o MAE; historico ou target invalido."
    else:
        mae_band = _band_from_max_thresholds(normalized_mae, pass_max=0.08, warn_max=0.12)
        mae_message = "O MAE e avaliado em relacao a media absoluta da target."
    checks.append(
        _make_check(
            name="normalized_mae",
            band=mae_band,
            actual=normalized_mae,
            expected="<= 0.08 pass; 0.08-0.12 warn; > 0.12 fail",
            message=mae_message,
        )
    )

    if normalized_rmse is None:
        rmse_band = FAIL
        rmse_message = "Nao foi possivel normalizar o RMSE; historico ou target invalido."
    else:
        rmse_band = _band_from_max_thresholds(normalized_rmse, pass_max=0.12, warn_max=0.18)
        rmse_message = "O RMSE complementa o MAE e penaliza mais erros grandes."
    checks.append(
        _make_check(
            name="normalized_rmse",
            band=rmse_band,
            actual=normalized_rmse,
            expected="<= 0.12 pass; 0.12-0.18 warn; > 0.18 fail",
            message=rmse_message,
        )
    )

    status, recommendation = _summarize_status(checks)
    summary = {
        "min_source_rows": min_source_rows,
        "overlap_ratio": round(overlap_ratio, 6),
        "rows_training": rows_training,
        "mae": mae,
        "rmse": rmse,
        "target_mean_abs": target_mean_abs,
        "normalized_mae": normalized_mae,
        "normalized_rmse": normalized_rmse,
        "artifact_data_mode": artifact_data_mode,
    }
    return {
        "status": status,
        "recommendation": recommendation,
        "checks": checks,
        "summary": summary,
    }
