from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .common import build_generic_table


TABLE_NAME = "Map"
DB2_NAME = "Map"
CSV_PATTERN = re.compile(r"Map\.(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d+)\.csv")


def build_table(conn: sqlite3.Connection, csv_path: Path, major_version: str | None) -> int:
    return build_generic_table(
        conn,
        csv_path,
        table_name="map",
        major_version=major_version,
        index_columns=["ID"],
    )

