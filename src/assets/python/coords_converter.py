from __future__ import annotations

from collections import defaultdict
from typing import Any


UNKNOWN_COORD_UI_MAP_ID = 0
UNKNOWN_COORD_POINT = (-1.0, -1.0)
# Tiny runtime escape hatches for legacy keys that do not fit normal
# basis/reprojection logic.
MANUAL_FIXED_POINT_OVERRIDES_BY_FLAVOR = {
    "classic": {
        10089: {
            "mapId": 1,
            "coordUiMapId": 1414,
            "sourceX": 29.99,
            "sourceY": 89.15,
            "targetX": 70.58,
            "targetY": 96.19,
        },
    },
    "tbc": {
        10089: {
            "mapId": 1,
            "coordUiMapId": 1414,
            "sourceX": 29.99,
            "sourceY": 89.15,
            "targetX": 70.58,
            "targetY": 96.19,
        },
    },
    "wotlk": {
        10089: {
            "mapId": 1,
            "coordUiMapId": 1414,
            "sourceX": 29.99,
            "sourceY": 89.15,
            "targetX": 77.11,
            "targetY": 88.84,
        },
    },
    "cata": {
        10089: {
            "mapId": 1,
            "coordUiMapId": 1414,
            "sourceX": 29.99,
            "sourceY": 89.15,
            "targetX": 77.11,
            "targetY": 88.84,
        },
    },
    "mop": {
        10089: {
            "mapId": 1,
            "coordUiMapId": 1414,
            "sourceX": 29.99,
            "sourceY": 89.15,
            "targetX": 77.11,
            "targetY": 88.84,
        },
    },
}


def convert_zone_buckets(
    pack: dict[str, Any],
    zone_buckets: dict[int, list[list[float]]],
    coord_decimals: int = 2,
) -> dict[int, dict[int, list[list[float | int]]]]:
    result: dict[int, dict[int, list[list[float | int]]]] = defaultdict(lambda: defaultdict(list))
    fixed_point_overrides = MANUAL_FIXED_POINT_OVERRIDES_BY_FLAVOR.get(
        str(pack["manifest"]["flavor"]),
        {},
    )

    for zone_area_id, points in zone_buckets.items():
        if _apply_manual_fixed_point_override(
            result=result,
            fixed_point_overrides=fixed_point_overrides,
            zone_area_id=int(zone_area_id),
            points=points,
            coord_decimals=coord_decimals,
        ):
            continue

        legacy_basis = pack["legacyBasisByKey"].get(int(zone_area_id))
        zone_space = pack["zoneSpaceByAreaId"].get(int(zone_area_id))
        if legacy_basis is None and zone_space is None:
            raise KeyError(f"No coordinate mapping for legacy key={zone_area_id}")

        if legacy_basis is not None:
            map_id = int(legacy_basis["mapId"])
            target_ui_map_id = int(legacy_basis["targetCoordUiMapId"])
            target_bounds = (
                None
                if target_ui_map_id == UNKNOWN_COORD_UI_MAP_ID
                else _get_projection_bounds(pack, map_id, target_ui_map_id)
            )
        else:
            map_id = int(zone_space["mapId"])
            target_ui_map_id = _target_coord_ui_map_id(pack, zone_space)
            target_bounds = _get_projection_bounds(pack, map_id, target_ui_map_id)

        for point in points:
            if len(point) < 2:
                raise ValueError(
                    f"Expected coordinate pair for zoneAreaId={zone_area_id}, got {point!r}"
                )
            if _should_emit_unknown_instance_bucket(pack, int(zone_area_id), map_id, point):
                result[map_id][UNKNOWN_COORD_UI_MAP_ID].append(
                    [UNKNOWN_COORD_POINT[0], UNKNOWN_COORD_POINT[1]]
                )
                continue
            x, y = _convert_legacy_point(
                pack=pack,
                legacy_basis=legacy_basis,
                zone_space=zone_space,
                target_bounds=target_bounds,
                point=point,
            )
            coord_pair: list[float | int] = [round(x, coord_decimals), round(y, coord_decimals)]
            hint_ui_map_id = (
                int(legacy_basis["defaultUiMapHintId"])
                if legacy_basis is not None and legacy_basis.get("defaultUiMapHintId") is not None
                else None
            )
            if hint_ui_map_id is not None:
                coord_pair.append(hint_ui_map_id)
            result[map_id][target_ui_map_id].append(coord_pair)

    return {
        int(map_id): {
            int(coord_ui_map_id): list(coords)
            for coord_ui_map_id, coords in coord_buckets.items()
        }
        for map_id, coord_buckets in result.items()
    }


def _apply_manual_fixed_point_override(
    *,
    result: dict[int, dict[int, list[list[float | int]]]],
    fixed_point_overrides: dict[int, dict[str, float | int]],
    zone_area_id: int,
    points: list[list[float]],
    coord_decimals: int,
) -> bool:
    fixed_point = fixed_point_overrides.get(int(zone_area_id))
    if fixed_point is None:
        return False

    # Only the known researched source point is accepted here. Anything else
    # should still fail loudly instead of being treated as a generic remap.
    bucket = result[int(fixed_point["mapId"])][int(fixed_point["coordUiMapId"])]
    for point in points:
        if len(point) < 2:
            raise ValueError(
                f"Expected coordinate pair for zoneAreaId={zone_area_id}, got {point!r}"
            )
        if (
            round(float(point[0]), 2) != round(float(fixed_point["sourceX"]), 2)
            or round(float(point[1]), 2) != round(float(fixed_point["sourceY"]), 2)
        ):
            raise ValueError(
                f"Legacy key={zone_area_id} only supports the known fixed point "
                f"({fixed_point['sourceX']}, {fixed_point['sourceY']})"
            )
        bucket.append(
            [
                round(float(fixed_point["targetX"]), coord_decimals),
                round(float(fixed_point["targetY"]), coord_decimals),
            ]
        )
    return True


def replace_unknown_instance_buckets(
    pack: dict[str, Any],
    map_buckets: dict[int, dict[int, list[list[float | int]]]],
) -> dict[int, dict[int, list[list[float | int]]]]:
    result: dict[int, dict[int, list[list[float | int]]]] = defaultdict(lambda: defaultdict(list))

    for map_id, coord_buckets in map_buckets.items():
        normalized = {
            int(coord_ui_map_id): [_normalize_point(point) for point in points]
            for coord_ui_map_id, points in coord_buckets.items()
        }
        anchor_record = pack["instanceAnchorByMapId"].get(int(map_id))
        if (
            anchor_record is not None
            and len(normalized) == 1
            and _is_unknown_bucket(normalized.get(UNKNOWN_COORD_UI_MAP_ID))
        ):
            for bucket in anchor_record["entrances"]:
                bucket_map_id = int(bucket["mapId"])
                bucket_coord_ui_map_id = int(bucket["coordUiMapId"])
                result[bucket_map_id][bucket_coord_ui_map_id].extend(
                    [[float(point[0]), float(point[1])] for point in bucket["points"]]
                )
        else:
            for coord_ui_map_id, points in normalized.items():
                result[int(map_id)][int(coord_ui_map_id)].extend(points)

    return {
        int(map_id): {
            int(coord_ui_map_id): list(points)
            for coord_ui_map_id, points in coord_buckets.items()
        }
        for map_id, coord_buckets in result.items()
    }


def invert_zone_percent_to_world(
    zone_space: dict[str, Any],
    zone_x: float,
    zone_y: float,
) -> tuple[float, float]:
    dx = float(zone_space["worldXMax"]) - float(zone_space["worldXMin"])
    dy = float(zone_space["worldYMax"]) - float(zone_space["worldYMin"])
    if dx == 0 or dy == 0:
        source_label = (
            f"zoneAreaId={zone_space['zoneAreaId']}"
            if "zoneAreaId" in zone_space
            else f"mapId={zone_space['mapId']}, uiMapId={zone_space['uiMapId']}"
        )
        raise ValueError(
            f"Degenerate source bounds for {source_label}"
        )

    world_y = float(zone_space["worldYMax"]) - (zone_x / 100.0) * dy
    world_x = float(zone_space["worldXMax"]) - (zone_y / 100.0) * dx
    return world_x, world_y


def _convert_legacy_point(
    pack: dict[str, Any],
    legacy_basis: dict[str, Any] | None,
    zone_space: dict[str, Any] | None,
    target_bounds: dict[str, Any] | None,
    point: list[float],
) -> tuple[float, float]:
    if legacy_basis is not None:
        if int(legacy_basis["targetCoordUiMapId"]) == UNKNOWN_COORD_UI_MAP_ID:
            if (
                legacy_basis["transform"] == "identity"
                and len(point) >= 2
                and float(point[0]) == UNKNOWN_COORD_POINT[0]
                and float(point[1]) == UNKNOWN_COORD_POINT[1]
            ):
                return UNKNOWN_COORD_POINT
            raise ValueError(
                f"Legacy key={legacy_basis['legacyKey']} maps to unresolved instance space; "
                "only {-1,-1} sentinel points are supported"
            )
        if legacy_basis["transform"] == "identity":
            return float(point[0]), float(point[1])

        source_bounds = _get_projection_bounds(
            pack,
            int(legacy_basis["mapId"]),
            int(legacy_basis["sourceCoordUiMapId"]),
        )
        assert target_bounds is not None
        world_x, world_y = invert_zone_percent_to_world(
            zone_space=source_bounds,
            zone_x=float(point[0]),
            zone_y=float(point[1]),
        )
        return project_world_to_percent(
            bounds=target_bounds,
            world_x=world_x,
            world_y=world_y,
        )

    assert zone_space is not None
    assert target_bounds is not None
    world_x, world_y = invert_zone_percent_to_world(
        zone_space=zone_space,
        zone_x=float(point[0]),
        zone_y=float(point[1]),
    )
    return project_world_to_percent(
        bounds=target_bounds,
        world_x=world_x,
        world_y=world_y,
    )


def project_world_to_percent(
    bounds: dict[str, Any],
    world_x: float,
    world_y: float,
) -> tuple[float, float]:
    dx = float(bounds["worldXMax"]) - float(bounds["worldXMin"])
    dy = float(bounds["worldYMax"]) - float(bounds["worldYMin"])
    if dx == 0 or dy == 0:
        raise ValueError(
            f"Degenerate target bounds for mapId={bounds['mapId']}, uiMapId={bounds['uiMapId']}"
        )

    x = (float(bounds["worldYMax"]) - world_y) / dy * 100.0
    y = (float(bounds["worldXMax"]) - world_x) / dx * 100.0
    return x, y


def _target_coord_ui_map_id(pack: dict[str, Any], zone_space: dict[str, Any]) -> int:
    map_id = int(zone_space["mapId"])
    coord_ui_map_id = pack["mapDefaultByMapId"].get(map_id)
    if coord_ui_map_id is not None:
        return int(coord_ui_map_id)
    parent_ui_map_id = zone_space.get("parentUiMapId")
    if parent_ui_map_id is not None:
        return int(parent_ui_map_id)
    return int(zone_space["zoneUiMapId"])


def _get_projection_bounds(pack: dict[str, Any], map_id: int, ui_map_id: int) -> dict[str, Any]:
    bounds = pack["projectionBoundsByKey"].get((int(map_id), int(ui_map_id)))
    if bounds is None:
        raise KeyError(f"No projection bounds for mapId={map_id}, uiMapId={ui_map_id}")
    return bounds

def _is_unknown_bucket(points: list[list[float]] | None) -> bool:
    if not points:
        return False
    return all(
        len(point) >= 2
        and float(point[0]) == UNKNOWN_COORD_POINT[0]
        and float(point[1]) == UNKNOWN_COORD_POINT[1]
        for point in points
    )


def _should_emit_unknown_instance_bucket(
    pack: dict[str, Any],
    zone_area_id: int,
    map_id: int,
    point: list[float],
) -> bool:
    if len(point) < 2:
        return False
    return (
        float(point[0]) == UNKNOWN_COORD_POINT[0]
        and float(point[1]) == UNKNOWN_COORD_POINT[1]
    )


def _normalize_point(point: list[float | int]) -> list[float | int]:
    normalized: list[float | int] = [float(point[0]), float(point[1])]
    normalized.extend(point[2:])
    return normalized
