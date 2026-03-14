from __future__ import annotations

from pathlib import Path

from coords_loader import load_coordinate_pack


def main() -> None:
    pack_root = Path(__file__).resolve().parents[2]
    pack = load_coordinate_pack(pack_root)

    zone = pack["zoneSpaceByAreaId"].get(12)
    default_coord = pack["mapDefaultByMapId"].get(0)

    print("flavor:", pack["manifest"]["flavor"])
    print("zone 12 source:", zone)
    print("map 0 default coordUiMapId:", default_coord)


if __name__ == "__main__":
    main()
