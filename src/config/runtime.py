from __future__ import annotations

import os

def app_env() -> str:
    return os.getenv("APP_ENV", "prod").strip().lower()
