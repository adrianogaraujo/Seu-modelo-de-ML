from __future__ import annotations

import json
import sys
from pathlib import Path
import tempfile
import unittest

import joblib
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.readiness_assessment import assess_readiness_from_artifacts, assess_readiness_from_run  # noqa: E402


def _source(rows: int) -> dict:
    return {
        "mode": "real",
        "configured": True,
        "rows": rows,
        "min_month": "2022-01",
        "max_month": "2025-12",
    }


class ReadinessAssessmentTest(unittest.TestCase):
    def _write_artifacts(
        self,
        root: Path,
        *,
        data_mode: str = "real",
        mae: float = 0.2,
        rmse: float = 0.3,
        target_value: float = 4.0,
        rows_training: int = 48,
    ) -> None:
        (root / "data" / "artifacts").mkdir(parents=True, exist_ok=True)
        (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"data_mode": data_mode, "data_provenance": {"bcb": _source(rows_training), "sidra": _source(rows_training), "caged": _source(rows_training)}},
            root / "data" / "artifacts" / "baseline_model.joblib",
        )
        (root / "data" / "artifacts" / "metrics.json").write_text(
            json.dumps({"mae": mae, "rmse": rmse}),
            encoding="utf-8",
        )
        pd.DataFrame({"year_month": [f"2024-{m:02d}" for m in range(1, rows_training + 1)], "x": range(rows_training)}).to_csv(
            root / "data" / "processed" / "monthly_dataset.csv", index=False
        )
        pd.DataFrame(
            {
                "year_month": [f"2024-{((m - 1) % 12) + 1:02d}" for m in range(1, rows_training + 1)],
                "target_default_rate": [target_value] * rows_training,
                "y_hat": [target_value - mae] * rows_training,
                "residual": [mae] * rows_training,
            }
        ).to_csv(root / "data" / "processed" / "historical_predictions.csv", index=False)

    def _run_inputs(
        self,
        *,
        rows: int = 48,
        overlap_ratio: float = 0.95,
        quality_status: str = "ok",
        rows_training: int = 48,
        mae: float = 0.2,
        rmse: float = 0.3,
    ) -> tuple[dict, dict, dict]:
        sources = {"bcb": _source(rows), "sidra": _source(rows), "caged": _source(rows)}
        source_validation = {"status": "ok", "sources": sources}
        data_quality = {
            "status": quality_status,
            "sources": {},
            "merged": {
                "common_months": int(rows * overlap_ratio),
                "min_source_rows": rows,
                "overlap_ratio": overlap_ratio,
                "status": "ok" if overlap_ratio >= 0.8 else "warn",
            },
        }
        pipeline_result = {
            "status": "ok",
            "rows_raw": rows,
            "rows_training": rows_training,
            "metrics": {"mae": mae, "rmse": rmse},
            "data_provenance": sources,
        }
        return source_validation, data_quality, pipeline_result

    def test_assess_readiness_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, mae=0.2, rmse=0.3, target_value=4.0, rows_training=48)
            source_validation, data_quality, pipeline_result = self._run_inputs()
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "pass")
            self.assertEqual(out["recommendation"], "continue")

    def test_assess_readiness_warn_on_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root)
            source_validation, data_quality, pipeline_result = self._run_inputs(overlap_ratio=0.85)
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "warn")

    def test_assess_readiness_fail_on_low_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root)
            source_validation, data_quality, pipeline_result = self._run_inputs(overlap_ratio=0.75)
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "fail")

    def test_assess_readiness_fail_on_low_rows_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, rows_training=20)
            source_validation, data_quality, pipeline_result = self._run_inputs(rows=48, rows_training=20)
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "fail")

    def test_assess_readiness_warn_on_mid_rows_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, rows_training=30)
            source_validation, data_quality, pipeline_result = self._run_inputs(rows=48, rows_training=30)
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "warn")

    def test_assess_readiness_fail_on_non_real_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, data_mode="legacy")
            source_validation, data_quality, pipeline_result = self._run_inputs()
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "fail")

    def test_assess_readiness_fail_when_metrics_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root)
            source_validation, data_quality, pipeline_result = self._run_inputs()
            pipeline_result["metrics"] = {}
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "fail")

    def test_assess_readiness_fail_when_target_mean_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, target_value=0.0)
            source_validation, data_quality, pipeline_result = self._run_inputs()
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "fail")

    def test_assess_readiness_fail_when_min_source_rows_too_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, rows_training=48)
            source_validation, data_quality, pipeline_result = self._run_inputs(rows=20)
            out = assess_readiness_from_run(source_validation, data_quality, pipeline_result, root)
            self.assertEqual(out["status"], "fail")

    def test_assess_readiness_from_artifacts_reads_current_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifacts(root, mae=0.2, rmse=0.3, target_value=4.0, rows_training=48)
            out = assess_readiness_from_artifacts(root)
            self.assertEqual(out["status"], "pass")
            self.assertAlmostEqual(out["summary"]["normalized_mae"], 0.05)


if __name__ == "__main__":
    unittest.main()
