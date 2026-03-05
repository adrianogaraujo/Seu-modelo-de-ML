from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config.runtime import app_env  # noqa: E402


class RuntimeConfigTest(unittest.TestCase):
    def test_app_env_defaults_to_prod(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(app_env(), "prod")

    def test_app_env_is_normalized(self):
        with patch.dict(os.environ, {"APP_ENV": " TeSt "}, clear=True):
            self.assertEqual(app_env(), "test")


if __name__ == "__main__":
    unittest.main()
