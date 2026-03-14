from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest


SUCCESS_CASES: dict[str, str] = {
    "normal_zone_reproject_elwynn": "v3",
    "dalaran_top_level_identity": "v3",
    "underbelly_identity": "v3",
    "shadowfang_unresolved": "v1",
    "blackfathom_unresolved": "v1",
    "scarlet_monastery_unresolved": "v1",
    "blackrock_spire_unresolved": "v1",
    "deeprun_tram_unresolved": "v3",
    "fake_ubrs_alias": "v3",
    "dire_maul_identity_real_coord": "v3",
    "dire_maul_unresolved": "v3",
    "mixed_wotlk_payload": "v3",
}

ERROR_CASES: dict[str, dict[str, str]] = {
    "unknown_legacy_key_error": {
        "version": "v3",
        "type": "KeyError",
        "match": "No coordinate mapping for legacy key=999999",
    },
    "malformed_point_error": {
        "version": "v3",
        "type": "ValueError",
        "match": "Expected coordinate pair for zoneAreaId=4395",
    },
}


@pytest.mark.parametrize("case_name", sorted(SUCCESS_CASES))
def test_converter_golden_outputs_match_expected_fixture(
    case_name: str,
    coordinate_runtimes: dict[str, dict],
    repo_root: Path,
) -> None:
    fixture_dir = repo_root / "tests" / "fixtures" / "converter_golden" / case_name
    input_payload = _normalize_zone_buckets_json(_load_json(fixture_dir / "input.json"))
    expected = _normalize_map_buckets_json(_load_json(fixture_dir / "expected.json"))

    runtime = coordinate_runtimes[SUCCESS_CASES[case_name]]
    converter = runtime["converter"]
    pack = runtime["pack"]

    converted = converter.convert_zone_buckets(pack, input_payload)
    replaced = converter.replace_unknown_instance_buckets(pack, converted)

    assert converted == expected
    assert replaced == expected


@pytest.mark.parametrize("case_name", sorted(ERROR_CASES))
def test_converter_golden_errors_match_expected_behavior(
    case_name: str,
    coordinate_runtimes: dict[str, dict],
    repo_root: Path,
) -> None:
    fixture_dir = repo_root / "tests" / "fixtures" / "converter_golden" / case_name
    input_payload = _normalize_zone_buckets_json(_load_json(fixture_dir / "input.json"))
    case = ERROR_CASES[case_name]
    runtime = coordinate_runtimes[case["version"]]
    converter = runtime["converter"]
    pack = runtime["pack"]

    error_type = getattr(builtins, case["type"])
    with pytest.raises(error_type, match=case["match"]):
        converter.convert_zone_buckets(pack, input_payload)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_zone_buckets_json(data: dict[str, object]) -> dict[int, list[list[float]]]:
    return {
        int(zone_area_id): [[float(value) for value in point] for point in points]
        for zone_area_id, points in data.items()
    }


def _normalize_map_buckets_json(
    data: dict[str, dict[str, list[list[float | int]]]],
) -> dict[int, dict[int, list[list[float | int]]]]:
    return {
        int(map_id): {
            int(coord_ui_map_id): [list(point) for point in points]
            for coord_ui_map_id, points in coord_buckets.items()
        }
        for map_id, coord_buckets in data.items()
    }
