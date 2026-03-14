from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_PARENT_UI_MAP_ID = 947
DEFAULT_POINT_X = 29.99
DEFAULT_POINT_Y = 89.15


@dataclass(frozen=True)
class AliasCandidate:
    major_version: int
    map_id: int
    target_coord_ui_map_id: int | None
    ui_min_x: float
    ui_min_y: float
    ui_max_x: float
    ui_max_y: float
    contains_point: bool
    translated_x: float | None
    translated_y: float | None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect how a parent-map coordinate would translate into child map coordinates."
    )
    parser.add_argument(
        "--major-version",
        type=int,
        action="append",
        dest="major_versions",
        help="Pack major version to inspect. Defaults to all discovered versions.",
    )
    parser.add_argument(
        "--parent-ui-map-id",
        type=int,
        default=DEFAULT_PARENT_UI_MAP_ID,
        help="Parent uiMapId that the fake key is authored against. Default: 947.",
    )
    parser.add_argument(
        "--x",
        type=float,
        default=DEFAULT_POINT_X,
        help="Source X in 0-100 map percent.",
    )
    parser.add_argument(
        "--y",
        type=float,
        default=DEFAULT_POINT_Y,
        help="Source Y in 0-100 map percent.",
    )
    parser.add_argument(
        "--dbc-root",
        type=Path,
        default=Path("dbc-output"),
        help="Directory containing dbc-source-vN.db files.",
    )
    parser.add_argument(
        "--pack-root",
        type=Path,
        default=Path("output"),
        help="Directory containing built output/vN packs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text report.",
    )
    args = parser.parse_args()

    major_versions = args.major_versions or _discover_major_versions(
        dbc_root=args.dbc_root,
        pack_root=args.pack_root,
    )
    if not major_versions:
        raise FileNotFoundError(
            f"No matching dbc-source-vN.db / output/vN data found under {args.dbc_root} and {args.pack_root}"
        )
    all_candidates: list[AliasCandidate] = []

    for major_version in major_versions:
        dbc_db = args.dbc_root / f"dbc-source-v{major_version}.db"
        pack_dir = args.pack_root / f"v{major_version}"
        all_candidates.extend(
            inspect_parent_map_alias(
                major_version=major_version,
                dbc_db=dbc_db,
                pack_dir=pack_dir,
                parent_ui_map_id=int(args.parent_ui_map_id),
                point_x=float(args.x),
                point_y=float(args.y),
            )
        )

    if args.json:
        print(json.dumps([asdict(candidate) for candidate in all_candidates], indent=2))
        return

    _print_report(
        major_versions=major_versions,
        parent_ui_map_id=int(args.parent_ui_map_id),
        point_x=float(args.x),
        point_y=float(args.y),
        candidates=all_candidates,
    )


def _discover_major_versions(*, dbc_root: Path, pack_root: Path) -> list[int]:
    dbc_versions = {
        int(match.group(1))
        for path in dbc_root.glob("dbc-source-v*.db")
        if (match := re.fullmatch(r"dbc-source-v(\d+)\.db", path.name))
    }
    pack_versions = {
        int(match.group(1))
        for path in pack_root.glob("v*")
        if path.is_dir() and (match := re.fullmatch(r"v(\d+)", path.name))
    }
    return sorted(dbc_versions & pack_versions)


def inspect_parent_map_alias(
    *,
    major_version: int,
    dbc_db: Path,
    pack_dir: Path,
    parent_ui_map_id: int,
    point_x: float,
    point_y: float,
) -> list[AliasCandidate]:
    if not dbc_db.exists():
        raise FileNotFoundError(f"Missing DBC DB: {dbc_db}")
    if not pack_dir.exists():
        raise FileNotFoundError(f"Missing pack directory: {pack_dir}")

    map_defaults = {
        int(row["mapId"]): int(row["coordUiMapId"])
        for row in json.loads((pack_dir / "map_defaults.json").read_text(encoding="utf-8"))
    }

    conn = sqlite3.connect(dbc_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = list(
            conn.execute(
                'SELECT "MapID", "UiMin_0", "UiMin_1", "UiMax_0", "UiMax_1" '
                'FROM ui_map_assignment '
                'WHERE "UiMapID" = ? AND "MapID" IS NOT NULL '
                'ORDER BY "MapID"',
                (int(parent_ui_map_id),),
            )
        )
    finally:
        conn.close()

    u = float(point_x) / 100.0
    v = float(point_y) / 100.0
    candidates: list[AliasCandidate] = []
    for row in rows:
        map_id = int(row["MapID"])
        ui_min_x = float(row["UiMin_0"])
        ui_min_y = float(row["UiMin_1"])
        ui_max_x = float(row["UiMax_0"])
        ui_max_y = float(row["UiMax_1"])
        contains = ui_min_x <= u <= ui_max_x and ui_min_y <= v <= ui_max_y
        translated_x: float | None = None
        translated_y: float | None = None
        if contains:
            translated_x = ((u - ui_min_x) / (ui_max_x - ui_min_x)) * 100.0
            translated_y = ((v - ui_min_y) / (ui_max_y - ui_min_y)) * 100.0
        candidates.append(
            AliasCandidate(
                major_version=major_version,
                map_id=map_id,
                target_coord_ui_map_id=map_defaults.get(map_id),
                ui_min_x=ui_min_x,
                ui_min_y=ui_min_y,
                ui_max_x=ui_max_x,
                ui_max_y=ui_max_y,
                contains_point=contains,
                translated_x=translated_x,
                translated_y=translated_y,
            )
        )
    return candidates


def _print_report(
    *,
    major_versions: list[int],
    parent_ui_map_id: int,
    point_x: float,
    point_y: float,
    candidates: list[AliasCandidate],
) -> None:
    print(
        f"parent_ui_map_id={parent_ui_map_id} point=({point_x:.4f}, {point_y:.4f}) versions={major_versions}"
    )
    grouped: dict[int, list[AliasCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.major_version, []).append(candidate)

    for major_version in major_versions:
        print(f"\nv{major_version}")
        version_candidates = grouped.get(major_version, [])
        if not version_candidates:
            print("  no parent-map candidates found")
            continue
        for candidate in version_candidates:
            target = (
                "n/a"
                if candidate.target_coord_ui_map_id is None
                else str(candidate.target_coord_ui_map_id)
            )
            print(
                "  "
                f"mapId={candidate.map_id} targetUiMapId={target} "
                f"rect=({candidate.ui_min_x:.6f},{candidate.ui_min_y:.6f})"
                f"-({candidate.ui_max_x:.6f},{candidate.ui_max_y:.6f}) "
                f"contains={candidate.contains_point}"
            )
            if candidate.contains_point:
                print(
                    "    "
                    f"translated=({candidate.translated_x:.4f}, {candidate.translated_y:.4f})"
                )


if __name__ == "__main__":
    main()
