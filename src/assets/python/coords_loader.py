from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FILES = {
    "manifest": "manifest.json",
    "zoneSpaces": "zone_spaces.json",
    "projectionBounds": "projection_bounds.json",
    "mapDefaults": "map_defaults.json",
    "legacyBases": "legacy_bases.json",
    "instanceAnchors": "instance_anchors.json",
}
CURRENT_SCHEMA_VERSION = 2


def load_coordinate_pack(pack_dir: str | Path) -> dict[str, Any]:
    root = Path(pack_dir)
    pack = {
        key: _read_json(root / filename)
        for key, filename in FILES.items()
    }
    schema_version = int(pack["manifest"]["schemaVersion"])
    if schema_version != CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported coordinate pack schemaVersion={schema_version} in "
            f"{root / FILES['manifest']}; expected {CURRENT_SCHEMA_VERSION}"
        )

    pack["zoneSpaceByAreaId"] = {
        int(row["zoneAreaId"]): row for row in pack["zoneSpaces"]
    }
    pack["projectionBoundsByKey"] = {
        (int(row["mapId"]), int(row["uiMapId"])): row
        for row in pack["projectionBounds"]
    }
    pack["mapDefaultByMapId"] = {
        int(row["mapId"]): int(row["coordUiMapId"])
        for row in pack["mapDefaults"]
    }
    pack["legacyBasisByKey"] = {
        int(row["legacyKey"]): row for row in pack["legacyBases"]
    }
    pack["instanceAnchorByMapId"] = {
        int(row["instanceMapId"]): row for row in pack["instanceAnchors"]
    }
    pack["instanceAnchorByZoneAreaId"] = {
        int(row["zoneAreaId"]): row
        for row in pack["instanceAnchors"]
        if row.get("zoneAreaId") is not None
    }
    return pack


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
