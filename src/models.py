from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runtime_assets import copy_runtime_assets


MANIFEST_FILE = "manifest.json"
ZONE_SPACES_FILE = "zone_spaces.json"
PROJECTION_BOUNDS_FILE = "projection_bounds.json"
MAP_DEFAULTS_FILE = "map_defaults.json"
INSTANCE_ANCHORS_FILE = "instance_anchors.json"
LEGACY_BASES_FILE = "legacy_bases.json"
CURRENT_SCHEMA_VERSION = 2
VALID_LEGACY_TRANSFORMS = frozenset({"identity", "reproject"})
VALID_LEGACY_SOURCE_KINDS = frozenset(
    {
        "zone_bounds",
        "direct_area_bounds",
        "containing_map_bounds",
        "inherited_parent_basis",
        "instance_map_alias",
    }
)


@dataclass(frozen=True)
class ProjectionBoundsRecord:
    map_id: int
    ui_map_id: int
    parent_ui_map_id: int | None
    area_id: int | None
    world_x_min: float
    world_x_max: float
    world_y_min: float
    world_y_max: float


@dataclass(frozen=True)
class ZoneSpaceRecord:
    zone_area_id: int
    map_id: int
    zone_ui_map_id: int
    parent_ui_map_id: int | None
    world_x_min: float
    world_x_max: float
    world_y_min: float
    world_y_max: float


@dataclass(frozen=True)
class MapDefaultRecord:
    map_id: int
    coord_ui_map_id: int


@dataclass(frozen=True)
class LegacyCoordinateBasisRecord:
    legacy_key: int
    map_id: int
    source_coord_ui_map_id: int
    target_coord_ui_map_id: int
    transform: str
    source_kind: str
    default_ui_map_hint_id: int | None


@dataclass(frozen=True)
class AnchorBucketRecord:
    map_id: int
    coord_ui_map_id: int
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class InstanceAnchorRecord:
    instance_map_id: int
    zone_area_id: int | None
    entrances: tuple[AnchorBucketRecord, ...]
    meeting_stone: tuple[AnchorBucketRecord, ...]


@dataclass(frozen=True)
class CoordinatePack:
    flavor: str
    schema_version: int
    zone_spaces: tuple[ZoneSpaceRecord, ...]
    projection_bounds: tuple[ProjectionBoundsRecord, ...]
    map_defaults: tuple[MapDefaultRecord, ...]
    legacy_bases: tuple[LegacyCoordinateBasisRecord, ...]
    instance_anchors: tuple[InstanceAnchorRecord, ...]

    def __post_init__(self) -> None:
        if self.schema_version != CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported coordinate pack schemaVersion={self.schema_version}; "
                f"expected {CURRENT_SCHEMA_VERSION}"
            )
        _validate_unique_keys(
            records=self.zone_spaces,
            key_fn=lambda record: record.zone_area_id,
            label="zone_spaces.zoneAreaId",
        )
        _validate_unique_keys(
            records=self.projection_bounds,
            key_fn=lambda record: (record.map_id, record.ui_map_id),
            label="projection_bounds.(mapId,uiMapId)",
        )
        _validate_unique_keys(
            records=self.map_defaults,
            key_fn=lambda record: record.map_id,
            label="map_defaults.mapId",
        )
        _validate_unique_keys(
            records=self.legacy_bases,
            key_fn=lambda record: record.legacy_key,
            label="legacy_bases.legacyKey",
        )
        _validate_unique_keys(
            records=self.instance_anchors,
            key_fn=lambda record: record.instance_map_id,
            label="instance_anchors.instanceMapId",
        )
        for record in self.legacy_bases:
            if record.transform not in VALID_LEGACY_TRANSFORMS:
                raise ValueError(
                    f"Unsupported legacy transform={record.transform!r} "
                    f"for legacyKey={record.legacy_key}"
                )
            if record.source_kind not in VALID_LEGACY_SOURCE_KINDS:
                raise ValueError(
                    f"Unsupported legacy sourceKind={record.source_kind!r} "
                    f"for legacyKey={record.legacy_key}"
                )

    def zone_space_by_area_id(self) -> dict[int, ZoneSpaceRecord]:
        return {record.zone_area_id: record for record in self.zone_spaces}

    def projection_bounds_by_key(self) -> dict[tuple[int, int], ProjectionBoundsRecord]:
        return {
            (record.map_id, record.ui_map_id): record
            for record in self.projection_bounds
        }

    def map_default_by_map_id(self) -> dict[int, int]:
        return {record.map_id: record.coord_ui_map_id for record in self.map_defaults}

    def legacy_basis_by_key(self) -> dict[int, LegacyCoordinateBasisRecord]:
        return {record.legacy_key: record for record in self.legacy_bases}

    def instance_anchor_by_map_id(self) -> dict[int, InstanceAnchorRecord]:
        return {record.instance_map_id: record for record in self.instance_anchors}

    def instance_anchor_by_zone_area_id(self) -> dict[int, InstanceAnchorRecord]:
        return {
            int(record.zone_area_id): record
            for record in self.instance_anchors
            if record.zone_area_id is not None
        }

    @classmethod
    def load(cls, pack_dir: str | Path) -> "CoordinatePack":
        pack_path = Path(pack_dir)

        manifest = _load_json(pack_path / MANIFEST_FILE)
        schema_version = int(manifest["schemaVersion"])
        if schema_version != CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported coordinate pack schemaVersion={schema_version} in "
                f"{pack_path / MANIFEST_FILE}; expected {CURRENT_SCHEMA_VERSION}"
            )
        zone_spaces = tuple(
            ZoneSpaceRecord(
                zone_area_id=int(row["zoneAreaId"]),
                map_id=int(row["mapId"]),
                zone_ui_map_id=int(row["zoneUiMapId"]),
                parent_ui_map_id=_int_or_none(row.get("parentUiMapId")),
                world_x_min=float(row["worldXMin"]),
                world_x_max=float(row["worldXMax"]),
                world_y_min=float(row["worldYMin"]),
                world_y_max=float(row["worldYMax"]),
            )
            for row in _load_json(pack_path / ZONE_SPACES_FILE)
        )
        projection_bounds = tuple(
            ProjectionBoundsRecord(
                map_id=int(row["mapId"]),
                ui_map_id=int(row["uiMapId"]),
                parent_ui_map_id=_int_or_none(row.get("parentUiMapId")),
                area_id=_int_or_none(row.get("areaId")),
                world_x_min=float(row["worldXMin"]),
                world_x_max=float(row["worldXMax"]),
                world_y_min=float(row["worldYMin"]),
                world_y_max=float(row["worldYMax"]),
            )
            for row in _load_json(pack_path / PROJECTION_BOUNDS_FILE)
        )
        map_defaults = tuple(
            MapDefaultRecord(
                map_id=int(row["mapId"]),
                coord_ui_map_id=int(row["coordUiMapId"]),
            )
            for row in _load_json(pack_path / MAP_DEFAULTS_FILE)
        )
        legacy_bases = tuple(
            LegacyCoordinateBasisRecord(
                legacy_key=int(row["legacyKey"]),
                map_id=int(row["mapId"]),
                source_coord_ui_map_id=int(row["sourceCoordUiMapId"]),
                target_coord_ui_map_id=int(row["targetCoordUiMapId"]),
                transform=str(row["transform"]),
                source_kind=str(row["sourceKind"]),
                default_ui_map_hint_id=_int_or_none(row.get("defaultUiMapHintId")),
            )
            for row in _load_json(pack_path / LEGACY_BASES_FILE)
        )
        instance_anchors = tuple(
            InstanceAnchorRecord(
                instance_map_id=int(row["instanceMapId"]),
                zone_area_id=_int_or_none(row.get("zoneAreaId")),
                entrances=_load_anchor_buckets(row.get("entrances", [])),
                meeting_stone=_load_anchor_buckets(row.get("meetingStone", [])),
            )
            for row in _load_json(pack_path / INSTANCE_ANCHORS_FILE)
        )
        return cls(
            flavor=str(manifest["flavor"]),
            schema_version=schema_version,
            zone_spaces=zone_spaces,
            projection_bounds=projection_bounds,
            map_defaults=map_defaults,
            legacy_bases=legacy_bases,
            instance_anchors=instance_anchors,
        )

    def dump(self, pack_dir: str | Path) -> None:
        pack_path = Path(pack_dir)
        pack_path.mkdir(parents=True, exist_ok=True)

        _dump_json(
            pack_path / MANIFEST_FILE,
            {
                "flavor": self.flavor,
                "schemaVersion": self.schema_version,
            },
        )
        _dump_json(
            pack_path / ZONE_SPACES_FILE,
            [
                {
                    "zoneAreaId": record.zone_area_id,
                    "mapId": record.map_id,
                    "zoneUiMapId": record.zone_ui_map_id,
                    "parentUiMapId": record.parent_ui_map_id,
                    "worldXMin": record.world_x_min,
                    "worldXMax": record.world_x_max,
                    "worldYMin": record.world_y_min,
                    "worldYMax": record.world_y_max,
                }
                for record in self.zone_spaces
            ],
        )
        _dump_json(
            pack_path / PROJECTION_BOUNDS_FILE,
            [
                {
                    "mapId": record.map_id,
                    "uiMapId": record.ui_map_id,
                    "parentUiMapId": record.parent_ui_map_id,
                    "areaId": record.area_id,
                    "worldXMin": record.world_x_min,
                    "worldXMax": record.world_x_max,
                    "worldYMin": record.world_y_min,
                    "worldYMax": record.world_y_max,
                }
                for record in self.projection_bounds
            ],
        )
        _dump_json(
            pack_path / MAP_DEFAULTS_FILE,
            [
                {
                    "mapId": record.map_id,
                    "coordUiMapId": record.coord_ui_map_id,
                }
                for record in self.map_defaults
            ],
        )
        _dump_json(
            pack_path / LEGACY_BASES_FILE,
            [
                {
                    "legacyKey": record.legacy_key,
                    "mapId": record.map_id,
                    "sourceCoordUiMapId": record.source_coord_ui_map_id,
                    "targetCoordUiMapId": record.target_coord_ui_map_id,
                    "transform": record.transform,
                    "sourceKind": record.source_kind,
                    "defaultUiMapHintId": record.default_ui_map_hint_id,
                }
                for record in self.legacy_bases
            ],
        )
        _dump_json(
            pack_path / INSTANCE_ANCHORS_FILE,
            [
                {
                    "instanceMapId": record.instance_map_id,
                    "zoneAreaId": record.zone_area_id,
                    "entrances": _dump_anchor_buckets(record.entrances),
                    "meetingStone": _dump_anchor_buckets(record.meeting_stone),
                }
                for record in self.instance_anchors
            ],
        )
        copy_runtime_assets(pack_path)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _validate_unique_keys(records: tuple[Any, ...], key_fn, label: str) -> None:
    seen: set[Any] = set()
    for record in records:
        key = key_fn(record)
        if key in seen:
            raise ValueError(f"Duplicate {label} entry for key={key!r}")
        seen.add(key)


def _load_anchor_buckets(rows: list[dict[str, Any]]) -> tuple[AnchorBucketRecord, ...]:
    return tuple(
        AnchorBucketRecord(
            map_id=int(row["mapId"]),
            coord_ui_map_id=int(row["coordUiMapId"]),
            points=tuple((float(point[0]), float(point[1])) for point in row["points"]),
        )
        for row in rows
    )


def _dump_anchor_buckets(rows: tuple[AnchorBucketRecord, ...]) -> list[dict[str, Any]]:
    return [
        {
            "mapId": row.map_id,
            "coordUiMapId": row.coord_ui_map_id,
            "points": [[x, y] for x, y in row.points],
        }
        for row in rows
    ]


def _load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _dump_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")
