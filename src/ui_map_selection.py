from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


DEFAULT_ORDER_INDEX = 999999
SUPPORTED_INSTANCE_TYPES: tuple[int, ...] = (1, 2, 3)


@dataclass(frozen=True)
class UiMapMeta:
    parent: int | None
    map_type: int | None
    system: int | None


class CoordUiMapCandidate(TypedDict):
    ui_map_id: int
    area_id: int | None
    order_index: int | None
    area: float


def map_type_rank(map_type: int | None) -> int:
    if map_type == 2:
        return 0
    if map_type == 1:
        return 1
    if map_type == 3:
        return 2
    if map_type == 6:
        return 3
    if map_type == 4:
        return 4
    if map_type == 5:
        return 5
    return 99


def system_rank(system: int | None) -> int:
    if system == 0:
        return 0
    if system == 1:
        return 1
    return 2


def bounds_area(
    world_x_min: float | None,
    world_x_max: float | None,
    world_y_min: float | None,
    world_y_max: float | None,
) -> float:
    if (
        world_x_min is None
        or world_x_max is None
        or world_y_min is None
        or world_y_max is None
    ):
        return 0.0
    return max(0.0, world_x_max - world_x_min) * max(0.0, world_y_max - world_y_min)


def bounds_area_from_regions(
    region_0: float | None,
    region_1: float | None,
    region_3: float | None,
    region_4: float | None,
) -> float:
    if region_0 is None or region_1 is None or region_3 is None or region_4 is None:
        return 0.0
    world_x_min = min(region_0, region_3)
    world_x_max = max(region_0, region_3)
    world_y_min = min(region_1, region_4)
    world_y_max = max(region_1, region_4)
    return bounds_area(world_x_min, world_x_max, world_y_min, world_y_max)


def primary_ui_map_sort_key(
    ui_map_id: int,
    ui_map_meta: UiMapMeta | None,
    area: float,
    order_index: int | None,
) -> tuple[int, int, float, int, int]:
    meta = ui_map_meta or UiMapMeta(None, None, None)
    return (
        map_type_rank(meta.map_type),
        system_rank(meta.system),
        -area,
        order_index if order_index is not None else DEFAULT_ORDER_INDEX,
        ui_map_id,
    )


def select_coord_ui_map_id(
    candidates: list[CoordUiMapCandidate],
    ui_map_meta: dict[int, UiMapMeta],
    map_instance_type: int | None,
) -> int | None:
    if not candidates:
        return None

    if map_instance_type in SUPPORTED_INSTANCE_TYPES:
        dungeon_ui_map_ids = sorted(
            {
                int(candidate["ui_map_id"])
                for candidate in candidates
                if (ui_map_meta.get(int(candidate["ui_map_id"])) or UiMapMeta(None, None, None)).map_type == 4
            }
        )
        if dungeon_ui_map_ids:
            return dungeon_ui_map_ids[0]

    area0 = [candidate for candidate in candidates if int(candidate.get("area_id") or 0) == 0]
    ranked_candidates = area0 if area0 else candidates
    ranked = sorted(
        ranked_candidates,
        key=lambda candidate: primary_ui_map_sort_key(
            ui_map_id=int(candidate["ui_map_id"]),
            ui_map_meta=ui_map_meta.get(int(candidate["ui_map_id"])),
            area=float(candidate.get("area") or 0.0),
            order_index=candidate.get("order_index"),
        ),
    )
    return int(ranked[0]["ui_map_id"])

