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
    "classic": {},
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

