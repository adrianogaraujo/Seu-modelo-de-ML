from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import copy2


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore files from a previously created local snapshot.")
    parser.add_argument("--name", required=True, help="Snapshot name")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    snapshot_root = root / "data" / "snapshots" / args.name
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

    print(json.dumps({"status": "ok", "restored_snapshot": args.name}, ensure_ascii=True))


if __name__ == "__main__":
    main()
