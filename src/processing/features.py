from __future__ import annotations

import pandas as pd


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    feature_cols = [c for c in out.columns if c not in {"year_month", "target_default_rate"}]
    for col in feature_cols:
        out[f"{col}_lag1"] = out[col].shift(1)
        out[f"{col}_ma3"] = out[col].rolling(window=3, min_periods=1).mean()
    out = out.dropna().reset_index(drop=True)
    return out

