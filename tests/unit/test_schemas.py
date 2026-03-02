from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.api.schemas import NowcastRequest  # noqa: E402


class SchemaValidationTest(unittest.TestCase):
    def test_reference_month_validation(self):
        ok = NowcastRequest(reference_month="2026-01")
        self.assertEqual(ok.reference_month, "2026-01")
        with self.assertRaises(Exception):
            NowcastRequest(reference_month="2026/01")


if __name__ == "__main__":
    unittest.main()

