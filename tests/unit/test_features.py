from __future__ import annotations

import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.processing.features import build_features  # noqa: E402


class FeatureEngineeringTest(unittest.TestCase):
    def test_build_features_creates_lags(self):
        df = pd.DataFrame(
            {
                "year_month": ["2025-01", "2025-02", "2025-03"],
                "target_default_rate": [1.0, 1.1, 1.2],
                "north_proxy": [2.0, 2.1, 2.2],
            }
        )
        out = build_features(df)
        self.assertIn("north_proxy_lag1", out.columns)
        self.assertGreaterEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()

