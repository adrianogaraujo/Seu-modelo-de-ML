from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.jobs.validate_sources import validate_sources  # noqa: E402


class ValidateSourcesTest(unittest.TestCase):
    def test_validate_sources_success(self):
        frame = pd.DataFrame({"year_month": ["2025-01", "2025-02"], "value": [1, 2]})
        with patch("src.jobs.validate_sources.BCBClient.fetch_monthly", return_value=frame):
            with patch("src.jobs.validate_sources.SIDRAClient.fetch_monthly", return_value=frame):
                with patch("src.jobs.validate_sources.CAGEDClient.fetch_monthly", return_value=frame):
                    out = validate_sources()
                    self.assertEqual(out["status"], "ok")
                    self.assertEqual(out["sources"]["bcb"]["mode"], "real")
                    self.assertEqual(out["sources"]["bcb"]["rows"], 2)
                    self.assertEqual(out["sources"]["sidra"]["min_month"], "2025-01")

    def test_validate_sources_failure(self):
        frame = pd.DataFrame({"year_month": ["2025-01"], "value": [1]})
        with patch("src.jobs.validate_sources.BCBClient.fetch_monthly", return_value=frame):
            with patch("src.jobs.validate_sources.SIDRAClient.fetch_monthly", side_effect=RuntimeError("boom")):
                with patch("src.jobs.validate_sources.CAGEDClient.fetch_monthly", return_value=frame):
                    with self.assertRaises(RuntimeError):
                        validate_sources()


if __name__ == "__main__":
    unittest.main()
