from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .common import build_generic_table


TABLE_NAME = "UiMapAssignment"
DB2_NAME = "UiMapAssignment"
CSV_PATTERN = re.compile(r"UiMapAssignment\.(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d+)\.csv")


def build_table(conn: sqlite3.Connection, csv_path: Path, major_version: str | None) -> int:
    return build_generic_table(
        conn,
        csv_path,
        table_name="ui_map_assignment",
        major_version=major_version,
        index_columns=["ID", "MapID", "UiMapID"],
    )

