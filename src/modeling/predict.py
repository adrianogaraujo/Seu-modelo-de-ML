from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


def predict_nowcast(
    model,
    feature_columns,
    latest_row: pd.Series,
    reference_month: str,
    features_override: Optional[Dict[str, float]] = None,
    uncertainty: Optional[Dict[str, float]] = None,
    data_mode: str = "real",
) -> Dict[str, object]:
    values = latest_row.copy()
    if features_override:
        for key, value in features_override.items():
            if key in values.index:
                values[key] = float(value)

    X = pd.DataFrame([{col: float(values[col]) for col in feature_columns}])
    y_hat = float(model.predict(X)[0])

    coef = pd.Series(model.coef_, index=feature_columns)
    contrib = (coef * X.iloc[0]).abs().sort_values(ascending=False).head(3)
    drivers = [{"name": name, "contribution": round(float(v), 6)} for name, v in contrib.items()]

    lower_q = None
    upper_q = None
    if uncertainty:
        lower_q = uncertainty.get("lower_residual_quantile")
        upper_q = uncertainty.get("upper_residual_quantile")

    if lower_q is not None and upper_q is not None:
        lower = y_hat + float(lower_q)
        upper = y_hat + float(upper_q)
        if lower > upper:
            lower, upper = upper, lower
    else:
        sigma = float(np.std(model.predict(X)))
        if uncertainty and uncertainty.get("residual_std") is not None:
            sigma = float(uncertainty["residual_std"])
        # For one row or legacy artifacts, fallback to fixed uncertainty floor.
        sigma = max(sigma, 0.15)
        lower = y_hat - 1.64 * sigma
        upper = y_hat + 1.64 * sigma

    return {
        "reference_month": reference_month,
        "y_hat": round(y_hat, 6),
        "lower": round(lower, 6),
        "upper": round(upper, 6),
        "data_mode": data_mode,
        "drivers": drivers,
    }
