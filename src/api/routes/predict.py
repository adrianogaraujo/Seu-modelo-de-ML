from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.api.schemas import NowcastRequest, NowcastResponse
from src.modeling.predict import predict_nowcast
from src.modeling.registry import load_model

router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]


@router.post("/predict/nowcast", response_model=NowcastResponse)
def predict_route(payload: NowcastRequest) -> NowcastResponse:
    model_path = ROOT / "data" / "artifacts" / "baseline_model.joblib"
    if not model_path.exists():
        raise HTTPException(status_code=400, detail="Model not found. Run /pipeline/run first.")
    bundle = load_model(model_path)
    latest_row = bundle["latest_row"]
    response = predict_nowcast(
        model=bundle["model"],
        feature_columns=bundle["feature_columns"],
        latest_row=latest_row,
        reference_month=payload.reference_month,
        features_override=payload.features_override,
    )
    return NowcastResponse(**response)

