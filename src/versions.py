from __future__ import annotations


KNOWN_FLAVOR_BY_MAJOR_VERSION = {
    1: "classic",
    2: "tbc",
    3: "wotlk",
    4: "cata",
    5: "mop",
}


def flavor_for_major_version(major_version: int) -> str:
    major_version = int(major_version)
    if major_version <= 0:
        raise ValueError(f"Unsupported major version: {major_version}")
    return KNOWN_FLAVOR_BY_MAJOR_VERSION.get(major_version, f"v{major_version}")
