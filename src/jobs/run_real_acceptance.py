from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.jobs.data_quality_report import run_data_quality_report
from src.jobs.readiness_assessment import assess_readiness_from_run
from src.jobs.run_pipeline import run_pipeline
from src.jobs.validate_sources import validate_sources


def run_real_acceptance(root: Path) -> Dict[str, object]:
    source_check = validate_sources(root)
    pipeline_result = run_pipeline(root)
    source_modes_real = all(source["mode"] == "real" for source in source_check["sources"].values())
    pipeline_modes_real = all(
        source["mode"] == "real" for source in pipeline_result["data_provenance"].values()
    )

    checks = {
        "sources_validated": source_check["status"] == "ok",
        "source_modes_real": source_modes_real,
        "rows_raw_positive": pipeline_result["rows_raw"] > 0,
        "rows_training_positive": pipeline_result["rows_training"] > 0,
        "metrics_present": "mae" in pipeline_result["metrics"] and "rmse" in pipeline_result["metrics"],
        "pipeline_modes_real": pipeline_modes_real,
        "model_artifact_exists": (root / "data" / "artifacts" / "baseline_model.joblib").exists(),
        "history_exists": (root / "data" / "processed" / "historical_predictions.csv").exists(),
    }
    data_quality = run_data_quality_report(root)
    readiness = assess_readiness_from_run(
        source_validation=source_check,
        data_quality=data_quality,
        pipeline_result=pipeline_result,
        project_root=root,
    )
    checks["readiness_non_fail"] = readiness["status"] != "fail"

    if not all(checks.values()):
        raise RuntimeError(
            f"Acceptance checks failed: {checks}. readiness={readiness['status']}"
        )

    return {
        "status": "ok",
        "checks": checks,
        "sources": source_check["sources"],
        "pipeline": pipeline_result,
        "readiness": readiness,
    }


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    print(run_real_acceptance(project_root))
