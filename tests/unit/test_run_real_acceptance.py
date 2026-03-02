from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.run_real_acceptance import run_real_acceptance  # noqa: E402


class RunRealAcceptanceTest(unittest.TestCase):
    def test_acceptance_fails_if_synthetic_enabled(self):
        with patch.dict(os.environ, {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "test"}, clear=False):
            with self.assertRaises(RuntimeError):
                run_real_acceptance(Path("."))

    def test_acceptance_success_with_mocked_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "artifacts").mkdir(parents=True, exist_ok=True)
            (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
            (root / "data" / "artifacts" / "baseline_model.joblib").write_text("x", encoding="utf-8")
            (root / "data" / "processed" / "historical_predictions.csv").write_text("x", encoding="utf-8")
            with patch.dict(os.environ, {"ALLOW_SYNTHETIC_DATA": "0", "APP_ENV": "test"}, clear=False):
                with patch("src.jobs.run_real_acceptance.validate_sources") as v:
                    with patch("src.jobs.run_real_acceptance.run_pipeline") as r:
                        v.return_value = {
                            "status": "ok",
                            "sources": {
                                "bcb": {"rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                "sidra": {"rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                "caged": {"rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                            },
                        }
                        r.return_value = {
                            "status": "ok",
                            "rows_raw": 10,
                            "rows_training": 9,
                            "metrics": {"mae": 0.1, "rmse": 0.2},
                        }
                        out = run_real_acceptance(root)
                        self.assertEqual(out["status"], "ok")
                        self.assertTrue(out["checks"]["metrics_present"])


if __name__ == "__main__":
    unittest.main()
