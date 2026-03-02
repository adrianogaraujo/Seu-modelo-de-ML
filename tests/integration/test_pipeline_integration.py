from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.run_pipeline import read_historical_series, run_pipeline  # noqa: E402


class PipelineIntegrationTest(unittest.TestCase):
    def test_pipeline_generates_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "test"}, clear=False):
                result = run_pipeline(root)
            self.assertEqual(result["status"], "ok")
            self.assertTrue((root / "data" / "artifacts" / "baseline_model.joblib").exists())
            self.assertTrue((root / "data" / "processed" / "historical_predictions.csv").exists())
            self.assertTrue((root / "data" / "db" / "risk_mvp.sqlite").exists())
            series = read_historical_series(root, "2025-01", "2025-12")
            self.assertGreater(len(series), 0)


if __name__ == "__main__":
    unittest.main()
