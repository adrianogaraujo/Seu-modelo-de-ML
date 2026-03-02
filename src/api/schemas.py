from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class PipelineRunResponse(BaseModel):
    status: str
    rows_raw: int
    rows_training: int
    metrics: Dict[str, float]


class SourceValidationSummary(BaseModel):
    rows: int
    min_month: str | None
    max_month: str | None


class SourceValidationResponse(BaseModel):
    status: str
    window: Dict[str, str]
    sources: Dict[str, SourceValidationSummary]
    allow_synthetic_data: bool


class RealAcceptanceResponse(BaseModel):
    status: str
    checks: Dict[str, bool]
    sources: Dict[str, SourceValidationSummary]
    pipeline: PipelineRunResponse


class DataQualitySourceSummary(BaseModel):
    rows: int
    min_month: str | None
    max_month: str | None
    duplicate_months: int
    missing_months: int
    null_cells: int
    invalid_year_month_rows: int
    status: str


class DataQualityMergedSummary(BaseModel):
    common_months: int
    min_source_rows: int
    overlap_ratio: float
    status: str


class DataQualityResponse(BaseModel):
    status: str
    window: Dict[str, str]
    allow_synthetic_data: bool
    sources: Dict[str, DataQualitySourceSummary]
    merged: DataQualityMergedSummary


class NowcastRequest(BaseModel):
    reference_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    features_override: Optional[Dict[str, float]] = None


class Driver(BaseModel):
    name: str
    contribution: float


class NowcastResponse(BaseModel):
    reference_month: str
    y_hat: float
    lower: float
    upper: float
    drivers: List[Driver]


class SeriesPoint(BaseModel):
    year_month: str
    target_default_rate: float
    y_hat: float


class SeriesResponse(BaseModel):
    from_month: str
    to_month: str
    points: List[SeriesPoint]
