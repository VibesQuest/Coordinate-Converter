from __future__ import annotations

from pathlib import Path

from coords_converter import (
    convert_zone_buckets,
    replace_unknown_instance_buckets,
)
from coords_loader import load_coordinate_pack


def main() -> None:
    pack_root = Path(__file__).resolve().parents[2]
    pack = load_coordinate_pack(pack_root)

    zone_result = convert_zone_buckets(
        pack,
        {
            12: [[42.1, 65.3]],
        },
    )
    instance_result = replace_unknown_instance_buckets(
        pack,
        {
            36: {
                0: [[-1, -1]],
            }
        },
    )

    print("zone conversion:", zone_result)
    print("instance fallback:", instance_result)


if __name__ == "__main__":
    main()
