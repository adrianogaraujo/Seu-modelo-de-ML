from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.api.schemas import NowcastRequest, ReadinessAssessment  # noqa: E402


class SchemaValidationTest(unittest.TestCase):
    def test_reference_month_validation(self):
        ok = NowcastRequest(reference_month="2026-01")
        self.assertEqual(ok.reference_month, "2026-01")
        with self.assertRaises(Exception):
            NowcastRequest(reference_month="2026/01")

    def test_readiness_schema(self):
        assessment = ReadinessAssessment(
            status="warn",
            recommendation="continue_with_caution",
            checks=[
                {
                    "name": "overlap_ratio",
                    "band": "warn",
                    "passed": True,
                    "actual": 0.85,
                    "expected": ">= 0.90 pass; 0.80-0.89 warn; < 0.80 fail",
                    "message": "A sobreposicao entre fontes mede a saude do cruzamento temporal.",
                }
            ],
            summary={"overlap_ratio": 0.85},
        )
        self.assertEqual(assessment.status, "warn")


if __name__ == "__main__":
    unittest.main()
