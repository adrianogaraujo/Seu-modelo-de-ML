from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import app


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        checks: dict[str, object] = {}

        health = await client.get("/health")
        checks["health_status_code"] = health.status_code

        readiness = await client.get("/pipeline/readiness")
        checks["readiness_status_code"] = readiness.status_code
        if readiness.status_code == 200:
            payload = readiness.json()
            checks["readiness_status"] = payload.get("status")
        else:
            checks["readiness_error"] = readiness.text

        pred = await client.post("/predict/nowcast", json={"reference_month": "2026-01"})
        checks["predict_status_code"] = pred.status_code
        if pred.status_code == 200:
            checks["predict_data_mode"] = pred.json().get("data_mode")
        else:
            checks["predict_error"] = pred.text

    print(json.dumps(checks, ensure_ascii=True))


if __name__ == "__main__":
    asyncio.run(main())
