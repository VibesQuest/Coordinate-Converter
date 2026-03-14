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


def _identity_basis_override(
    legacy_key: int,
    map_id: int,
    coord_ui_map_id: int,
) -> ManualLegacyBasisOverride:
    return ManualLegacyBasisOverride(
        legacy_key=legacy_key,
        map_id=map_id,
        source_coord_ui_map_id=coord_ui_map_id,
        target_coord_ui_map_id=coord_ui_map_id,
    )


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
        # These are Questie-authored fake legacy keys for specific instance
        # floors/sub-maps. We map them directly to the verified UiMapID on the
        # shared instance MapID and preserve XY as identity.
        10002: _identity_basis_override(10002, 230, 243),
        10047: _identity_basis_override(10047, 578, 144),
        10048: _identity_basis_override(10048, 578, 145),
        10049: _identity_basis_override(10049, 578, 146),
        10050: _identity_basis_override(10050, 603, 150),
        10051: _identity_basis_override(10051, 603, 151),
        10052: _identity_basis_override(10052, 603, 149),
        10053: _identity_basis_override(10053, 575, 136),
        10054: _identity_basis_override(10054, 602, 139),
        10055: _identity_basis_override(10055, 601, 157),
        10056: _identity_basis_override(10056, 601, 158),
        10057: _identity_basis_override(10057, 574, 134),
        10058: _identity_basis_override(10058, 574, 135),
        10059: _identity_basis_override(10059, 595, 131),
        10060: _identity_basis_override(10060, 600, 161),
        10061: _identity_basis_override(10061, 604, 153),
        10062: _identity_basis_override(10062, 533, 162),
        10063: _identity_basis_override(10063, 533, 163),
        10064: _identity_basis_override(10064, 533, 164),
        10065: _identity_basis_override(10065, 533, 165),
        10066: _identity_basis_override(10066, 533, 167),
        10067: _identity_basis_override(10067, 631, 187),
        10068: _identity_basis_override(10068, 631, 188),
        10069: _identity_basis_override(10069, 631, 189),
        10070: _identity_basis_override(10070, 631, 190),
        10071: _identity_basis_override(10071, 631, 191),
        10072: _identity_basis_override(10072, 631, 192),
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
