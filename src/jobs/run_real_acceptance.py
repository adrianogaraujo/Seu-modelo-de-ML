from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.config.runtime import allow_synthetic_data
from src.jobs.run_pipeline import run_pipeline
from src.jobs.validate_sources import validate_sources


def run_real_acceptance(root: Path) -> Dict[str, object]:
    allow_synthetic = allow_synthetic_data()
    if allow_synthetic:
        raise RuntimeError("Disable ALLOW_SYNTHETIC_DATA for real-data acceptance run.")

    source_check = validate_sources(root)
    pipeline_result = run_pipeline(root)

    checks = {
        "sources_validated": source_check["status"] == "ok",
        "rows_raw_positive": pipeline_result["rows_raw"] > 0,
        "rows_training_positive": pipeline_result["rows_training"] > 0,
        "metrics_present": "mae" in pipeline_result["metrics"] and "rmse" in pipeline_result["metrics"],
        "model_artifact_exists": (root / "data" / "artifacts" / "baseline_model.joblib").exists(),
        "history_exists": (root / "data" / "processed" / "historical_predictions.csv").exists(),
    }

    if not all(checks.values()):
        raise RuntimeError(f"Acceptance checks failed: {checks}")

    return {
        "status": "ok",
        "checks": checks,
        "sources": source_check["sources"],
        "pipeline": pipeline_result,
    }


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    print(run_real_acceptance(project_root))
