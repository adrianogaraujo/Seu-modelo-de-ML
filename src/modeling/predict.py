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

    sigma = float(np.std(model.predict(X)))
    # For one row, fallback to fixed uncertainty floor.
    sigma = max(sigma, 0.15)
    return {
        "reference_month": reference_month,
        "y_hat": round(y_hat, 6),
        "lower": round(y_hat - 1.64 * sigma, 6),
        "upper": round(y_hat + 1.64 * sigma, 6),
        "drivers": drivers,
    }

