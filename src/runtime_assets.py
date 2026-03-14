from __future__ import annotations

import shutil
from pathlib import Path


def copy_runtime_assets(output_dir: str | Path) -> None:
    """Copy standalone runtime loaders and example scripts beside a pack."""
    destination_root = Path(output_dir) / "runtime"
    source_root = Path(__file__).parent / "assets"
    destination_root.mkdir(parents=True, exist_ok=True)

    for src_file in source_root.glob("*.md"):
        shutil.copy2(src_file, destination_root / src_file.name)

    for language_dir in ("python", "typescript", "lua"):
        src = source_root / language_dir
        dst = destination_root / language_dir
        shutil.copytree(src, dst, dirs_exist_ok=True)
