from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2


FILES_TO_COPY = [
    "data/raw/monthly_merged.csv",
    "data/processed/monthly_dataset.csv",
    "data/processed/historical_predictions.csv",
    "data/artifacts/metrics.json",
    "data/artifacts/baseline_model.joblib",
    "data/db/risk_mvp.sqlite",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a reproducible local snapshot for course demos.")
    parser.add_argument("--name", required=True, help="Snapshot name, e.g. 2026-03-06-course-baseline")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    snapshot_root = root / "data" / "snapshots" / args.name
    snapshot_root.mkdir(parents=True, exist_ok=True)

    copied = []
    for relative in FILES_TO_COPY:
        src = root / relative
        if not src.exists():
            raise FileNotFoundError(f"Required file not found: {src}")
        dst = snapshot_root / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy2(src, dst)
        copied.append(
            {
                "path": relative,
                "size_bytes": src.stat().st_size,
                "sha256": _sha256(src),
            }
        )

    manifest = {
        "snapshot_name": args.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": copied,
    }
    (snapshot_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"status": "ok", "snapshot": str(snapshot_root)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
