from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.data_quality_report import run_data_quality_report  # noqa: E402


class DataQualityReportTest(unittest.TestCase):
    def test_data_quality_ok(self):
        bcb = pd.DataFrame({"year_month": ["2025-01", "2025-02"], "x": [1.0, 1.1]})
        sidra = pd.DataFrame({"year_month": ["2025-01", "2025-02"], "y": [2.0, 2.1]})
        caged = pd.DataFrame({"year_month": ["2025-01", "2025-02"], "z": [3.0, 3.1]})
        env = {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "test"}
        with patch.dict(os.environ, env, clear=False):
            with patch("src.jobs.data_quality_report.BCBClient.fetch_monthly", return_value=bcb):
                with patch("src.jobs.data_quality_report.SIDRAClient.fetch_monthly", return_value=sidra):
                    with patch("src.jobs.data_quality_report.CAGEDClient.fetch_monthly", return_value=caged):
                        out = run_data_quality_report()
                        self.assertEqual(out["status"], "ok")
                        self.assertEqual(out["merged"]["overlap_ratio"], 1.0)

    def test_data_quality_warn_on_duplicates(self):
        bcb = pd.DataFrame({"year_month": ["2025-01", "2025-01"], "x": [1.0, 1.1]})
        sidra = pd.DataFrame({"year_month": ["2025-01", "2025-02"], "y": [2.0, 2.1]})
        caged = pd.DataFrame({"year_month": ["2025-01", "2025-02"], "z": [3.0, 3.1]})
        env = {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "test"}
        with patch.dict(os.environ, env, clear=False):
            with patch("src.jobs.data_quality_report.BCBClient.fetch_monthly", return_value=bcb):
                with patch("src.jobs.data_quality_report.SIDRAClient.fetch_monthly", return_value=sidra):
                    with patch("src.jobs.data_quality_report.CAGEDClient.fetch_monthly", return_value=caged):
                        out = run_data_quality_report()
                        self.assertEqual(out["status"], "warn")
                        self.assertEqual(out["sources"]["bcb"]["duplicate_months"], 1)


if __name__ == "__main__":
    unittest.main()

