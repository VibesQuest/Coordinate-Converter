from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._coords import EXPANSION_TO_VERSION, iter_zone_bucket_cases, load_runtime_modules


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def corrections_data(repo_root: Path) -> dict:
    candidates = (
        repo_root / "ui" / "public" / "corrections.json",
        repo_root / "tests" / "data" / "corrections.json",
    )
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "No corrections.json found; checked: " + ", ".join(str(path) for path in candidates)
    )


@pytest.fixture(scope="session")
def corrections_cases(corrections_data: dict) -> list:
    return list(iter_zone_bucket_cases(corrections_data))


@pytest.fixture(scope="session")
def coordinate_runtimes(repo_root: Path) -> dict[str, dict]:
    runtimes: dict[str, dict] = {}
    for version in sorted(set(EXPANSION_TO_VERSION.values())):
        loader_module, converter_module = load_runtime_modules(repo_root, version)
        runtimes[version] = {
            "loader": loader_module,
            "converter": converter_module,
            "pack": loader_module.load_coordinate_pack(_find_pack_dir(repo_root, version)),
        }
    return runtimes


def _find_pack_dir(repo_root: Path, version: str) -> Path:
    candidates = (repo_root / "output" / version,)
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"No pack directory found for {version}; checked: "
        + ", ".join(str(path) for path in candidates)
    )
