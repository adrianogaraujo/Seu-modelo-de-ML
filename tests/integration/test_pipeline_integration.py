from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.readiness_assessment import assess_readiness_from_artifacts  # noqa: E402
from src.jobs.run_pipeline import read_historical_series, run_pipeline  # noqa: E402


class PipelineIntegrationTest(unittest.TestCase):
    def test_pipeline_generates_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            months = pd.period_range(start="2022-01", periods=48, freq="M").astype(str)
            bcb = pd.DataFrame(
                {
                    "year_month": months,
                    "target_default_rate": [4.0 + (i * 0.015) + ((i % 4) * 0.01) for i in range(len(months))],
                    "north_proxy": [6.8 + (i * 0.01) + ((i % 3) * 0.015) for i in range(len(months))],
                }
            )
            sidra = pd.DataFrame(
                {
                    "year_month": months,
                    "am_unemployment_rate": [10.5 - (i * 0.03) + ((i % 5) * 0.004) for i in range(len(months))],
                    "am_retail_index": [100.0 + (i * 0.12) + ((i % 6) * 0.05) for i in range(len(months))],
                }
            )
            caged = pd.DataFrame(
                {
                    "year_month": months,
                    "am_net_jobs": [90 + i + ((i % 4) * 3) for i in range(len(months))],
                }
            )
            with patch("src.jobs.run_pipeline.BCBClient.fetch_monthly", return_value=bcb):
                with patch("src.jobs.run_pipeline.SIDRAClient.fetch_monthly", return_value=sidra):
                    with patch("src.jobs.run_pipeline.CAGEDClient.fetch_monthly", return_value=caged):
                        result = run_pipeline(root)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["data_provenance"]["bcb"]["mode"], "real")
            self.assertTrue((root / "data" / "artifacts" / "baseline_model.joblib").exists())
            self.assertTrue((root / "data" / "processed" / "historical_predictions.csv").exists())
            self.assertTrue((root / "data" / "db" / "risk_mvp.sqlite").exists())
            readiness = assess_readiness_from_artifacts(root)
            self.assertIn(readiness["status"], {"warn", "pass"})
            self.assertEqual(readiness["summary"]["artifact_data_mode"], "real")
            series = read_historical_series(root, "2025-01", "2025-12")
            self.assertGreater(len(series), 0)


if __name__ == "__main__":
    unittest.main()
