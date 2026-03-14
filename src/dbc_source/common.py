from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import requests


VERSIONS_URL = "https://wago.tools/db2"
DOWNLOAD_URL_TEMPLATE = "https://wago.tools/db2/{table}/csv?build={build}"


def download_file(url: str, destination: Path) -> bool:
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        destination.write_bytes(response.content)
        return True
    except requests.exceptions.RequestException:
        return False


def get_all_versions() -> list[str]:
    try:
        response = requests.get(VERSIONS_URL, timeout=30)
        response.raise_for_status()
        response_text = response.text.replace("&quot;", "\"")
        return re.findall(r"(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d+)", response_text)
    except requests.exceptions.RequestException:
        return []


def get_latest_version(major_version: str, all_versions: Iterable[str]) -> str | None:
    largest_version = 0
    largest_version_str = ""
    for version in all_versions:
        split_version = version.split(".")
        build_number = split_version[-1]
        if split_version[0] == major_version and int(build_number) > largest_version:
            largest_version = int(build_number)
            largest_version_str = version
    return largest_version_str or None


def list_local_versions(data_dir: Path, pattern: re.Pattern) -> list[str]:
    versions: list[str] = []
    if not data_dir.exists():
        return versions
    for path in data_dir.iterdir():
        if not path.is_file():
            continue
        match = pattern.fullmatch(path.name)
        if match:
            versions.append(match.group(1))
    return versions


def resolve_build(
    build: str,
    all_versions: Iterable[str] | None = None,
    data_dir: Path | None = None,
    csv_pattern: re.Pattern | None = None,
) -> str | None:
    if not build:
        return None
    if build.isdigit():
        versions = list(all_versions) if all_versions is not None else []
        if not versions and data_dir is not None and csv_pattern is not None:
            versions = list_local_versions(data_dir, csv_pattern)
        return get_latest_version(build, versions) if versions else None
    return build


def download_csv(table_name: str, build_version: str, data_dir: Path) -> Path | None:
    filename = f"{table_name}.{build_version}.csv"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / filename
    if data_path.exists():
        return data_path
    url = DOWNLOAD_URL_TEMPLATE.format(table=table_name, build=build_version)
    if download_file(url, data_path):
        return data_path
    return None


def quote_identifier(identifier: str) -> str:
    escaped = identifier.replace("\"", "\"\"")
    return f"\"{escaped}\""


def infer_type(value: str) -> str:
    if value == "":
        return "int"
    try:
        int(value)
        return "int"
    except ValueError:
        try:
            float(value)
            return "float"
        except ValueError:
            return "text"


def merge_type(current: str, candidate: str) -> str:
    if current == "text" or candidate == "text":
        return "text"
    if current == "float" or candidate == "float":
        return "float"
    return "int"


def infer_column_types(csv_path: Path, columns: list[str]) -> dict[str, str]:
    types = {col: "int" for col in columns}
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for col in columns:
                value = row.get(col, "") or ""
                types[col] = merge_type(types[col], infer_type(value))
    return types


def build_generic_table(
    conn: sqlite3.Connection,
    csv_path: Path,
    table_name: str,
    major_version: str | None,
    index_columns: list[str] | None = None,
) -> int:
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        raw_columns = reader.fieldnames or []
        if not raw_columns:
            raise ValueError(f"No columns found in {csv_path}")

    col_types = infer_column_types(csv_path, raw_columns)
    sqlite_columns = []
    for col in raw_columns:
        col_type = "INTEGER" if col_types[col] == "int" else "REAL" if col_types[col] == "float" else "TEXT"
        sqlite_columns.append(f"{quote_identifier(col)} {col_type}")
    sqlite_columns.append(f'{quote_identifier("major_version")} TEXT')

    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(f"CREATE TABLE {table_name} ({', '.join(sqlite_columns)})")

    insert_columns = list(raw_columns) + ["major_version"]
    placeholders = ", ".join(["?"] * len(insert_columns))
    insert_sql = (
        f"INSERT INTO {table_name} ("
        + ", ".join(quote_identifier(col) for col in insert_columns)
        + f") VALUES ({placeholders})"
    )

    batch: list[list[object | None]] = []
    batch_size = 5000
    row_count = 0
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            values: list[object | None] = []
            for col in raw_columns:
                raw_value = row.get(col, "")
                if raw_value == "":
                    values.append(None)
                    continue
                value_type = col_types[col]
                if value_type == "int":
                    values.append(int(raw_value))
                elif value_type == "float":
                    values.append(float(raw_value))
                else:
                    values.append(raw_value)
            values.append(major_version)
            batch.append(values)
            row_count += 1
            if len(batch) >= batch_size:
                conn.executemany(insert_sql, batch)
                batch = []
        if batch:
            conn.executemany(insert_sql, batch)

    if index_columns:
        for col in index_columns:
            if col in raw_columns:
                idx_name = f"idx_{table_name}_{col.lower()}"
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({quote_identifier(col)})"
                )
    return row_count

