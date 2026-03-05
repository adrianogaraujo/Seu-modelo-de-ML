from __future__ import annotations

import pandas as pd


def apply_quality_rules(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    num_cols = [c for c in out.columns if c != "year_month"]
    out[num_cols] = out[num_cols].interpolate(limit_direction="both")
    for col in num_cols:
        low = out[col].quantile(0.01)
        high = out[col].quantile(0.99)
        out[col] = out[col].clip(lower=low, upper=high)
    return out

