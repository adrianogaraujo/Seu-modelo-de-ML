from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from src.ingestion.bcb_client import BCBClient
from src.ingestion.caged_client import CAGEDClient
from src.ingestion.sidra_client import SIDRAClient
from src.modeling.registry import ensure_dirs, save_csv, save_json, save_model
from src.modeling.train import train_baseline
from src.processing.align import align_monthly_tables
from src.processing.features import build_features
from src.processing.quality import apply_quality_rules
from src.storage.sqlite_store import (
    fetch_historical_predictions,
    init_db,
    insert_metrics,
    upsert_historical_predictions,
    upsert_monthly_observations,
)


def _provenance(df: pd.DataFrame) -> Dict[str, object]:
    return {
        "mode": "real",
        "configured": True,
        "rows": int(len(df)),
        "min_month": str(df["year_month"].min()) if not df.empty else None,
        "max_month": str(df["year_month"].max()) if not df.empty else None,
    }


def run_pipeline(root: Path) -> Dict[str, object]:
    ensure_dirs(root)
    db_path = root / "data" / "db" / "risk_mvp.sqlite"
    init_db(db_path)

    bcb_df = BCBClient().fetch_monthly()
    sidra_df = SIDRAClient().fetch_monthly()
    caged_df = CAGEDClient().fetch_monthly()
    data_provenance = {
        "bcb": _provenance(bcb_df),
        "sidra": _provenance(sidra_df),
        "caged": _provenance(caged_df),
    }
    merged = align_monthly_tables(bcb_df, sidra_df, caged_df)
    cleaned = apply_quality_rules(merged)
    featured = build_features(cleaned)
    train_out = train_baseline(featured)

    save_csv(merged, root / "data" / "raw" / "monthly_merged.csv")
    save_csv(featured, root / "data" / "processed" / "monthly_dataset.csv")
    save_csv(train_out.predictions_df, root / "data" / "processed" / "historical_predictions.csv")
    save_json(train_out.metrics, root / "data" / "artifacts" / "metrics.json")
    upsert_monthly_observations(db_path, merged)
    upsert_historical_predictions(db_path, train_out.predictions_df)
    insert_metrics(db_path, train_out.metrics)
    save_model(
        {
            "model": train_out.model,
            "feature_columns": train_out.feature_columns,
            "latest_row": featured.iloc[-1].to_dict(),
            "latest_month": str(featured.iloc[-1]["year_month"]),
            "uncertainty": train_out.uncertainty,
            "data_mode": "real",
            "data_provenance": data_provenance,
        },
        root / "data" / "artifacts" / "baseline_model.joblib",
    )

    return {
        "status": "ok",
        "rows_raw": int(len(merged)),
        "rows_training": int(len(featured)),
        "metrics": train_out.metrics,
        "data_provenance": data_provenance,
    }


def read_historical_series(root: Path, from_month: str, to_month: str) -> pd.DataFrame:
    db_path = root / "data" / "db" / "risk_mvp.sqlite"
    if db_path.exists():
        df = fetch_historical_predictions(db_path, from_month, to_month)
        if not df.empty:
            return df
    path = root / "data" / "processed" / "historical_predictions.csv"
    df = pd.read_csv(path)
    mask = (df["year_month"] >= from_month) & (df["year_month"] <= to_month)
    return df.loc[mask, ["year_month", "target_default_rate", "y_hat"]].reset_index(drop=True)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    result = run_pipeline(project_root)
    print(result)
