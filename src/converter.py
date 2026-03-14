from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence

from .manual_overrides import MANUAL_FIXED_POINT_OVERRIDES_BY_FLAVOR
from .models import (
    LegacyCoordinateBasisRecord,
    CoordinatePack,
    ProjectionBoundsRecord,
    ZoneSpaceRecord,
)


UNKNOWN_COORD_UI_MAP_ID = 0
UNKNOWN_COORD_POINT = (-1.0, -1.0)


@dataclass(frozen=True)
class WorldPoint:
    x: float
    y: float


class CoordinateConverter:
    """Reference converter that only depends on a coordinate pack."""

    def __init__(self, pack: CoordinatePack):
        self._pack = pack
        self._zone_spaces = pack.zone_space_by_area_id()
        self._projection_bounds = pack.projection_bounds_by_key()
        self._map_defaults = pack.map_default_by_map_id()
        self._legacy_bases = pack.legacy_basis_by_key()
        self._instance_anchors = pack.instance_anchor_by_map_id()
        self._instance_anchors_by_zone_area = pack.instance_anchor_by_zone_area_id()
        self._manual_fixed_points = MANUAL_FIXED_POINT_OVERRIDES_BY_FLAVOR.get(pack.flavor, {})

    def convert_zone_buckets(
        self,
        zone_buckets: Mapping[int, Sequence[Sequence[float]]],
        coord_decimals: int = 2,
    ) -> dict[int, dict[int, list[list[float | int]]]]:
        """Convert `{zoneAreaId: [[x,y], ...]}` to v2 map/uiMap buckets."""
        result: dict[int, dict[int, list[list[float | int]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for zone_area_id, points in zone_buckets.items():
            if self._apply_manual_fixed_point_override(
                result=result,
                zone_area_id=int(zone_area_id),
                points=points,
                coord_decimals=coord_decimals,
            ):
                continue

            legacy_basis = self._legacy_bases.get(int(zone_area_id))
            zone_space = self._zone_spaces.get(int(zone_area_id))
            if legacy_basis is None and zone_space is None:
                raise KeyError(
                    f"No coordinate mapping for legacy key={zone_area_id}"
                )

            if legacy_basis is not None:
                map_id = int(legacy_basis.map_id)
                target_ui_map_id = int(legacy_basis.target_coord_ui_map_id)
            else:
                assert zone_space is not None
                map_id = int(zone_space.map_id)
                target_ui_map_id = self._target_coord_ui_map_id(zone_space)
            target_bounds: ProjectionBoundsRecord | None = None

            for point in points:
                if len(point) < 2:
                    raise ValueError(
                        f"Expected coordinate pair for zoneAreaId={zone_area_id}, got {point!r}"
                    )
                if self._should_emit_unknown_instance_bucket(
                    zone_area_id=int(zone_area_id),
                    map_id=map_id,
                    point=point,
                ):
                    result[map_id][UNKNOWN_COORD_UI_MAP_ID].append(
                        [UNKNOWN_COORD_POINT[0], UNKNOWN_COORD_POINT[1]]
                    )
                    continue
                if target_ui_map_id != UNKNOWN_COORD_UI_MAP_ID and target_bounds is None:
                    target_bounds = self._get_projection_bounds(map_id, target_ui_map_id)
                x, y = self._convert_legacy_point(
                    legacy_basis=legacy_basis,
                    zone_space=zone_space,
                    target_bounds=target_bounds,
                    point=point,
                )
                coord_pair: list[float | int] = [round(x, coord_decimals), round(y, coord_decimals)]
                hint_ui_map_id = (
                    int(legacy_basis.default_ui_map_hint_id)
                    if legacy_basis is not None and legacy_basis.default_ui_map_hint_id is not None
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

    def replace_unknown_instance_buckets(
        self,
        map_buckets: Mapping[int, Mapping[int, Sequence[Sequence[float]]]],
    ) -> dict[int, dict[int, list[list[float | int]]]]:
        """Replace unresolved `[mapId][0]={{-1,-1}}` buckets with anchors."""
        result: dict[int, dict[int, list[list[float | int]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for map_id, coord_buckets in map_buckets.items():
            normalized = {
                int(coord_ui_map_id): [self._normalize_point(point) for point in points]
                for coord_ui_map_id, points in coord_buckets.items()
            }
            anchor_record = self._instance_anchors.get(int(map_id))
            if (
                anchor_record is not None
                and len(normalized) == 1
                and self._is_unknown_bucket(normalized.get(UNKNOWN_COORD_UI_MAP_ID))
            ):
                for bucket in anchor_record.entrances:
                    result[int(bucket.map_id)][int(bucket.coord_ui_map_id)].extend(
                        [[x, y] for x, y in bucket.points]
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

    def _apply_manual_fixed_point_override(
        self,
        *,
        result: dict[int, dict[int, list[list[float | int]]]],
        zone_area_id: int,
        points: Sequence[Sequence[float]],
        coord_decimals: int,
    ) -> bool:
        fixed_point = self._manual_fixed_points.get(int(zone_area_id))
        if fixed_point is None:
            return False

        # These are intentionally tiny, flavor-scoped escape hatches for legacy
        # keys that do not fit the normal basis/reprojection model.
        bucket = result[int(fixed_point.map_id)][int(fixed_point.coord_ui_map_id)]
        for point in points:
            if len(point) < 2:
                raise ValueError(
                    f"Expected coordinate pair for zoneAreaId={zone_area_id}, got {point!r}"
                )
            # Match only the one researched source point so this path cannot
            # silently start acting like a generic remapping rule.
            if (
                round(float(point[0]), 2) != round(float(fixed_point.source_x), 2)
                or round(float(point[1]), 2) != round(float(fixed_point.source_y), 2)
            ):
                raise ValueError(
                    f"Legacy key={zone_area_id} only supports the known fixed point "
                    f"({fixed_point.source_x}, {fixed_point.source_y})"
                )
            bucket.append(
                [
                    round(float(fixed_point.target_x), coord_decimals),
                    round(float(fixed_point.target_y), coord_decimals),
                ]
            )
        return True

    def _target_coord_ui_map_id(self, zone_space: ZoneSpaceRecord) -> int:
        coord_ui_map_id = self._map_defaults.get(zone_space.map_id)
        if coord_ui_map_id is not None:
            return int(coord_ui_map_id)
        if zone_space.parent_ui_map_id is not None:
            return int(zone_space.parent_ui_map_id)
        return int(zone_space.zone_ui_map_id)

    def _convert_legacy_point(
        self,
        legacy_basis: LegacyCoordinateBasisRecord | None,
        zone_space: ZoneSpaceRecord | None,
        target_bounds: ProjectionBoundsRecord | None,
        point: Sequence[float],
    ) -> tuple[float, float]:
        if legacy_basis is not None:
            if legacy_basis.target_coord_ui_map_id == UNKNOWN_COORD_UI_MAP_ID:
                if (
                    legacy_basis.transform == "identity"
                    and len(point) >= 2
                    and float(point[0]) == UNKNOWN_COORD_POINT[0]
                    and float(point[1]) == UNKNOWN_COORD_POINT[1]
                ):
                    return UNKNOWN_COORD_POINT
                raise ValueError(
                    f"Legacy key={legacy_basis.legacy_key} maps to unresolved instance space; "
                    "only {-1,-1} sentinel points are supported"
                )
            if legacy_basis.transform == "identity":
                return float(point[0]), float(point[1])

            source_bounds = self._get_projection_bounds(
                legacy_basis.map_id,
                legacy_basis.source_coord_ui_map_id,
            )
            assert target_bounds is not None
            world_point = invert_zone_percent_to_world(
                source_bounds,
                float(point[0]),
                float(point[1]),
            )
            return project_world_to_percent(target_bounds, world_point.x, world_point.y)

        if zone_space is None:
            raise KeyError("Missing zone-space record for legacy conversion")
        assert target_bounds is not None
        world_point = invert_zone_percent_to_world(zone_space, float(point[0]), float(point[1]))
        return project_world_to_percent(target_bounds, world_point.x, world_point.y)

    def _should_emit_unknown_instance_bucket(
        self,
        zone_area_id: int,
        map_id: int,
        point: Sequence[float],
    ) -> bool:
        if len(point) < 2:
            return False
        return (
            float(point[0]) == UNKNOWN_COORD_POINT[0]
            and float(point[1]) == UNKNOWN_COORD_POINT[1]
        )

    def _get_projection_bounds(self, map_id: int, ui_map_id: int) -> ProjectionBoundsRecord:
        record = self._projection_bounds.get((int(map_id), int(ui_map_id)))
        if record is None:
            raise KeyError(
                f"No projection bounds for mapId={map_id}, uiMapId={ui_map_id}"
            )
        return record

    def _is_unknown_bucket(points: Sequence[Sequence[float]] | None) -> bool:
        if not points:
            return False
        return all(
            len(point) >= 2
            and float(point[0]) == UNKNOWN_COORD_POINT[0]
            and float(point[1]) == UNKNOWN_COORD_POINT[1]
            for point in points
        )

    @staticmethod
    def _normalize_point(point: Sequence[float | int]) -> list[float | int]:
        normalized: list[float | int] = [float(point[0]), float(point[1])]
        normalized.extend(point[2:])
        return normalized


def invert_zone_percent_to_world(
    zone_space: ZoneSpaceRecord | ProjectionBoundsRecord,
    zone_x: float,
    zone_y: float,
) -> WorldPoint:
    dx = zone_space.world_x_max - zone_space.world_x_min
    dy = zone_space.world_y_max - zone_space.world_y_min
    if dx == 0 or dy == 0:
        source_label = (
            f"zoneAreaId={zone_space.zone_area_id}"
            if isinstance(zone_space, ZoneSpaceRecord)
            else f"mapId={zone_space.map_id}, uiMapId={zone_space.ui_map_id}"
        )
        raise ValueError(
            f"Degenerate source bounds for {source_label}"
        )

    world_y = zone_space.world_y_max - (zone_x / 100.0) * dy
    world_x = zone_space.world_x_max - (zone_y / 100.0) * dx
    return WorldPoint(x=world_x, y=world_y)


def project_world_to_percent(
    bounds: ProjectionBoundsRecord,
    world_x: float,
    world_y: float,
) -> tuple[float, float]:
    dx = bounds.world_x_max - bounds.world_x_min
    dy = bounds.world_y_max - bounds.world_y_min
    if dx == 0 or dy == 0:
        raise ValueError(
            f"Degenerate target bounds for mapId={bounds.map_id}, uiMapId={bounds.ui_map_id}"
        )

    x = (bounds.world_y_max - world_y) / dy * 100.0
    y = (bounds.world_x_max - world_x) / dx * 100.0
    return x, y
