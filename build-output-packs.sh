#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${ROOT_DIR}/../sources/dbc/data"
DBC_OUT_DIR="${ROOT_DIR}/dbc-output"
PACK_OUT_DIR="${ROOT_DIR}/output"

cd "${ROOT_DIR}"

build_version() {
  local major_version="$1"
  local dbc_db="${DBC_OUT_DIR}/dbc-source-v${major_version}.db"
  local pack_dir="${PACK_OUT_DIR}/v${major_version}"

  mkdir -p "${DBC_OUT_DIR}" "${PACK_OUT_DIR}"

  uv run python -m src.dbc_source.main \
    --major-version "${major_version}" \
    --data-dir "${DATA_DIR}" \
    --out "${dbc_db}" \
    --offline

  uv run python -m src.build_pack \
    --major-version "${major_version}" \
    --dbc-db "${dbc_db}" \
    --output-dir "${pack_dir}"
}

main() {
  if [[ $# -gt 1 ]]; then
    echo "Usage: bash build-output-packs.sh [major_version]" >&2
    exit 1
  fi

  if [[ $# -eq 1 ]]; then
    build_version "$1"
    exit 0
  fi

  build_version 1
  build_version 2
  build_version 3
}

main "$@"
