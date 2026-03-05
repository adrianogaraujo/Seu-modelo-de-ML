from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.api.main import app  # noqa: E402


class ApiE2ETest(unittest.IsolatedAsyncioTestCase):
    async def test_end_to_end(self):
        transport = httpx.ASGITransport(app=app)
        source_meta = {
            "bcb": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
            "sidra": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
            "caged": {"mode": "real", "configured": True, "rows": 10, "min_month": "2025-01", "max_month": "2025-10"},
        }
        quality_meta = {
            "bcb": {
                **source_meta["bcb"],
                "duplicate_months": 0,
                "missing_months": 0,
                "null_cells": 0,
                "invalid_year_month_rows": 0,
                "status": "ok",
            },
            "sidra": {
                **source_meta["sidra"],
                "duplicate_months": 0,
                "missing_months": 0,
                "null_cells": 0,
                "invalid_year_month_rows": 0,
                "status": "ok",
            },
            "caged": {
                **source_meta["caged"],
                "duplicate_months": 0,
                "missing_months": 0,
                "null_cells": 0,
                "invalid_year_month_rows": 0,
                "status": "ok",
            },
        }
        readiness = {
            "status": "warn",
            "recommendation": "continue_with_caution",
            "checks": [
                {
                    "name": "overlap_ratio",
                    "band": "warn",
                    "passed": True,
                    "actual": 0.85,
                    "expected": ">= 0.90 pass; 0.80-0.89 warn; < 0.80 fail",
                    "message": "A sobreposicao entre fontes mede a saude do cruzamento temporal.",
                }
            ],
            "summary": {
                "min_source_rows": 36,
                "overlap_ratio": 0.85,
                "rows_training": 30,
                "mae": 0.1,
                "rmse": 0.2,
                "target_mean_abs": 4.2,
                "normalized_mae": 0.02381,
                "normalized_rmse": 0.047619,
                "artifact_data_mode": "real",
            },
        }

        class StubModel:
            coef_ = [0.1, 0.2]

            def predict(self, X):
                return [4.25]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "artifacts").mkdir(parents=True, exist_ok=True)
            (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
            (root / "data" / "artifacts" / "baseline_model.joblib").write_text("x", encoding="utf-8")
            (root / "data" / "processed" / "historical_predictions.csv").write_text("x", encoding="utf-8")
            bundle = {
                "model": StubModel(),
                "feature_columns": ["feature_a", "feature_b"],
                "latest_row": {"feature_a": 1.0, "feature_b": 2.0},
                "uncertainty": {
                    "residual_std": 0.2,
                    "lower_residual_quantile": -0.1,
                    "upper_residual_quantile": 0.15,
                },
                "data_mode": "real",
                "data_provenance": source_meta,
            }
            with patch("src.api.routes.pipeline.validate_sources", return_value={"status": "ok", "window": {"start": "2025-01", "end": "2025-10"}, "sources": source_meta}):
                with patch("src.api.routes.pipeline.run_data_quality_report", return_value={"status": "ok", "window": {"start": "2025-01", "end": "2025-10"}, "sources": quality_meta, "merged": {"common_months": 10, "min_source_rows": 10, "overlap_ratio": 1.0, "status": "ok"}}):
                    with patch("src.api.routes.pipeline.assess_readiness_from_artifacts", return_value=readiness):
                        with patch("src.api.routes.pipeline.run_real_acceptance", return_value={"status": "ok", "checks": {"sources_validated": True}, "sources": source_meta, "pipeline": {"status": "ok", "rows_raw": 10, "rows_training": 9, "metrics": {"mae": 0.1, "rmse": 0.2}, "data_provenance": source_meta}, "readiness": readiness}):
                            with patch("src.api.routes.pipeline.run_pipeline", return_value={"status": "ok", "rows_raw": 10, "rows_training": 9, "metrics": {"mae": 0.1, "rmse": 0.2}, "data_provenance": source_meta}):
                                with patch("src.api.routes.predict.ROOT", root):
                                    with patch("src.api.routes.predict.load_model", return_value=bundle):
                                        with patch("src.api.routes.series.ROOT", root):
                                            with patch("src.api.routes.series.read_historical_series", return_value=pd.DataFrame({"year_month": ["2025-01"], "target_default_rate": [4.2], "y_hat": [4.25]})):
                                                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                                                    r_health = await client.get("/health")
                                                    self.assertEqual(r_health.status_code, 200)
                                                    r_validate = await client.get("/pipeline/validate-sources")
                                                    self.assertEqual(r_validate.status_code, 200)
                                                    self.assertEqual(r_validate.json()["sources"]["bcb"]["mode"], "real")
                                                    r_quality = await client.get("/pipeline/data-quality")
                                                    self.assertEqual(r_quality.status_code, 200)
                                                    r_readiness = await client.get("/pipeline/readiness")
                                                    self.assertEqual(r_readiness.status_code, 200)
                                                    self.assertEqual(r_readiness.json()["status"], "warn")
                                                    r_acceptance = await client.post("/pipeline/run-real-acceptance")
                                                    self.assertEqual(r_acceptance.status_code, 200)
                                                    self.assertIn("readiness", r_acceptance.json())
                                                    r_pipeline = await client.post("/pipeline/run")
                                                    self.assertEqual(r_pipeline.status_code, 200)
                                                    self.assertIn("data_provenance", r_pipeline.json())
                                                    r_predict = await client.post("/predict/nowcast", json={"reference_month": "2026-01"})
                                                    self.assertEqual(r_predict.status_code, 200)
                                                    self.assertEqual(r_predict.json()["data_mode"], "real")
                                                    r_series = await client.get("/series/target", params={"from": "2025-01", "to": "2026-01"})
                                                    self.assertEqual(r_series.status_code, 200)
                                                    self.assertIn("points", r_series.json())


if __name__ == "__main__":
    unittest.main()
