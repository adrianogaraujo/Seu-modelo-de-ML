from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config.runtime import allow_synthetic_data  # noqa: E402


class RuntimeConfigTest(unittest.TestCase):
    def test_synthetic_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(allow_synthetic_data())

    def test_synthetic_requires_dev_like_env(self):
        with patch.dict(os.environ, {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "prod"}, clear=True):
            with self.assertRaises(RuntimeError):
                allow_synthetic_data()

    def test_synthetic_allowed_in_test_env(self):
        with patch.dict(os.environ, {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "test"}, clear=True):
            self.assertTrue(allow_synthetic_data())


if __name__ == "__main__":
    unittest.main()

