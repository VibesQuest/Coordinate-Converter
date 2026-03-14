from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .common import build_generic_table


TABLE_NAME = "AreaTable"
DB2_NAME = "AreaTable"
CSV_PATTERN = re.compile(r"AreaTable\.(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d+)\.csv")


def build_table(conn: sqlite3.Connection, csv_path: Path, major_version: str | None) -> int:
    return build_generic_table(
        conn,
        csv_path,
        table_name="area_table",
        major_version=major_version,
        index_columns=["ID", "ContinentID", "ParentAreaID"],
    )

