from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .build_pack import build_coordinate_pack
from .converter import CoordinateConverter
from .models import CoordinatePack


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone coordinate tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_pack_parser = subparsers.add_parser("build-pack")
    build_pack_parser.add_argument("--major-version", type=int, required=True)
    build_pack_parser.add_argument("--dbc-db", type=Path, required=True)
    build_pack_parser.add_argument("--output-dir", type=Path, required=True)

    convert_zone_parser = subparsers.add_parser("convert-zone-buckets")
    convert_zone_parser.add_argument("--pack-dir", type=Path, required=True)
    convert_zone_parser.add_argument("--input-json", type=Path, required=True)
    convert_zone_parser.add_argument("--output-json", type=Path, required=True)
    convert_zone_parser.add_argument("--coord-decimals", type=int, default=2)

    args = parser.parse_args()

    if args.command == "build-pack":
        pack = build_coordinate_pack(
            major_version=args.major_version,
            dbc_db_path=args.dbc_db,
        )
        pack.dump(args.output_dir)
        return

    if args.command == "convert-zone-buckets":
        pack = CoordinatePack.load(args.pack_dir)
        converter = CoordinateConverter(pack)
        data = _load_int_key_dict(args.input_json)
        result = converter.convert_zone_buckets(data, coord_decimals=args.coord_decimals)
        _dump_json(args.output_json, _stringify_int_keys(result))
        return

    raise RuntimeError(f"Unhandled command: {args.command}")


def _load_int_key_dict(path: Path) -> dict[int, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {int(key): value for key, value in data.items()}


def _stringify_int_keys(data: dict[int, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in data.items()}


def _dump_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
