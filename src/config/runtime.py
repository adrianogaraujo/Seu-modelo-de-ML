from __future__ import annotations

import os


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def app_env() -> str:
    return os.getenv("APP_ENV", "prod").strip().lower()


def allow_synthetic_data() -> bool:
    enabled = _flag("ALLOW_SYNTHETIC_DATA")
    if not enabled:
        return False
    if app_env() not in {"dev", "local", "test"}:
        raise RuntimeError(
            "ALLOW_SYNTHETIC_DATA is only permitted in APP_ENV=dev|local|test."
        )
    return True

