from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import TimeSeriesSplit

from src.modeling.evaluate import evaluate_regression


@dataclass
class TrainOutput:
    model: ElasticNet
    feature_columns: List[str]
    metrics: Dict[str, float]
    predictions_df: pd.DataFrame


def train_baseline(df: pd.DataFrame) -> TrainOutput:
    target_col = "target_default_rate"
    feature_cols = [c for c in df.columns if c not in {"year_month", target_col}]
    X = df[feature_cols]
    y = df[target_col]

    tscv = TimeSeriesSplit(n_splits=4)
    model = ElasticNet(alpha=0.05, l1_ratio=0.35, random_state=42, max_iter=10000)

    oof_predictions = pd.Series(index=df.index, dtype=float)
    for train_idx, valid_idx in tscv.split(X):
        X_train, X_valid = X.iloc[train_idx], X.iloc[valid_idx]
        y_train = y.iloc[train_idx]
        model.fit(X_train, y_train)
        oof_predictions.iloc[valid_idx] = model.predict(X_valid)

    valid_mask = oof_predictions.notna()
    metrics = evaluate_regression(y[valid_mask], oof_predictions[valid_mask])

    model.fit(X, y)
    full_predictions = model.predict(X)
    pred_df = df[["year_month", target_col]].copy()
    pred_df["y_hat"] = full_predictions
    pred_df["residual"] = pred_df[target_col] - pred_df["y_hat"]
    return TrainOutput(
        model=model,
        feature_columns=feature_cols,
        metrics=metrics,
        predictions_df=pred_df,
    )

