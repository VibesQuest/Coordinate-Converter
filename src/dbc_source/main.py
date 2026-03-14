from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

from . import areatable, map, uimap, uimapassignment
from .common import download_csv, get_all_versions, resolve_build
from ..versions import flavor_for_major_version


DBC_TABLES: list[ModuleType] = [
    areatable,
    map,
    uimap,
    uimapassignment,
]


def ensure_csv(
    table_module: ModuleType,
    build_version: str,
    data_dir: Path,
    allow_download: bool,
) -> Path:
    filename = f"{table_module.TABLE_NAME}.{build_version}.csv"
    data_path = data_dir / filename
    if data_path.exists():
        return data_path
    if not allow_download:
        raise FileNotFoundError(f"{table_module.TABLE_NAME} CSV not found in {data_dir}")
    downloaded = download_csv(table_module.DB2_NAME, build_version, data_dir)
    if not downloaded:
        raise FileNotFoundError(f"Failed to download {table_module.TABLE_NAME} for build {build_version}")
    return downloaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build minimal DBC SQLite source for coordinate packs.")
    parser.add_argument("--major-version", type=int, required=True)
    parser.add_argument("--build", default=None, help="Specific build version like 3.80.0.66130")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if int(args.major_version) <= 0:
        raise ValueError(f"Unsupported major version: {args.major_version}")
    all_versions = get_all_versions() if not args.offline else None
    build_input = args.build if args.build else str(args.major_version)
    build_version = resolve_build(
        build_input,
        all_versions=all_versions,
        data_dir=args.data_dir,
        csv_pattern=areatable.CSV_PATTERN,
    ) or build_input
    if build_input.isdigit() and "." not in build_version:
        raise ValueError(f"Unable to resolve major version {build_input}")

    csv_paths = {
        table_module.TABLE_NAME: ensure_csv(
            table_module,
            build_version,
            args.data_dir,
            not args.offline,
        )
        for table_module in DBC_TABLES
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()

    with sqlite3.connect(args.out) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)", ("build", build_version))
        conn.execute("INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)", ("major_version", str(args.major_version)))
        conn.execute("INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)", ("flavor", flavor_for_major_version(args.major_version)))
        conn.execute("INSERT OR REPLACE INTO db_meta (key, value) VALUES (?, ?)", ("source", "dbc-minimal"))
        for table_module in DBC_TABLES:
            row_count = table_module.build_table(
                conn,
                csv_paths[table_module.TABLE_NAME],
                str(args.major_version),
            )
            print(f"Loaded {row_count} {table_module.TABLE_NAME} rows")
        conn.commit()

    print(f"Built standalone DBC source DB at {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
