from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManualLegacyBasisOverride:
    legacy_key: int
    map_id: int
    source_coord_ui_map_id: int
    target_coord_ui_map_id: int
    default_ui_map_hint_id: int | None = None
    source_kind: str = "containing_map_bounds"


@dataclass(frozen=True)
class ManualFixedPointOverride:
    legacy_key: int
    map_id: int
    coord_ui_map_id: int
    source_x: float
    source_y: float
    target_x: float
    target_y: float


MANUAL_LEGACY_KEY_ALIASES_BY_FLAVOR: dict[str, dict[int, int]] = {
    "classic": {
        7307: 1583,
    },
    "tbc": {
        7307: 1583,
    },
    "wotlk": {
        7307: 1583,
    },
}


MANUAL_LEGACY_BASIS_OVERRIDES_BY_FLAVOR: dict[str, dict[int, ManualLegacyBasisOverride]] = {
    "classic": {
        10073: ManualLegacyBasisOverride(
            legacy_key=10073,
            map_id=1,
            source_coord_ui_map_id=1414,
            target_coord_ui_map_id=1414,
        ),
        10074: ManualLegacyBasisOverride(
            legacy_key=10074,
            map_id=0,
            source_coord_ui_map_id=1415,
            target_coord_ui_map_id=1415,
        ),
    },
    "tbc": {
        2557: ManualLegacyBasisOverride(
            legacy_key=2557,
            map_id=429,
            source_coord_ui_map_id=235,
            target_coord_ui_map_id=235,
        ),
    },
    "wotlk": {
        4395: ManualLegacyBasisOverride(
            legacy_key=4395,
            map_id=571,
            source_coord_ui_map_id=113,
            target_coord_ui_map_id=113,
            default_ui_map_hint_id=125,
        ),
        4560: ManualLegacyBasisOverride(
            legacy_key=4560,
            map_id=571,
            source_coord_ui_map_id=113,
            target_coord_ui_map_id=113,
            default_ui_map_hint_id=126,
        ),
        2557: ManualLegacyBasisOverride(
            legacy_key=2557,
            map_id=429,
            source_coord_ui_map_id=235,
            target_coord_ui_map_id=235,
        ),
    },
}


MANUAL_FIXED_POINT_OVERRIDES_BY_FLAVOR: dict[str, dict[int, ManualFixedPointOverride]] = {
    "classic": {
        # `10089` is a fake world-map legacy key. We convert the one known
        # authored point directly to the target continent coordinate.
        10089: ManualFixedPointOverride(
            legacy_key=10089,
            map_id=1,
            coord_ui_map_id=1414,
            source_x=29.99,
            source_y=89.15,
            target_x=70.58,
            target_y=96.19,
        ),
    },
    "tbc": {
        # Same authored world-map point as classic, but kept flavor-scoped so it
        # can diverge cleanly if later validation finds different numbers.
        10089: ManualFixedPointOverride(
            legacy_key=10089,
            map_id=1,
            coord_ui_map_id=1414,
            source_x=29.99,
            source_y=89.15,
            target_x=70.58,
            target_y=96.19,
        ),
    },
    "wotlk": {
        # WotLK uses a different translated target point from the same authored
        # source coordinate because the parent-map slices changed.
        10089: ManualFixedPointOverride(
            legacy_key=10089,
            map_id=1,
            coord_ui_map_id=1414,
            source_x=29.99,
            source_y=89.15,
            target_x=77.11,
            target_y=88.84,
        ),
    },
    "cata": {
        # Cata currently reuses the known post-Wrath target until separate
        # flavor-specific validation is available.
        10089: ManualFixedPointOverride(
            legacy_key=10089,
            map_id=1,
            coord_ui_map_id=1414,
            source_x=29.99,
            source_y=89.15,
            target_x=77.11,
            target_y=88.84,
        ),
    },
    "mop": {
        # MoP currently reuses the known post-Wrath target until separate
        # flavor-specific validation is available.
        10089: ManualFixedPointOverride(
            legacy_key=10089,
            map_id=1,
            coord_ui_map_id=1414,
            source_x=29.99,
            source_y=89.15,
            target_x=77.11,
            target_y=88.84,
        ),
    },
}
