from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


EXPANSION_TO_VERSION = {
    "classic": "v1",
    "sod": "v1",
    "tbc": "v2",
    "wotlk": "v3",
    "cata": "v3",
    "mop": "v3",
}

COORD_FIELDS = ("spawns", "triggerEnd", "extraObjectives", "waypoints")

_RUNTIME_CACHE: dict[tuple[Path, str], tuple[ModuleType, ModuleType]] = {}


@dataclass(frozen=True)
class ZoneBucketCase:
    expansion: str
    entity_type: str
    field: str
    file: str
    function: str
    entity_id: str
    zone_area_id: int
    points: tuple[tuple[float, float], ...]
    source_label: str


def load_runtime_modules(repo_root: Path, version: str) -> tuple[ModuleType, ModuleType]:
    cache_key = (repo_root, version)
    if cache_key not in _RUNTIME_CACHE:
        runtime_dir = _find_runtime_dir(repo_root, version)
        loader_module = _load_module(
            f"coords_loader_{version}",
            runtime_dir / "coords_loader.py",
        )
        converter_module = _load_module(
            f"coords_converter_{version}",
            runtime_dir / "coords_converter.py",
        )
        _RUNTIME_CACHE[cache_key] = (loader_module, converter_module)
    return _RUNTIME_CACHE[cache_key]


def iter_zone_bucket_cases(corrections_data: dict[str, Any]) -> Iterable[ZoneBucketCase]:
    for group in corrections_data["corrections"]:
        common = {
            "expansion": group["expansion"],
            "entity_type": group["type"],
            "file": group["file"],
            "function": group["function"],
        }
        for entity_id, fields in group["corrections"].items():
            yield from _iter_entity_cases(entity_id, fields, common)


def classify_zone_bucket_case(
    pack: dict[str, Any],
    converter_module: ModuleType,
    case: ZoneBucketCase,
) -> str:
    legacy_basis = pack["legacyBasisByKey"].get(case.zone_area_id)
    zone_space = pack["zoneSpaceByAreaId"].get(case.zone_area_id)
    if legacy_basis is None and zone_space is None:
        return "missing_mapping"

    if legacy_basis is not None and int(legacy_basis["targetCoordUiMapId"]) == int(
        converter_module.UNKNOWN_COORD_UI_MAP_ID
    ):
        unknown_point = tuple(float(value) for value in converter_module.UNKNOWN_COORD_POINT)
        if any(point != unknown_point for point in case.points):
            return "unresolved_instance_non_sentinel"

    return "convertible"


def validate_map_buckets(map_buckets: dict[int, dict[int, list[list[float | int]]]]) -> list[str]:
    errors: list[str] = []
    if not isinstance(map_buckets, dict):
        return [f"expected dict result, got {type(map_buckets).__name__}"]

    if not map_buckets:
        errors.append("expected at least one map bucket")
        return errors

    for map_id, coord_buckets in map_buckets.items():
        if not isinstance(map_id, int):
            errors.append(f"mapId key is not int: {map_id!r}")
        if not isinstance(coord_buckets, dict) or not coord_buckets:
            errors.append(f"mapId={map_id!r} has invalid coord buckets")
            continue
        for coord_ui_map_id, points in coord_buckets.items():
            if not isinstance(coord_ui_map_id, int):
                errors.append(
                    f"mapId={map_id!r} coordUiMapId key is not int: {coord_ui_map_id!r}"
                )
            if not isinstance(points, list) or not points:
                errors.append(
                    f"mapId={map_id!r} coordUiMapId={coord_ui_map_id!r} has invalid points"
                )
                continue
            for point in points:
                if not isinstance(point, list):
                    errors.append(
                        f"mapId={map_id!r} coordUiMapId={coord_ui_map_id!r} point is not a list"
                    )
                    continue
                if len(point) not in (2, 3):
                    errors.append(
                        f"mapId={map_id!r} coordUiMapId={coord_ui_map_id!r} "
                        f"point has unexpected length {len(point)}"
                    )
                for value in point:
                    if not isinstance(value, (int, float)):
                        errors.append(
                            f"mapId={map_id!r} coordUiMapId={coord_ui_map_id!r} "
                            f"point contains non-numeric value {value!r}"
                        )
    return errors


def _iter_entity_cases(
    entity_id: str,
    fields: dict[str, Any],
    common: dict[str, str],
) -> Iterable[ZoneBucketCase]:
    if isinstance(fields.get("spawns"), dict):
        yield from _zone_bucket_cases_from_zone_table(
            fields["spawns"],
            field="spawns",
            entity_id=entity_id,
            source_prefix="spawns",
            **common,
        )

    trigger_end = fields.get("triggerEnd")
    if isinstance(trigger_end, dict) and isinstance(trigger_end.get("2"), dict):
        yield from _zone_bucket_cases_from_zone_table(
            trigger_end["2"],
            field="triggerEnd",
            entity_id=entity_id,
            source_prefix="triggerEnd[2]",
            **common,
        )

    extra_objectives = fields.get("extraObjectives")
    if isinstance(extra_objectives, dict):
        for objective_index, objective in _iter_lua_array_items(extra_objectives):
            if not isinstance(objective, dict) or not isinstance(objective.get("1"), dict):
                continue
            yield from _zone_bucket_cases_from_zone_table(
                objective["1"],
                field="extraObjectives",
                entity_id=entity_id,
                source_prefix=f"extraObjectives[{objective_index}][1]",
                **common,
            )

    waypoints = fields.get("waypoints")
    if isinstance(waypoints, dict):
        for zone_area_id, paths in waypoints.items():
            if not isinstance(paths, dict):
                continue
            for path_index, path_points_obj in _iter_lua_array_items(paths):
                points = _lua_points_object_to_list(path_points_obj)
                if not points:
                    continue
                yield ZoneBucketCase(
                    expansion=common["expansion"],
                    entity_type=common["entity_type"],
                    field="waypoints",
                    file=common["file"],
                    function=common["function"],
                    entity_id=entity_id,
                    zone_area_id=int(zone_area_id),
                    points=tuple(points),
                    source_label=f"waypoints[{zone_area_id}][{path_index}]",
                )


def _zone_bucket_cases_from_zone_table(
    zone_table: dict[str, Any],
    *,
    expansion: str,
    entity_type: str,
    file: str,
    function: str,
    entity_id: str,
    field: str,
    source_prefix: str,
) -> Iterable[ZoneBucketCase]:
    for zone_area_id, points_obj in zone_table.items():
        points = _lua_points_object_to_list(points_obj)
        if not points:
            continue
        yield ZoneBucketCase(
            expansion=expansion,
            entity_type=entity_type,
            field=field,
            file=file,
            function=function,
            entity_id=entity_id,
            zone_area_id=int(zone_area_id),
            points=tuple(points),
            source_label=f"{source_prefix}[{zone_area_id}]",
        )


def _lua_points_object_to_list(points_obj: Any) -> list[tuple[float, float]]:
    if not isinstance(points_obj, dict):
        return []

    points: list[tuple[float, float]] = []
    for _, point in _iter_lua_array_items(points_obj):
        if not isinstance(point, dict):
            continue
        if "1" not in point or "2" not in point:
            continue
        points.append((float(point["1"]), float(point["2"])))
    return points


def _iter_lua_array_items(lua_obj: dict[str, Any]) -> Iterable[tuple[int, Any]]:
    indexed_values: list[tuple[int, Any]] = []
    for key, value in lua_obj.items():
        try:
            index = int(key)
        except (TypeError, ValueError):
            continue
        indexed_values.append((index, value))

    indexed_values.sort(key=lambda item: item[0])
    return indexed_values


def _load_module(module_name: str, module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_runtime_dir(repo_root: Path, version: str) -> Path:
    candidates = (repo_root / "output" / version / "runtime" / "python",)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No runtime/python directory found for {version}; checked: "
        + ", ".join(str(candidate) for candidate in candidates)
    )
