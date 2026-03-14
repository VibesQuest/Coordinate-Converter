from __future__ import annotations

import json

import pytest

from tests._coords import EXPANSION_TO_VERSION, validate_map_buckets


@pytest.mark.parametrize("version", sorted(set(EXPANSION_TO_VERSION.values())))
def test_pack_loader_builds_expected_indexes(version: str, coordinate_runtimes: dict[str, dict]) -> None:
    runtime = coordinate_runtimes[version]
    pack = runtime["pack"]

    assert int(pack["manifest"]["schemaVersion"]) == 2
    assert pack["zoneSpaceByAreaId"]
    assert pack["projectionBoundsByKey"]
    assert pack["legacyBasisByKey"]
    assert isinstance(pack["instanceAnchorByMapId"], dict)

    assert len(pack["zoneSpaceByAreaId"]) == len(pack["zoneSpaces"])
    assert len(pack["projectionBoundsByKey"]) == len(pack["projectionBounds"])
    assert len(pack["legacyBasisByKey"]) == len(pack["legacyBases"])
    assert len(pack["instanceAnchorByMapId"]) == len(pack["instanceAnchors"])


def test_pack_loader_rejects_unsupported_schema_version(tmp_path, coordinate_runtimes: dict[str, dict]) -> None:
    loader_module = coordinate_runtimes["v3"]["loader"]
    pack_dir = tmp_path / "bad_pack"
    pack_dir.mkdir()

    files = {
        "manifest.json": {"schemaVersion": 999, "flavor": "broken"},
        "zone_spaces.json": [],
        "projection_bounds.json": [],
        "map_defaults.json": [],
        "legacy_bases.json": [],
        "instance_anchors.json": [],
    }
    for filename, payload in files.items():
        (pack_dir / filename).write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported coordinate pack schemaVersion=999"):
        loader_module.load_coordinate_pack(pack_dir)


@pytest.mark.parametrize("version", sorted(set(EXPANSION_TO_VERSION.values())))
def test_projection_round_trip_is_identity_for_same_bounds(
    version: str,
    coordinate_runtimes: dict[str, dict],
) -> None:
    converter = coordinate_runtimes[version]["converter"]
    bounds = coordinate_runtimes[version]["pack"]["projectionBounds"][0]

    for zone_x, zone_y in ((0.0, 0.0), (12.34, 56.78), (99.99, 33.33), (100.0, 100.0)):
        world_x, world_y = converter.invert_zone_percent_to_world(bounds, zone_x, zone_y)
        projected_x, projected_y = converter.project_world_to_percent(bounds, world_x, world_y)
        assert projected_x == pytest.approx(zone_x)
        assert projected_y == pytest.approx(zone_y)


def test_target_coord_ui_map_id_prefers_default_then_parent_then_zone(
    coordinate_runtimes: dict[str, dict],
) -> None:
    converter = coordinate_runtimes["v3"]["converter"]
    pack = {"mapDefaultByMapId": {1: 999}}

    assert converter._target_coord_ui_map_id(
        pack,
        {"mapId": 1, "parentUiMapId": 123, "zoneUiMapId": 456},
    ) == 999
    assert converter._target_coord_ui_map_id(
        pack,
        {"mapId": 2, "parentUiMapId": 123, "zoneUiMapId": 456},
    ) == 123
    assert converter._target_coord_ui_map_id(
        pack,
        {"mapId": 3, "parentUiMapId": None, "zoneUiMapId": 456},
    ) == 456


def test_unknown_instance_bucket_is_preserved_without_anchors_for_v1_zone_719(
    coordinate_runtimes: dict[str, dict],
) -> None:
    converter = coordinate_runtimes["v1"]["converter"]
    pack = coordinate_runtimes["v1"]["pack"]

    converted = converter.convert_zone_buckets(pack, {719: [[-1.0, -1.0]]})
    assert converted == {48: {0: [[-1.0, -1.0]]}}

    replaced = converter.replace_unknown_instance_buckets(pack, converted)
    assert replaced == converted


def test_known_unknown_bucket_without_anchor_is_preserved_for_v1_zone_2677(
    coordinate_runtimes: dict[str, dict],
) -> None:
    converter = coordinate_runtimes["v1"]["converter"]
    pack = coordinate_runtimes["v1"]["pack"]

    converted = converter.convert_zone_buckets(pack, {2677: [[-1.0, -1.0]]})
    assert converted == {469: {0: [[-1.0, -1.0]]}}
    assert converter.replace_unknown_instance_buckets(pack, converted) == converted


def test_unresolved_instance_with_real_point_raises_for_known_v3_legacy_keys(
    coordinate_runtimes: dict[str, dict],
) -> None:
    converter = coordinate_runtimes["v3"]["converter"]
    pack = coordinate_runtimes["v3"]["pack"]

    with pytest.raises(ValueError, match="Legacy key=4131 maps to unresolved instance space"):
        converter.convert_zone_buckets(pack, {4131: [[42.53, 23.6], [-1.0, -1.0]]})

    with pytest.raises(ValueError, match="Legacy key=2257 maps to unresolved instance space"):
        converter.convert_zone_buckets(pack, {2257: [[52.15, 47.69], [-1.0, -1.0]]})


def test_known_v3_legacy_basis_appends_default_ui_map_hint_id(
    coordinate_runtimes: dict[str, dict],
) -> None:
    converter = coordinate_runtimes["v3"]["converter"]
    pack = coordinate_runtimes["v3"]["pack"]

    converted = converter.convert_zone_buckets(pack, {4395: [[12.34, 56.78]]})
    assert converted == {571: {113: [[12.34, 56.78, 125]]}}
    assert validate_map_buckets(converted) == []
