from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._portable_coords import EXPANSION_TO_VERSION, iter_zone_bucket_cases, load_runtime_modules


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def corrections_data(repo_root: Path) -> dict:
    return json.loads((repo_root / "ui" / "public" / "corrections.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def corrections_cases(corrections_data: dict) -> list:
    return list(iter_zone_bucket_cases(corrections_data))


@pytest.fixture(scope="session")
def portable_runtimes(repo_root: Path) -> dict[str, dict]:
    runtimes: dict[str, dict] = {}
    for version in sorted(set(EXPANSION_TO_VERSION.values())):
        loader_module, converter_module = load_runtime_modules(repo_root, version)
        runtimes[version] = {
            "loader": loader_module,
            "converter": converter_module,
            "pack": loader_module.load_portable_coordinate_pack(repo_root / "portable_coords" / version),
        }
    return runtimes
