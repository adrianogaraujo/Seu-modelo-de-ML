from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict

import pandas as pd

from src.ingestion.bcb_client import BCBClient
from src.ingestion.caged_client import CAGEDClient
from src.ingestion.sidra_client import SIDRAClient

YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _month_span(min_month: str | None, max_month: str | None) -> int:
    if not min_month or not max_month:
        return 0
    start = pd.Period(min_month, freq="M")
    end = pd.Period(max_month, freq="M")
    return (end.ordinal - start.ordinal) + 1


def _source_quality(df: pd.DataFrame) -> Dict[str, object]:
    if df.empty:
        return {
            "mode": "real",
            "configured": True,
            "rows": 0,
            "min_month": None,
            "max_month": None,
            "duplicate_months": 0,
            "missing_months": 0,
            "null_cells": 0,
            "invalid_year_month_rows": 0,
            "status": "fail",
        }

    year_month = df["year_month"].astype(str)
    invalid_rows = int((~year_month.str.match(YEAR_MONTH_RE)).sum())
    duplicate_months = int(year_month.duplicated().sum())

    min_month = str(year_month.min())
    max_month = str(year_month.max())
    span = _month_span(min_month, max_month)
    unique_months = int(year_month.nunique())
    missing_months = max(span - unique_months, 0)

    value_cols = [c for c in df.columns if c != "year_month"]
    null_cells = int(df[value_cols].isna().sum().sum()) if value_cols else 0

    status = "ok"
    if invalid_rows > 0:
        status = "fail"
    elif duplicate_months > 0 or missing_months > 0 or null_cells > 0:
        status = "warn"

    return {
        "mode": "real",
        "configured": True,
        "rows": int(len(df)),
        "min_month": min_month,
        "max_month": max_month,
        "duplicate_months": duplicate_months,
        "missing_months": missing_months,
        "null_cells": null_cells,
        "invalid_year_month_rows": invalid_rows,
        "status": status,
    }


def run_data_quality_report(_: Path | None = None) -> Dict[str, object]:
    start = os.getenv("SOURCE_VALIDATION_START", "2024-01")
    end = os.getenv("SOURCE_VALIDATION_END", "2026-01")

    clients = {
        "bcb": BCBClient(),
        "sidra": SIDRAClient(),
        "caged": CAGEDClient(),
    }

    source_frames: Dict[str, pd.DataFrame] = {}
    source_reports: Dict[str, Dict[str, object]] = {}

    for name, client in clients.items():
        df = client.fetch_monthly(start=start, end=end)
        source_frames[name] = df
        source_reports[name] = _source_quality(df)

    common = set(source_frames["bcb"]["year_month"].astype(str))
    common &= set(source_frames["sidra"]["year_month"].astype(str))
    common &= set(source_frames["caged"]["year_month"].astype(str))
    common_months = len(common)
    min_rows = min(int(len(v)) for v in source_frames.values()) if source_frames else 0
    overlap_ratio = round((common_months / min_rows), 6) if min_rows > 0 else 0.0

    merged_status = "ok" if overlap_ratio >= 0.8 else "warn"
    overall_status = "ok"
    if any(r["status"] == "fail" for r in source_reports.values()):
        overall_status = "fail"
    elif any(r["status"] == "warn" for r in source_reports.values()) or merged_status == "warn":
        overall_status = "warn"

    return {
        "status": overall_status,
        "window": {"start": start, "end": end},
        "sources": source_reports,
        "merged": {
            "common_months": common_months,
            "min_source_rows": min_rows,
            "overlap_ratio": overlap_ratio,
            "status": merged_status,
        },
    }
