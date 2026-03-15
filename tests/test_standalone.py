from __future__ import annotations

from pathlib import Path

import pytest

from src.build_pack import build_coordinate_pack
from src.converter import CoordinateConverter


ROOT = Path(__file__).resolve().parents[2]
DBC_V3 = ROOT / "sources" / "dbc" / "output" / "dbc-source-v3.db"


@pytest.mark.skipif(not DBC_V3.exists(), reason="repo DBC source DB is unavailable")
def test_wotlk_standalone_pack_handles_known_legacy_keys() -> None:
    pack = build_coordinate_pack(major_version=3, dbc_db_path=DBC_V3)
    converter = CoordinateConverter(pack)

    result = converter.convert_zone_buckets(
        {
            4395: [[48.34, 41.48]],
            4560: [[47.11, 54.22]],
            2257: [[-1, -1]],
            7307: [[-1, -1]],
        }
    )

    assert result[571][113] == [
        [48.34, 41.48, 125],
        [47.11, 54.22, 126],
    ]
    assert result[369][0] == [[-1.0, -1.0]]
    assert result[229][0] == [[-1.0, -1.0]]


@pytest.mark.skipif(not DBC_V3.exists(), reason="repo DBC source DB is unavailable")
def test_source_converter_preserves_unknown_buckets_without_anchors() -> None:
    pack = build_coordinate_pack(major_version=3, dbc_db_path=DBC_V3)
    converter = CoordinateConverter(pack)

    replaced = converter.replace_unknown_instance_buckets(
        {
            369: {0: [[-1.0, -1.0]]},
            571: {113: [[48.34, 41.48, 125]]},
        }
    )

    assert replaced == {
        369: {0: [[-1.0, -1.0]]},
        571: {113: [[48.34, 41.48, 125]]},
    }
