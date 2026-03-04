from __future__ import annotations

import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.modeling.predict import predict_nowcast  # noqa: E402
from src.modeling.train import train_baseline  # noqa: E402


class PredictiveUncertaintyTest(unittest.TestCase):
    def test_train_baseline_exposes_uncertainty_from_residuals(self):
        rows = 12
        df = pd.DataFrame(
            {
                "year_month": [f"2025-{month:02d}" for month in range(1, rows + 1)],
                "target_default_rate": [1.0 + month * 0.07 for month in range(rows)],
                "north_proxy": [2.0 + month * 0.09 for month in range(rows)],
                "north_proxy_lag1": [1.8 + month * 0.09 for month in range(rows)],
                "am_economic_index": [10.0 + month * 0.3 for month in range(rows)],
            }
        )

        out = train_baseline(df)

        self.assertIn("residual_std", out.uncertainty)
        self.assertIn("lower_residual_quantile", out.uncertainty)
        self.assertIn("upper_residual_quantile", out.uncertainty)
        self.assertGreaterEqual(out.uncertainty["residual_std"], 0.0)
        self.assertLessEqual(
            out.uncertainty["lower_residual_quantile"],
            out.uncertainty["upper_residual_quantile"],
        )

    def test_predict_nowcast_prefers_residual_quantiles_when_available(self):
        class StubModel:
            coef_ = [0.5, -0.25]

            def predict(self, X):
                return [2.0]

        latest_row = pd.Series({"feature_a": 4.0, "feature_b": 2.0})

        out = predict_nowcast(
            model=StubModel(),
            feature_columns=["feature_a", "feature_b"],
            latest_row=latest_row,
            reference_month="2026-01",
            uncertainty={
                "residual_std": 0.8,
                "lower_residual_quantile": -0.12,
                "upper_residual_quantile": 0.34,
            },
        )

        self.assertEqual(out["lower"], 1.88)
        self.assertEqual(out["upper"], 2.34)
        self.assertEqual(out["drivers"][0]["name"], "feature_a")


if __name__ == "__main__":
    unittest.main()
