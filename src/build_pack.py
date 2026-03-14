from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .manual_overrides import (
    MANUAL_LEGACY_BASIS_OVERRIDES_BY_FLAVOR,
    MANUAL_LEGACY_KEY_ALIASES_BY_FLAVOR,
)
from .models import (
    CURRENT_SCHEMA_VERSION,
    InstanceAnchorRecord,
    LegacyCoordinateBasisRecord,
    MapDefaultRecord,
    CoordinatePack,
    ProjectionBoundsRecord,
    ZoneSpaceRecord,
)
from .ui_map_selection import (
    CoordUiMapCandidate,
    UiMapMeta,
    bounds_area_from_regions,
    primary_ui_map_sort_key,
    select_coord_ui_map_id,
)


FLAVOR_BY_MAJOR_VERSION = {
    1: "classic",
    2: "tbc",
    3: "wotlk",
}
LEGACY_TRANSFORM_IDENTITY = "identity"
LEGACY_TRANSFORM_REPROJECT = "reproject"
LEGACY_SOURCE_KIND_ZONE_BOUNDS = "zone_bounds"
LEGACY_SOURCE_KIND_DIRECT_AREA_BOUNDS = "direct_area_bounds"
LEGACY_SOURCE_KIND_CONTAINING_MAP_BOUNDS = "containing_map_bounds"
LEGACY_SOURCE_KIND_INHERITED_PARENT_BASIS = "inherited_parent_basis"
LEGACY_SOURCE_KIND_INSTANCE_MAP_ALIAS = "instance_map_alias"


def build_coordinate_pack(
    major_version: int,
    dbc_db_path: str | Path | None = None,
) -> CoordinatePack:
    flavor = FLAVOR_BY_MAJOR_VERSION.get(int(major_version))
    if flavor is None:
        raise ValueError(f"Unsupported major version: {major_version}")

    db_path = Path(dbc_db_path) if dbc_db_path else Path(f"dbc-source-v{major_version}.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ui_map_meta = _load_ui_map_meta(conn)
        map_rows = _load_map_rows(conn)
        area_rows = _load_area_rows(conn)
        projection_bounds = _build_projection_bounds(conn, ui_map_meta)
        zone_spaces = _build_zone_spaces(conn, ui_map_meta, area_rows)
        map_defaults = _build_map_defaults(conn, ui_map_meta, map_rows)
        legacy_bases = _build_legacy_coordinate_bases(
            flavor=flavor,
            area_rows=area_rows,
            map_rows=map_rows,
            zone_spaces=zone_spaces,
            map_defaults=map_defaults,
            projection_bounds=projection_bounds,
            conn=conn,
        )
    finally:
        conn.close()

    return CoordinatePack(
        flavor=flavor,
        schema_version=CURRENT_SCHEMA_VERSION,
        zone_spaces=tuple(sorted(zone_spaces, key=lambda row: row.zone_area_id)),
        projection_bounds=tuple(sorted(projection_bounds, key=lambda row: (row.map_id, row.ui_map_id))),
        map_defaults=tuple(sorted(map_defaults, key=lambda row: row.map_id)),
        legacy_bases=tuple(sorted(legacy_bases, key=lambda row: row.legacy_key)),
        instance_anchors=tuple(),
    )


def _load_ui_map_meta(conn: sqlite3.Connection) -> dict[int, UiMapMeta]:
    meta: dict[int, UiMapMeta] = {}
    for row in conn.execute('SELECT "ID", "ParentUiMapID", "Type", "System" FROM ui_map'):
        meta[int(row["ID"])] = UiMapMeta(
            parent=int(row["ParentUiMapID"]) if row["ParentUiMapID"] not in (None, 0) else None,
            map_type=int(row["Type"]) if row["Type"] is not None else None,
            system=int(row["System"]) if row["System"] is not None else None,
        )
    return meta


def _load_map_rows(conn: sqlite3.Connection) -> dict[int, dict[str, int | None]]:
    rows: dict[int, dict[str, int | None]] = {}
    for row in conn.execute('SELECT "ID", "MapType", "InstanceType", "AreaTableID", "ParentMapID" FROM map'):
        rows[int(row["ID"])] = {
            "map_type": int(row["MapType"]) if row["MapType"] is not None else None,
            "instance_type": int(row["InstanceType"]) if row["InstanceType"] is not None else None,
            "area_table_id": int(row["AreaTableID"]) if row["AreaTableID"] not in (None, 0) else None,
            "parent_map_id": int(row["ParentMapID"]) if row["ParentMapID"] not in (None, -1) else None,
        }
    return rows


def _load_area_rows(conn: sqlite3.Connection) -> dict[int, dict[str, int]]:
    rows: dict[int, dict[str, int]] = {}
    for row in conn.execute('SELECT "ID", "ContinentID", "ParentAreaID" FROM area_table'):
        rows[int(row["ID"])] = {
            "map_id": int(row["ContinentID"] or 0),
            "parent_id": int(row["ParentAreaID"] or 0),
        }
    return rows


def _build_projection_bounds(
    conn: sqlite3.Connection,
    ui_map_meta: dict[int, UiMapMeta],
) -> list[ProjectionBoundsRecord]:
    best_by_key: dict[tuple[int, int], tuple[tuple[int, int, float, int, int], ProjectionBoundsRecord]] = {}
    for row in conn.execute(
        'SELECT "MapID", "UiMapID", "AreaID", "OrderIndex", "Region_0", "Region_1", "Region_3", "Region_4" '
        "FROM ui_map_assignment WHERE \"MapID\" IS NOT NULL AND \"UiMapID\" IS NOT NULL"
    ):
        map_id = int(row["MapID"])
        ui_map_id = int(row["UiMapID"])
        area_id = int(row["AreaID"]) if row["AreaID"] not in (None, 0) else None
        world_x_min = min(float(row["Region_0"]), float(row["Region_3"]))
        world_x_max = max(float(row["Region_0"]), float(row["Region_3"]))
        world_y_min = min(float(row["Region_1"]), float(row["Region_4"]))
        world_y_max = max(float(row["Region_1"]), float(row["Region_4"]))
        meta = ui_map_meta.get(ui_map_id)
        area = bounds_area_from_regions(
            float(row["Region_0"]),
            float(row["Region_1"]),
            float(row["Region_3"]),
            float(row["Region_4"]),
        )
        sort_key = primary_ui_map_sort_key(
            ui_map_id=ui_map_id,
            ui_map_meta=meta,
            area=area,
            order_index=int(row["OrderIndex"]) if row["OrderIndex"] is not None else None,
        )
        record = ProjectionBoundsRecord(
            map_id=map_id,
            ui_map_id=ui_map_id,
            parent_ui_map_id=_normalize_parent_ui_map_id(meta.parent if meta else None),
            area_id=area_id,
            world_x_min=world_x_min,
            world_x_max=world_x_max,
            world_y_min=world_y_min,
            world_y_max=world_y_max,
        )
        key = (map_id, ui_map_id)
        current = best_by_key.get(key)
        if current is None or sort_key < current[0]:
            best_by_key[key] = (sort_key, record)
    return [value[1] for value in best_by_key.values()]


def _build_zone_spaces(
    conn: sqlite3.Connection,
    ui_map_meta: dict[int, UiMapMeta],
    area_rows: dict[int, dict[str, int]],
) -> list[ZoneSpaceRecord]:
    candidates_by_area: dict[int, list[tuple[tuple[int, int, float, int, int], ZoneSpaceRecord]]] = {}
    for row in conn.execute(
        'SELECT "MapID", "UiMapID", "AreaID", "OrderIndex", "Region_0", "Region_1", "Region_3", "Region_4" '
        'FROM ui_map_assignment WHERE "AreaID" IS NOT NULL AND "AreaID" != 0'
    ):
        area_id = int(row["AreaID"])
        if area_rows.get(area_id, {}).get("parent_id", 0) != 0:
            continue
        ui_map_id = int(row["UiMapID"])
        meta = ui_map_meta.get(ui_map_id)
        if meta is None or meta.map_type != 3:
            continue
        world_x_min = min(float(row["Region_0"]), float(row["Region_3"]))
        world_x_max = max(float(row["Region_0"]), float(row["Region_3"]))
        world_y_min = min(float(row["Region_1"]), float(row["Region_4"]))
        world_y_max = max(float(row["Region_1"]), float(row["Region_4"]))
        area = bounds_area_from_regions(
            float(row["Region_0"]),
            float(row["Region_1"]),
            float(row["Region_3"]),
            float(row["Region_4"]),
        )
        sort_key = primary_ui_map_sort_key(
            ui_map_id=ui_map_id,
            ui_map_meta=meta,
            area=area,
            order_index=int(row["OrderIndex"]) if row["OrderIndex"] is not None else None,
        )
        record = ZoneSpaceRecord(
            zone_area_id=area_id,
            map_id=int(row["MapID"]),
            zone_ui_map_id=ui_map_id,
            parent_ui_map_id=_normalize_parent_ui_map_id(meta.parent),
            world_x_min=world_x_min,
            world_x_max=world_x_max,
            world_y_min=world_y_min,
            world_y_max=world_y_max,
        )
        candidates_by_area.setdefault(area_id, []).append((sort_key, record))
    return [sorted(candidates, key=lambda item: item[0])[0][1] for candidates in candidates_by_area.values()]


def _build_map_defaults(
    conn: sqlite3.Connection,
    ui_map_meta: dict[int, UiMapMeta],
    map_rows: dict[int, dict[str, int | None]],
) -> list[MapDefaultRecord]:
    rows_by_map_id: dict[int, list[CoordUiMapCandidate]] = {}
    for row in conn.execute(
        'SELECT "MapID", "UiMapID", "AreaID", "OrderIndex", "Region_0", "Region_1", "Region_3", "Region_4" '
        'FROM ui_map_assignment WHERE "MapID" IS NOT NULL AND "UiMapID" IS NOT NULL'
    ):
        map_id = int(row["MapID"])
        rows_by_map_id.setdefault(map_id, []).append(
            {
                "ui_map_id": int(row["UiMapID"]),
                "area_id": int(row["AreaID"]) if row["AreaID"] not in (None, 0) else None,
                "order_index": int(row["OrderIndex"]) if row["OrderIndex"] is not None else None,
                "area": float(
                    bounds_area_from_regions(
                        float(row["Region_0"]),
                        float(row["Region_1"]),
                        float(row["Region_3"]),
                        float(row["Region_4"]),
                    )
                ),
            }
        )
    results: list[MapDefaultRecord] = []
    for map_id, candidates in rows_by_map_id.items():
        selected = select_coord_ui_map_id(
            candidates,
            ui_map_meta,
            map_rows.get(map_id, {}).get("instance_type"),
        )
        if selected is not None:
            results.append(MapDefaultRecord(map_id=map_id, coord_ui_map_id=int(selected)))
    return results


def _build_legacy_coordinate_bases(
    flavor: str,
    area_rows: dict[int, dict[str, int]],
    map_rows: dict[int, dict[str, int | None]],
    zone_spaces: list[ZoneSpaceRecord],
    map_defaults: list[MapDefaultRecord],
    projection_bounds: list[ProjectionBoundsRecord],
    conn: sqlite3.Connection,
) -> list[LegacyCoordinateBasisRecord]:
    records_by_key: dict[int, LegacyCoordinateBasisRecord] = {}
    map_defaults_by_map_id = {int(record.map_id): int(record.coord_ui_map_id) for record in map_defaults}

    for zone_space in zone_spaces:
        target_coord_ui_map_id = _target_coord_ui_map_id_for_zone_space(map_defaults_by_map_id, zone_space)
        records_by_key[int(zone_space.zone_area_id)] = _make_legacy_basis_record(
            legacy_key=int(zone_space.zone_area_id),
            map_id=int(zone_space.map_id),
            source_coord_ui_map_id=int(zone_space.zone_ui_map_id),
            target_coord_ui_map_id=int(target_coord_ui_map_id),
            source_kind=LEGACY_SOURCE_KIND_ZONE_BOUNDS,
        )

    for record in _build_direct_area_legacy_bases(conn, map_defaults_by_map_id):
        records_by_key.setdefault(int(record.legacy_key), record)

    for record in _build_unresolved_instance_aliases(area_rows, map_rows, map_defaults_by_map_id):
        records_by_key.setdefault(int(record.legacy_key), record)

    _apply_manual_basis_overrides(flavor, records_by_key)
    _add_inherited_parent_legacy_bases(records_by_key, area_rows)
    _apply_manual_key_aliases(flavor, records_by_key)
    _drop_degenerate_reprojects(records_by_key, projection_bounds)
    return list(records_by_key.values())


def _build_direct_area_legacy_bases(
    conn: sqlite3.Connection,
    map_defaults_by_map_id: dict[int, int],
) -> list[LegacyCoordinateBasisRecord]:
    records_by_area_id: dict[int, LegacyCoordinateBasisRecord] = {}
    for row in conn.execute(
        'SELECT "MapID", "UiMapID", "AreaID", "Region_0", "Region_1", "Region_3", "Region_4" '
        'FROM ui_map_assignment WHERE "MapID" IS NOT NULL AND "UiMapID" IS NOT NULL '
        'AND "AreaID" IS NOT NULL AND "AreaID" != 0'
    ):
        area_id = int(row["AreaID"])
        map_id = int(row["MapID"])
        source_coord_ui_map_id = int(row["UiMapID"])
        world_x_min = min(float(row["Region_0"]), float(row["Region_3"]))
        world_x_max = max(float(row["Region_0"]), float(row["Region_3"]))
        world_y_min = min(float(row["Region_1"]), float(row["Region_4"]))
        world_y_max = max(float(row["Region_1"]), float(row["Region_4"]))
        if world_x_min == world_x_max or world_y_min == world_y_max:
            continue
        target_coord_ui_map_id = int(map_defaults_by_map_id.get(map_id, source_coord_ui_map_id))
        candidate = _make_legacy_basis_record(
            legacy_key=area_id,
            map_id=map_id,
            source_coord_ui_map_id=source_coord_ui_map_id,
            target_coord_ui_map_id=target_coord_ui_map_id,
            source_kind=LEGACY_SOURCE_KIND_DIRECT_AREA_BOUNDS,
        )
        current = records_by_area_id.get(area_id)
        if current is None:
            records_by_area_id[area_id] = candidate
            continue
        if int(candidate.source_coord_ui_map_id) == int(candidate.target_coord_ui_map_id):
            records_by_area_id[area_id] = candidate
    return list(records_by_area_id.values())


def _build_unresolved_instance_aliases(
    area_rows: dict[int, dict[str, int]],
    map_rows: dict[int, dict[str, int | None]],
    map_defaults_by_map_id: dict[int, int],
) -> list[LegacyCoordinateBasisRecord]:
    records_by_area_id: dict[int, LegacyCoordinateBasisRecord] = {}
    for area_id, area_row in area_rows.items():
        if int(area_row["parent_id"]) != 0:
            continue
        map_id = int(area_row["map_id"])
        if map_id <= 1:
            continue
        map_row = map_rows.get(map_id)
        if map_row is None:
            continue
        if not _is_unresolved_instance_like_map(map_row):
            continue
        records_by_area_id.setdefault(
            int(area_id),
            _make_legacy_basis_record(
                legacy_key=int(area_id),
                map_id=map_id,
                source_coord_ui_map_id=0,
                target_coord_ui_map_id=0,
                source_kind=LEGACY_SOURCE_KIND_INSTANCE_MAP_ALIAS,
            ),
        )
    for map_id, map_row in map_rows.items():
        area_id = map_row.get("area_table_id")
        if area_id in (None, 0):
            continue
        if not _is_unresolved_instance_like_map(map_row):
            continue
        records_by_area_id.setdefault(
            int(area_id),
            _make_legacy_basis_record(
                legacy_key=int(area_id),
                map_id=int(map_id),
                source_coord_ui_map_id=0,
                target_coord_ui_map_id=0,
                source_kind=LEGACY_SOURCE_KIND_INSTANCE_MAP_ALIAS,
            ),
        )
    return list(records_by_area_id.values())


def _is_unresolved_instance_like_map(map_row: dict[str, int | None]) -> bool:
    return (
        map_row.get("instance_type") not in (None, 0)
        or map_row.get("map_type") in (2, 3)
    )


def _apply_manual_basis_overrides(
    flavor: str,
    records_by_key: dict[int, LegacyCoordinateBasisRecord],
) -> None:
    for legacy_key, override in MANUAL_LEGACY_BASIS_OVERRIDES_BY_FLAVOR.get(flavor, {}).items():
        records_by_key[int(legacy_key)] = _make_legacy_basis_record(
            legacy_key=int(override.legacy_key),
            map_id=int(override.map_id),
            source_coord_ui_map_id=int(override.source_coord_ui_map_id),
            target_coord_ui_map_id=int(override.target_coord_ui_map_id),
            source_kind=str(override.source_kind),
            default_ui_map_hint_id=override.default_ui_map_hint_id,
        )


def _apply_manual_key_aliases(
    flavor: str,
    records_by_key: dict[int, LegacyCoordinateBasisRecord],
) -> None:
    for legacy_key, canonical_key in MANUAL_LEGACY_KEY_ALIASES_BY_FLAVOR.get(flavor, {}).items():
        if int(legacy_key) in records_by_key:
            continue
        canonical = records_by_key.get(int(canonical_key))
        if canonical is None:
            continue
        records_by_key[int(legacy_key)] = LegacyCoordinateBasisRecord(
            legacy_key=int(legacy_key),
            map_id=int(canonical.map_id),
            source_coord_ui_map_id=int(canonical.source_coord_ui_map_id),
            target_coord_ui_map_id=int(canonical.target_coord_ui_map_id),
            transform=str(canonical.transform),
            source_kind=str(canonical.source_kind),
            default_ui_map_hint_id=canonical.default_ui_map_hint_id,
        )


def _add_inherited_parent_legacy_bases(
    records_by_key: dict[int, LegacyCoordinateBasisRecord],
    area_rows: dict[int, dict[str, int]],
) -> None:
    changed = True
    while changed:
        changed = False
        for area_id in sorted(area_rows):
            if area_id in records_by_key:
                continue
            parent_id = int(area_rows[area_id]["parent_id"])
            if parent_id <= 0:
                continue
            parent_record = records_by_key.get(parent_id)
            if parent_record is None:
                continue
            if int(parent_record.map_id) != int(area_rows[area_id]["map_id"]):
                continue
            records_by_key[int(area_id)] = LegacyCoordinateBasisRecord(
                legacy_key=int(area_id),
                map_id=int(parent_record.map_id),
                source_coord_ui_map_id=int(parent_record.source_coord_ui_map_id),
                target_coord_ui_map_id=int(parent_record.target_coord_ui_map_id),
                transform=str(parent_record.transform),
                source_kind=LEGACY_SOURCE_KIND_INHERITED_PARENT_BASIS,
                default_ui_map_hint_id=None,
            )
            changed = True


def _drop_degenerate_reprojects(
    records_by_key: dict[int, LegacyCoordinateBasisRecord],
    projection_bounds: list[ProjectionBoundsRecord],
) -> None:
    bounds_by_key = {
        (int(record.map_id), int(record.ui_map_id)): record
        for record in projection_bounds
    }
    for legacy_key, record in list(records_by_key.items()):
        if str(record.transform) != LEGACY_TRANSFORM_REPROJECT:
            continue
        source = bounds_by_key.get((int(record.map_id), int(record.source_coord_ui_map_id)))
        target = bounds_by_key.get((int(record.map_id), int(record.target_coord_ui_map_id)))
        if source is None or target is None:
            continue
        if _is_degenerate_bounds(source) and not _is_degenerate_bounds(target):
            records_by_key[int(legacy_key)] = _make_legacy_basis_record(
                legacy_key=int(record.legacy_key),
                map_id=int(record.map_id),
                source_coord_ui_map_id=int(record.target_coord_ui_map_id),
                target_coord_ui_map_id=int(record.target_coord_ui_map_id),
                source_kind=LEGACY_SOURCE_KIND_CONTAINING_MAP_BOUNDS,
                default_ui_map_hint_id=record.default_ui_map_hint_id,
            )


def _is_degenerate_bounds(record: ProjectionBoundsRecord) -> bool:
    return (
        float(record.world_x_min) == float(record.world_x_max)
        or float(record.world_y_min) == float(record.world_y_max)
    )


def _make_legacy_basis_record(
    legacy_key: int,
    map_id: int,
    source_coord_ui_map_id: int,
    target_coord_ui_map_id: int,
    source_kind: str,
    default_ui_map_hint_id: int | None = None,
) -> LegacyCoordinateBasisRecord:
    return LegacyCoordinateBasisRecord(
        legacy_key=int(legacy_key),
        map_id=int(map_id),
        source_coord_ui_map_id=int(source_coord_ui_map_id),
        target_coord_ui_map_id=int(target_coord_ui_map_id),
        transform=(
            LEGACY_TRANSFORM_IDENTITY
            if int(source_coord_ui_map_id) == int(target_coord_ui_map_id)
            else LEGACY_TRANSFORM_REPROJECT
        ),
        source_kind=str(source_kind),
        default_ui_map_hint_id=default_ui_map_hint_id,
    )


def _target_coord_ui_map_id_for_zone_space(
    map_defaults_by_map_id: dict[int, int],
    zone_space: ZoneSpaceRecord,
) -> int:
    coord_ui_map_id = map_defaults_by_map_id.get(int(zone_space.map_id))
    if coord_ui_map_id is not None:
        return int(coord_ui_map_id)
    if zone_space.parent_ui_map_id is not None:
        return int(zone_space.parent_ui_map_id)
    return int(zone_space.zone_ui_map_id)


def _normalize_parent_ui_map_id(parent_ui_map_id: int | None) -> int | None:
    if parent_ui_map_id in (None, 0):
        return None
    return int(parent_ui_map_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build standalone coordinate packs.")
    parser.add_argument("--major-version", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--dbc-db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    pack = build_coordinate_pack(
        major_version=args.major_version,
        dbc_db_path=args.dbc_db,
    )
    pack.dump(args.output_dir)
    print(f"Wrote standalone coordinate pack to {args.output_dir}")


if __name__ == "__main__":
    main()
