# Coordinate Converter

Standalone coordinate converter with:

- JSON pack runtime and converter
- copied Python / TypeScript / Lua runtime assets
- a minimal DBC-driven metadata builder
- no dependency on `core-vN.db`
- no dependency on `zoneid-calculator.db`

## Scope

This standalone project intentionally keeps the conversion dumb:

- old keys are mapped to `mapId` / `coordUiMapId` / optional hint
- clean zone-space coordinates are reprojected
- map-space fallback coordinates are kept as-is
- `{-1,-1}` stays `{-1,-1}`
- instance entrance resolution is out of scope

That means the output is suitable for downstream systems that already have a
separate dungeon / instance lookup keyed by `mapId`.

## Inputs

To build packs, this project only needs metadata from these DBC/DB2 tables:

- `AreaTable`
- `Map`
- `UiMap`
- `UiMapAssignment`

The project can build a small SQLite source DB from Wago CSV exports.

## Commands

Build everything for `v1`, `v2`, and `v3` using the repo's existing DBC CSVs:

```bash
bash build-output-packs.sh
```

Build one version only:

```bash
bash build-output-packs.sh 3
```

Or run the steps manually.

Build a minimal DBC source DB:

```bash
coordinate-dbc-source \
  --major-version 3 \
  --offline \
  --data-dir /path/to/dbc-csvs \
  --out dbc-source-v3.db
```

Build a coordinate pack from that DBC DB:

```bash
coordinate-converter build-pack \
  --major-version 3 \
  --dbc-db dbc-source-v3.db \
  --output-dir output/v3
```

Convert old zone buckets:

```bash
coordinate-converter convert-zone-buckets \
  --pack-dir output/v3 \
  --input-json input.json \
  --output-json output.json
```

## Notes

- The runtime pack format matches the current coordinate-pack contract.
- `instance_anchors.json` is emitted as an empty list in this standalone version.
- Manual aliases and basis overrides live in `src/manual_overrides.py`.
- Generated packs are written under `output/v1`, `v2`, and `v3`.
