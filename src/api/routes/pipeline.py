from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    DataQualityResponse,
    PipelineRunResponse,
    RealAcceptanceResponse,
    SourceValidationResponse,
)
from src.jobs.data_quality_report import run_data_quality_report
from src.jobs.run_pipeline import run_pipeline
from src.jobs.run_real_acceptance import run_real_acceptance
from src.jobs.validate_sources import validate_sources

router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]


@router.post("/pipeline/run", response_model=PipelineRunResponse)
def run_pipeline_route() -> PipelineRunResponse:
    try:
        return PipelineRunResponse(**run_pipeline(ROOT))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pipeline/validate-sources", response_model=SourceValidationResponse)
def validate_sources_route() -> SourceValidationResponse:
    try:
        return SourceValidationResponse(**validate_sources(ROOT))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pipeline/run-real-acceptance", response_model=RealAcceptanceResponse)
def run_real_acceptance_route() -> RealAcceptanceResponse:
    try:
        return RealAcceptanceResponse(**run_real_acceptance(ROOT))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pipeline/data-quality", response_model=DataQualityResponse)
def data_quality_route() -> DataQualityResponse:
    try:
        return DataQualityResponse(**run_data_quality_report(ROOT))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
