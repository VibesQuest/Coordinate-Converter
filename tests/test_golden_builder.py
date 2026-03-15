from __future__ import annotations

import json
from pathlib import Path

import pytest


PACK_FILES = (
    "manifest.json",
    "zone_spaces.json",
    "projection_bounds.json",
    "map_defaults.json",
    "legacy_bases.json",
    "instance_anchors.json",
)

RUNTIME_FILES = (
    "runtime/RUNTIME.md",
    "runtime/python/coords_loader.py",
    "runtime/python/coords_converter.py",
    "runtime/typescript/coordsLoader.ts",
    "runtime/typescript/coordsConverter.ts",
    "runtime/lua/coords_loader.lua",
    "runtime/lua/coords_converter.lua",
    "runtime/lua/json.lua",
)

EXPECTED_FLAVORS = {
    "v1": "classic",
    "v2": "tbc",
    "v3": "wotlk",
    "v4": "cata",
    "v5": "mop",
}

REQUIRED_LEGACY_KEYS = {
    "v1": {12, 209, 719, 796, 1583, 2257, 7307},
    "v2": {12, 209, 719, 796, 1583, 2257, 2557, 7307},
    "v3": {12, 209, 719, 796, 1583, 2257, 2557, 4395, 4560, 7307},
}


@pytest.mark.parametrize("version", sorted(EXPECTED_FLAVORS))
def test_built_pack_contains_required_files_and_runtime_bundle(
    version: str,
    repo_root: Path,
) -> None:
    pack_dir = repo_root / "output" / version

    for relative_path in (*PACK_FILES, *RUNTIME_FILES):
        assert (pack_dir / relative_path).exists(), f"missing {version}/{relative_path}"


@pytest.mark.parametrize("version, flavor", sorted(EXPECTED_FLAVORS.items()))
def test_built_pack_manifest_matches_expected_schema_and_flavor(
    version: str,
    flavor: str,
    repo_root: Path,
) -> None:
    manifest = _load_json(repo_root / "output" / version / "manifest.json")

    assert manifest["flavor"] == flavor
    assert manifest["schemaVersion"] == 2
    assert manifest["majorVersion"] == int(version.removeprefix("v"))
    assert isinstance(manifest["dbcBuild"], str) and manifest["dbcBuild"]
    assert manifest["dbcSource"] == "dbc-minimal"


@pytest.mark.parametrize("version", sorted(EXPECTED_FLAVORS))
def test_built_pack_instance_anchors_are_empty(version: str, repo_root: Path) -> None:
    instance_anchors = _load_json(repo_root / "output" / version / "instance_anchors.json")
    assert instance_anchors == []


@pytest.mark.parametrize("version", sorted(REQUIRED_LEGACY_KEYS))
def test_required_legacy_basis_keys_are_present(version: str, repo_root: Path) -> None:
    legacy_bases = _legacy_bases_by_key(repo_root / "output" / version / "legacy_bases.json")

    for legacy_key in REQUIRED_LEGACY_KEYS[version]:
        assert legacy_key in legacy_bases, f"missing legacy key {legacy_key} in {version}"


def test_wotlk_exact_legacy_basis_records_match_golden_contract(repo_root: Path) -> None:
    legacy_bases = _legacy_bases_by_key(repo_root / "output" / "v3" / "legacy_bases.json")

    assert legacy_bases[4395] == {
        "legacyKey": 4395,
        "mapId": 571,
        "sourceCoordUiMapId": 113,
        "targetCoordUiMapId": 113,
        "transform": "identity",
        "sourceKind": "containing_map_bounds",
        "defaultUiMapHintId": 125,
    }
    assert legacy_bases[4560] == {
        "legacyKey": 4560,
        "mapId": 571,
        "sourceCoordUiMapId": 113,
        "targetCoordUiMapId": 113,
        "transform": "identity",
        "sourceKind": "containing_map_bounds",
        "defaultUiMapHintId": 126,
    }
    assert legacy_bases[2257] == {
        "legacyKey": 2257,
        "mapId": 369,
        "sourceCoordUiMapId": 0,
        "targetCoordUiMapId": 0,
        "transform": "identity",
        "sourceKind": "instance_map_alias",
        "defaultUiMapHintId": None,
    }
    assert legacy_bases[2557] == {
        "legacyKey": 2557,
        "mapId": 429,
        "sourceCoordUiMapId": 235,
        "targetCoordUiMapId": 235,
        "transform": "identity",
        "sourceKind": "containing_map_bounds",
        "defaultUiMapHintId": None,
    }


def test_wotlk_manual_alias_7307_matches_1583_except_for_legacy_key(repo_root: Path) -> None:
    legacy_bases = _legacy_bases_by_key(repo_root / "output" / "v3" / "legacy_bases.json")

    alias_record = dict(legacy_bases[7307])
    canonical_record = dict(legacy_bases[1583])
    alias_record["legacyKey"] = 1583

    assert alias_record == canonical_record


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _legacy_bases_by_key(path: Path) -> dict[int, dict[str, object]]:
    return {
        int(record["legacyKey"]): record
        for record in _load_json(path)
    }
