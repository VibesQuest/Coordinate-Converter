# Coordinate Converter

`coordinate-converter` builds small JSON coordinate packs from WoW DBC/DB2 metadata and uses those packs to convert old legacy zone buckets into modern `{mapId -> coordUiMapId -> points}` buckets.

This project exists to solve one specific problem cleanly:

- old correction data often stores coordinates under legacy area ids
- modern consumers often want coordinates grouped by `mapId` and `UiMapID`
- some legacy ids are normal zones, some are instance aliases, and some are hand-authored fake floor ids

This repo converts those old keys into a stable portable pack and ships small runtime implementations for:

- Python
- TypeScript
- Lua

## What It Does

The converter handles:

- normal zone-space reprojection
- identity rebucketing when the old numbers already live in the target basis
- unresolved instance aliasing as `[mapId][0] -> [[-1.0, -1.0]]`
- explicit manual overrides for known legacy oddities
- fake floor/sub-map ids that need to resolve to a specific `UiMapID`

The output format is designed for downstream tools that already know how to deal with `mapId` buckets.

Example input:

```json
{
  "4395": [[48.34, 41.48]],
  "2257": [[-1, -1]]
}
```

Example output:

```json
{
  "571": {
    "113": [[48.34, 41.48, 125]]
  },
  "369": {
    "0": [[-1.0, -1.0]]
  }
}
```

## What It Does Not Do

This project is intentionally narrow.

It does not depend on:

- `core-vN.db`
- `zoneid-calculator.db`
- exporter/core monorepo code

It also does not try to:

- reconstruct dungeon entrances
- replay spawn exports
- turn unresolved `[-1, -1]` points into recovered entrance points

If a legacy key maps to unresolved instance space, this project keeps it unresolved and only moves it into the correct `mapId` bucket.

## How It Works

The pipeline has two stages.

### 1. Build a small SQLite metadata DB

The DBC source step reads only:

- `AreaTable`
- `Map`
- `UiMap`
- `UiMapAssignment`

and writes a minimal SQLite DB.

### 2. Build a portable coordinate pack

The pack builder uses that DB to generate:

- `manifest.json`
- `zone_spaces.json`
- `projection_bounds.json`
- `map_defaults.json`
- `legacy_bases.json`
- `instance_anchors.json`
- `runtime/`

The runtime pack is then used by the CLI or by the shipped language runtimes.

## Supported Scope

The repo currently has tested corpus coverage for:

- `v1` / `classic`
- `v2` / `tbc`
- `v3` / `wotlk`
- `v4` / `cata`
- `v5` / `mop`

The builder is version-aware beyond that, but the currently verified correction-data coverage is the list above.

## Project Layout

- [src/build_pack.py](/home/logon/projects/coordinate-converter/src/build_pack.py)
  DBC-driven pack builder
- [src/converter.py](/home/logon/projects/coordinate-converter/src/converter.py)
  reference Python converter
- [src/manual_overrides.py](/home/logon/projects/coordinate-converter/src/manual_overrides.py)
  manual aliases, fake floor mappings, fixed-point overrides
- [src/models.py](/home/logon/projects/coordinate-converter/src/models.py)
  pack schema and load/dump logic
- [src/dbc_source](/home/logon/projects/coordinate-converter/src/dbc_source)
  CSV/DBC to SQLite metadata builder
- [src/assets](/home/logon/projects/coordinate-converter/src/assets)
  shipped Python/TypeScript/Lua runtime assets
- [src/edge_cases](/home/logon/projects/coordinate-converter/src/edge_cases)
  notes and inspection tools for weird conversion cases
- [build-output-packs.sh](/home/logon/projects/coordinate-converter/build-output-packs.sh)
  convenience script for test + build flow
- [HANDOVER.md](/home/logon/projects/coordinate-converter/HANDOVER.md)
  deeper implementation notes

## Commands

Build one DBC metadata DB:

```bash
coordinate-dbc-source \
  --major-version 3 \
  --data-dir sources/dbc/data \
  --out dbc-output/dbc-source-v3.db
```

Build one coordinate pack:

```bash
coordinate-converter build-pack \
  --major-version 3 \
  --dbc-db dbc-output/dbc-source-v3.db \
  --output-dir output/v3
```

Convert old zone buckets with a built pack:

```bash
coordinate-converter convert-zone-buckets \
  --pack-dir output/v3 \
  --input-json input.json \
  --output-json output.json
```

Run the repo build script:

```bash
bash build-output-packs.sh
```

Important:

- the build script runs the test suite first
- if tests fail, it stops before building packs

Build one version only:

```bash
bash build-output-packs.sh 3
```

## Why You Would Use This

Use this project if you need to:

- migrate old zone-keyed correction data into modern map/uiMap buckets
- ship a small standalone runtime without depending on a larger WoW data stack
- keep coordinate conversion logic portable across multiple languages
- handle known legacy edge cases explicitly instead of re-deriving them in every consumer

## Current Quality Bar

The repo currently includes:

- fixture-style golden tests
- corpus conversion tests against imported corrections data
- runtime tests against the shipped Python runtime packs
- direct source-class tests for the reference converter

At the time of writing, the supported corpus scope is green.

## More Detail

For deeper design notes, edge-case explanations, and fake-id mapping research, see:

- [HANDOVER.md](/home/logon/projects/coordinate-converter/HANDOVER.md)
