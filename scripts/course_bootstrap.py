from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from shutil import copy2
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.jobs.readiness_assessment import assess_readiness_from_artifacts
from src.jobs.run_pipeline import run_pipeline
from src.jobs.validate_sources import validate_sources


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


def _restore_snapshot(root: Path, name: str) -> None:
    snapshot_root = root / "data" / "snapshots" / name
    manifest_path = snapshot_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Snapshot manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        relative = item["path"]
        src = snapshot_root / relative
        dst = root / relative
        if not src.exists():
            raise FileNotFoundError(f"Snapshot file missing: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="One-command bootstrap for course demo runs.")
    parser.add_argument("--mode", choices=["real", "snapshot"], default="snapshot")
    parser.add_argument("--snapshot", default="", help="Snapshot name for snapshot mode")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--env-file", default=".env", help="Path to env file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    _load_env_file(root / args.env_file)

    out: dict[str, object] = {"mode": args.mode}
    if args.mode == "real":
        out["source_validation"] = validate_sources(root)
        out["pipeline"] = run_pipeline(root)
    else:
        if not args.snapshot:
            raise ValueError("--snapshot is required in snapshot mode")
        _restore_snapshot(root, args.snapshot)

    out["readiness"] = assess_readiness_from_artifacts(root)
    print(json.dumps(out, ensure_ascii=True))


if __name__ == "__main__":
    main()
