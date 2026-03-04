from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.run_real_acceptance import run_real_acceptance  # noqa: E402


class RunRealAcceptanceTest(unittest.TestCase):
    def test_acceptance_fails_if_any_source_is_not_real(self):
        with patch("src.jobs.run_real_acceptance.validate_sources") as v:
            with patch("src.jobs.run_real_acceptance.run_pipeline") as r:
                with patch("src.jobs.run_real_acceptance.run_data_quality_report") as q:
                    with patch("src.jobs.run_real_acceptance.assess_readiness_from_run") as a:
                        v.return_value = {
                            "status": "ok",
                            "sources": {
                                "bcb": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                "sidra": {"mode": "synthetic", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                "caged": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                            },
                        }
                        r.return_value = {
                            "status": "ok",
                            "rows_raw": 10,
                            "rows_training": 9,
                            "metrics": {"mae": 0.1, "rmse": 0.2},
                            "data_provenance": {
                                "bcb": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                "sidra": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                "caged": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                            },
                        }
                        q.return_value = {"status": "ok", "merged": {"overlap_ratio": 1.0}}
                        a.return_value = {
                            "status": "pass",
                            "recommendation": "continue",
                            "checks": [],
                            "summary": {},
                        }
                        with self.assertRaises(RuntimeError):
                            run_real_acceptance(Path("."))

    def test_acceptance_success_with_mocked_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "artifacts").mkdir(parents=True, exist_ok=True)
            (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
            (root / "data" / "artifacts" / "baseline_model.joblib").write_text("x", encoding="utf-8")
            (root / "data" / "processed" / "historical_predictions.csv").write_text("x", encoding="utf-8")
            with patch("src.jobs.run_real_acceptance.validate_sources") as v:
                with patch("src.jobs.run_real_acceptance.run_pipeline") as r:
                    with patch("src.jobs.run_real_acceptance.run_data_quality_report") as q:
                        with patch("src.jobs.run_real_acceptance.assess_readiness_from_run") as a:
                            v.return_value = {
                                "status": "ok",
                                "sources": {
                                    "bcb": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                    "sidra": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                    "caged": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                },
                            }
                            r.return_value = {
                                "status": "ok",
                                "rows_raw": 10,
                                "rows_training": 9,
                                "metrics": {"mae": 0.1, "rmse": 0.2},
                                "data_provenance": {
                                    "bcb": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                    "sidra": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                    "caged": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
                                },
                            }
                            q.return_value = {"status": "ok", "merged": {"overlap_ratio": 1.0}}
                            a.return_value = {
                                "status": "warn",
                                "recommendation": "continue_with_caution",
                                "checks": [],
                                "summary": {"overlap_ratio": 0.85},
                            }
                            out = run_real_acceptance(root)
                            self.assertEqual(out["status"], "ok")
                            self.assertTrue(out["checks"]["metrics_present"])
                            self.assertTrue(out["checks"]["source_modes_real"])
                            self.assertIn("readiness", out)
                            self.assertEqual(out["readiness"]["status"], "warn")


if __name__ == "__main__":
    unittest.main()
