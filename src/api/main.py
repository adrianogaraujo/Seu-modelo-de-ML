from __future__ import annotations

from fastapi import FastAPI

from src.api.routes.health import router as health_router
from src.api.routes.pipeline import router as pipeline_router
from src.api.routes.predict import router as predict_router
from src.api.routes.series import router as series_router

app = FastAPI(title="Risco de Credito Amazonas MVP", version="0.1.0")
app.include_router(health_router)
app.include_router(pipeline_router)
app.include_router(predict_router)
app.include_router(series_router)

