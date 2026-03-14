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


MANUAL_FAKE_UI_MAP_ALIASES_BY_FLAVOR: dict[str, dict[int, int]] = {
    "wotlk": {
        # Verified fake floor/sub-map keys. The builder resolves the shared
        # instance MapID from the DBC and keeps the exact UiMapID here, which
        # is the part that determines the floor/sub-level.
        # Questie: Blackrock Depths - Shadowforge City
        # UiMap DBC: Blackrock Depths
        10002: 243,
        # Questie: The Oculus - Band of Acceleration
        # UiMap DBC: The Oculus
        10047: 144,
        # Questie: The Oculus - Band of Transmutation
        # UiMap DBC: The Oculus
        10048: 145,
        # Questie: The Oculus - Band of Alignment
        # UiMap DBC: The Oculus
        10049: 146,
        # Questie: Ulduar - The Descent of Madness
        # UiMap DBC: Ulduar
        10050: 150,
        # Questie: Ulduar - The Spark of Imagination
        # UiMap DBC: Ulduar
        10051: 151,
        # Questie: Ulduar - The Inner Sanctum of Ulduar
        # UiMap DBC: Ulduar
        10052: 149,
        # Questie: Utgarde Pinnacle - Lower Level
        # UiMap DBC: Utgarde Pinnacle
        10053: 136,
        # Questie: Halls of Lightning - The Terrestrial Watchtower
        # UiMap DBC: Halls of Lightning
        10054: 139,
        # Questie: Azjol-Nerub - The Brood Pit
        # UiMap DBC: Azjol-Nerub
        10055: 157,
        # Questie: Azjol-Nerub - Hadronox's Lair
        # UiMap DBC: Azjol-Nerub
        10056: 158,
        # Questie: Utgarde Keep - Middle Level
        # UiMap DBC: Utgarde Keep
        10057: 134,
        # Questie: Utgarde Keep - Upper Level
        # UiMap DBC: Utgarde Keep
        10058: 135,
        # Questie: The Culling of Stratholme - City
        # UiMap DBC: The Culling of Stratholme
        10059: 131,
        # Questie: Drak'Tharon Keep - Upper Level
        # UiMap DBC: Drak'Tharon Keep
        10060: 161,
        # Questie: Gundrak - Lower Level
        # UiMap DBC: Gundrak
        10061: 153,
        # Questie: Naxxramas - Construct Quarter
        # UiMap DBC: Naxxramas
        10062: 162,
        # Questie: Naxxramas - Arachnid Quarter
        # UiMap DBC: Naxxramas
        10063: 163,
        # Questie: Naxxramas - Military Quarter
        # UiMap DBC: Naxxramas
        10064: 164,
        # Questie: Naxxramas - Plague Quarter
        # UiMap DBC: Naxxramas
        10065: 165,
        # Questie: Naxxramas - Frostwyrm Lair
        # UiMap DBC: Naxxramas
        10066: 167,
        # Questie: Icecrown Citadel - Rampart of Skulls
        # UiMap DBC: Icecrown Citadel
        10067: 187,
        # Questie: Icecrown Citadel - Deathbringer's Rise
        # UiMap DBC: Icecrown Citadel
        10068: 188,
        # Questie: Icecrown Citadel - Sindragosa
        # UiMap DBC: Icecrown Citadel
        10069: 189,
        # Questie: Icecrown Citadel - Upper Spire
        # UiMap DBC: Icecrown Citadel
        10070: 190,
        # Questie: Icecrown Citadel - Queen Lana'thel
        # UiMap DBC: Icecrown Citadel
        10071: 191,
        # Questie: Icecrown Citadel - The Frozen Throne
        # UiMap DBC: Icecrown Citadel
        10072: 192,
    },
    "cata": {
        # Questie-authored fake floor/sub-map keys. The builder resolves these
        # to the verified UiMapID family in the Cata DBC and emits a normal
        # identity basis record on the shared instance MapID.
        # Questie: Maraudon - Zaetar's Grave
        # UiMap DBC: Maraudon
        10000: 281,
        # Questie: Stratholme - The Gauntlet
        # UiMap DBC: Stratholme
        10001: 318,
        # Questie: Blackrock Depths - Shadowforge City
        # UiMap DBC: Blackrock Depths
        10002: 243,
        # Questie: Blackrock Spire - Tazz'Alor
        # UiMap DBC: Blackrock Spire
        10003: 250,
        # Questie: Blackrock Spire - Hordemar City
        # UiMap DBC: Blackrock Spire
        10005: 252,
        # Questie: Blackrock Spire - Chamber of Battle
        # UiMap DBC: Blackrock Spire
        10007: 255,
        # Questie: Scarlet Monastery - Library
        # UiMap DBC: Scarlet Monastery
        10008: 303,
        # Questie: Scarlet Monastery - Armory
        # UiMap DBC: Scarlet Monastery
        10009: 304,
        # Questie: Scarlet Monastery - Cathedral
        # UiMap DBC: Scarlet Monastery
        10010: 305,
        # Questie: Scholomance - Chamber of Summoning
        # UiMap DBC: ScholomanceOLD
        10011: 307,
        # Questie: Scholomance - The Upper Study
        # UiMap DBC: ScholomanceOLD
        10012: 308,
        # Questie: Scholomance - Headmaster's Study
        # UiMap DBC: ScholomanceOLD
        10013: 309,
        # Questie: Shadowfang Keep - Dining Hall
        # UiMap DBC: Shadowfang Keep
        10014: 311,
        # Questie: Shadowfang Keep - Lower Observatory
        # UiMap DBC: Shadowfang Keep
        10016: 313,
        # Questie: Shadowfang Keep - Lord Godfrey's Chamber
        # UiMap DBC: Shadowfang Keep
        10018: 315,
        # Questie: Shadowfang Keep - The Wall Walk
        # UiMap DBC: Shadowfang Keep
        10019: 316,
        # Questie: Blackfathom Deeps - Moonshrine Sanctum
        # UiMap DBC: Blackfathom Deeps
        10020: 222,
        # Questie: Blackfathom Deeps - The Forgotten Pool
        # UiMap DBC: Blackfathom Deeps
        10021: 223,
        # Questie: Dire Maul - Gordok Commons
        # UiMap DBC: Dire Maul
        10022: 235,
        # Questie: Dire Maul - Capital Gardens
        # UiMap DBC: Dire Maul
        10023: 236,
        # Questie: Dire Maul - Court of the Highborne
        # UiMap DBC: Dire Maul
        10024: 237,
        # Questie: Dire Maul - Prison of Immol'Thar
        # UiMap DBC: Dire Maul
        10025: 238,
        # Questie: Dire Maul - Warpwood Quarter
        # UiMap DBC: Dire Maul
        10026: 239,
        # Questie: Dire Maul - The Shrine of Eldretharr
        # UiMap DBC: Dire Maul
        10027: 240,
        # Questie: Magisters' Terrace - Grand Magister's Asylum
        # UiMap DBC: Magisters' Terrace
        10028: 348,
        # Questie: The Deadmines - Ironclad Cove
        # UiMap DBC: The Deadmines
        10029: 292,
        # Questie: Gnomeregan - The Dormitory
        # UiMap DBC: Gnomeregan
        10030: 227,
        # Questie: Gnomeregan - Launch Bay
        # UiMap DBC: Gnomeregan
        10031: 228,
        # Questie: Gnomeregan - Tinkers' Court
        # UiMap DBC: Gnomeregan
        10032: 229,
        # Questie: Uldaman - Khaz'Goroth's Seat
        # UiMap DBC: Uldaman
        10033: 231,
        # Questie: Hour of Twilight - Wyrmrest Temple
        # UiMap DBC: Hour of Twilight
        10039: 400,
        # Questie: Ahn'Qiraj - Vault of C'Thun
        # UiMap DBC: Ahn'Qiraj
        10041: 321,
        # Questie: Sethekk Halls - Halls of Mourning
        # UiMap DBC: Sethekk Halls
        10042: 259,
        # Questie: Auchenai Crypts - Bridge of Souls
        # UiMap DBC: Auchenai Crypts
        10043: 257,
        # Questie: The Mechanar - Calculation Chamber
        # UiMap DBC: The Mechanar
        10044: 268,
        # Questie: The Arcatraz - Stasis Block: Maximus
        # UiMap DBC: The Arcatraz
        10045: 270,
        # Questie: The Arcatraz - Containment Core
        # UiMap DBC: The Arcatraz
        10046: 271,
        # Questie: Karazhan - Servant's Quarters
        # UiMap DBC: Karazhan
        10102: 350,
        # Questie: Karazhan - The Guest Chambers
        # UiMap DBC: Karazhan
        10105: 353,
        # Questie: Karazhan - Master's Terrace
        # UiMap DBC: Karazhan
        10107: 355,
        # Questie: Karazhan - The Menagerie
        # UiMap DBC: Karazhan
        10110: 358,
        # Questie: Karazhan - Guardian's Library
        # UiMap DBC: Karazhan
        10111: 359,
        # Questie: Karazhan - Netherspace
        # UiMap DBC: Karazhan
        10118: 366,
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
