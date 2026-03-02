from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.api.main import app  # noqa: E402


class ApiE2ETest(unittest.IsolatedAsyncioTestCase):
    async def test_end_to_end(self):
        transport = httpx.ASGITransport(app=app)
        with patch.dict(os.environ, {"ALLOW_SYNTHETIC_DATA": "1", "APP_ENV": "test"}, clear=False):
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                r_health = await client.get("/health")
                self.assertEqual(r_health.status_code, 200)
                r_validate = await client.get("/pipeline/validate-sources")
                self.assertEqual(r_validate.status_code, 200)
                r_quality = await client.get("/pipeline/data-quality")
                self.assertEqual(r_quality.status_code, 200)
                r_acceptance = await client.post("/pipeline/run-real-acceptance")
                self.assertEqual(r_acceptance.status_code, 400)
                r_pipeline = await client.post("/pipeline/run")
                self.assertEqual(r_pipeline.status_code, 200)
                r_predict = await client.post("/predict/nowcast", json={"reference_month": "2026-01"})
                self.assertEqual(r_predict.status_code, 200)
                r_series = await client.get("/series/target", params={"from": "2025-01", "to": "2026-01"})
                self.assertEqual(r_series.status_code, 200)
                self.assertIn("points", r_series.json())


if __name__ == "__main__":
    unittest.main()
