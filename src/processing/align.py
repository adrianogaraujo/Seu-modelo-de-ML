from __future__ import annotations

import pandas as pd


def align_monthly_tables(*tables: pd.DataFrame) -> pd.DataFrame:
    if not tables:
        raise ValueError("At least one table is required")
    base = tables[0].copy()
    for table in tables[1:]:
        base = base.merge(table, on="year_month", how="inner")
    return base.sort_values("year_month").reset_index(drop=True)

