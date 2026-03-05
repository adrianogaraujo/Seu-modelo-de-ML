from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pandas as pd

from src.ingestion.bcb_client import BCBClient
from src.ingestion.caged_client import CAGEDClient
from src.ingestion.sidra_client import SIDRAClient


def _summary(df: pd.DataFrame) -> Dict[str, object]:
    if df.empty:
        return {"mode": "real", "configured": True, "rows": 0, "min_month": None, "max_month": None}
    return {
        "mode": "real",
        "configured": True,
        "rows": int(len(df)),
        "min_month": str(df["year_month"].min()),
        "max_month": str(df["year_month"].max()),
    }


def validate_sources(_: Path | None = None) -> Dict[str, object]:
    start = os.getenv("SOURCE_VALIDATION_START", "2024-01")
    end = os.getenv("SOURCE_VALIDATION_END", "2026-01")

    errors: Dict[str, str] = {}
    details: Dict[str, Dict[str, object]] = {}
    clients = {
        "bcb": BCBClient(),
        "sidra": SIDRAClient(),
        "caged": CAGEDClient(),
    }

    for name, client in clients.items():
        try:
            df = client.fetch_monthly(start=start, end=end)
            details[name] = _summary(df)
        except Exception as exc:
            errors[name] = str(exc)

    if errors:
        raise RuntimeError(f"Source validation failed: {errors}")

    return {
        "status": "ok",
        "window": {"start": start, "end": end},
        "sources": details,
    }
