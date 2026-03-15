from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write release metadata for built coordinate packs.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--release-tag", default=None)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    versions: list[dict[str, object]] = []
    for pack_dir in sorted(path for path in args.output_dir.glob("v*") if path.is_dir()):
        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        versions.append(
            {
                "packVersion": pack_dir.name,
                "majorVersion": manifest.get("majorVersion"),
                "flavor": manifest.get("flavor"),
                "schemaVersion": manifest.get("schemaVersion"),
                "dbcBuild": manifest.get("dbcBuild"),
                "dbcSource": manifest.get("dbcSource"),
            }
        )

    payload = {
        "releaseTag": args.release_tag,
        "versions": versions,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
