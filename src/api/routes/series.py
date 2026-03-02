from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import SeriesPoint, SeriesResponse
from src.jobs.run_pipeline import read_historical_series

router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]


@router.get("/series/target", response_model=SeriesResponse)
def series_route(
    from_month: str = Query(alias="from", pattern=r"^\d{4}-\d{2}$"),
    to_month: str = Query(alias="to", pattern=r"^\d{4}-\d{2}$"),
) -> SeriesResponse:
    csv_path = ROOT / "data" / "processed" / "historical_predictions.csv"
    db_path = ROOT / "data" / "db" / "risk_mvp.sqlite"
    if not csv_path.exists() and not db_path.exists():
        raise HTTPException(status_code=400, detail="History not found. Run /pipeline/run first.")
    df = read_historical_series(ROOT, from_month, to_month)
    points = [
        SeriesPoint(
            year_month=str(row["year_month"]),
            target_default_rate=float(row["target_default_rate"]),
            y_hat=float(row["y_hat"]),
        )
        for _, row in df.iterrows()
    ]
    return SeriesResponse(from_month=from_month, to_month=to_month, points=points)
