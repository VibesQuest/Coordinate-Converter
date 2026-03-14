# Coordinate Converter Handover

## Purpose

This project is a standalone coordinate converter.

It is intentionally a **dumb converter**:

- no `core-vN.db`
- no `zoneid-calculator.db`
- no dungeon entrance recovery
- `{-1,-1}` stays unresolved
- goal is only to convert old legacy buckets into new `{[mapId]={[coordUiMapId]=...}}` shape

The downstream system is expected to already have access to `dungeonLookupDB.lua` or equivalent lookup keyed by `mapId`.

## Current Contract

### Input

Old-style coordinate buckets:

```json
{
  "4395": [[48.34, 41.48]],
  "2257": [[-1, -1]]
}
```

### Output

New-style map/uiMap buckets:

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

### Rules

- clean zone-space keys can reproject
- containing-map fallback keys keep the same numbers and only change bucketing
- unresolved instance-style keys map to `[mapId][0]`
- no attempt is made here to replace `[mapId][0]={{-1,-1}}` with entrance points

## Project Layout

- `src/models.py`
  Pack schema, load/dump logic, runtime asset copy.
- `src/converter.py`
  Reference converter used by the CLI.
- `src/build_pack.py`
  Standalone builder from DBC metadata.
- `src/manual_overrides.py`
  Manual aliases and basis overrides.
- `src/ui_map_selection.py`
  Local coord-ui-map selection logic.
- `src/dbc_source/`
  Minimal DBC/CSV -> SQLite builder for:
  - `AreaTable`
  - `Map`
  - `UiMap`
  - `UiMapAssignment`
- `build-output-packs.sh`
  Builds `v1`, `v2`, and `v3` outputs inside this project.
- `output/v1`, `output/v2`, `output/v3`
  Generated packs and runtime bundle.

## What Was Ported

These parts were adapted from the earlier coordinate conversion implementation:

- pack/runtime model
- reference converter
- copied runtime assets for Python / TypeScript / Lua

These parts were rewritten locally:

- pack builder
- DBC source builder
- manual override layer
- uiMap default selection helper

## What Was Intentionally Not Ported

- `core-vN.db`
- `zoneid-calculator.db`
- spawn replay / old exporter behavior reconstruction
- dungeon entrance lookup / anchor projection
- `exporters.questie*` dependencies

This project should stay independent of those.

## Data Inputs

The standalone builder uses only DBC-style metadata:

- `AreaTable`
- `Map`
- `UiMap`
- `UiMapAssignment`

In this repo, the helper script reads the CSVs from:

- `../sources/dbc/data`

and writes temporary SQLite DBs to:

- `dbc-output/`

That folder is ignored and can be regenerated.

## Important Logic

### Legacy basis generation

Current sources of `legacy_bases.json`:

1. zone-space records from top-level area/uiMap assignments
2. direct area-basis records from `UiMapAssignment.AreaID`
3. unresolved instance aliases from `AreaTable.ContinentID` / `Map.AreaTableID`
4. parent-basis inheritance
5. manual basis overrides
6. manual key aliases
7. degenerate reproject normalization

### Unresolved instance behavior

This project does **not** resolve entrances.

It only ensures that old unresolved instance-style keys become:

```json
{
  "mapId": {
    "0": [[-1.0, -1.0]]
  }
}
```

Examples:

- `2257 -> [369][0]`
- `7307 -> [229][0]`

## Manual Overrides

Current important overrides in `manual_overrides.py`:

- `7307 -> 1583`
  Fake UBRS key should map to Blackrock Spire.
- `4395 -> map 571, uiMap 113, hint 125`
  Dalaran top-level.
- `4560 -> map 571, uiMap 113, hint 126`
  Underbelly.
- `2557 -> map 429, uiMap 235`
  Dire Maul orphan/broken basis normalization.

If more legacy oddities appear, prefer keeping them here as explicit data rather than spreading conditionals through the converter.

## Known Good Cases

Verified working:

- Dalaran `4395`
- Underbelly `4560`
- Deeprun Tram `2257`
- fake UBRS key `7307`
- unresolved instance aliases like `209`, `719`, `796`, `1583`
- Dire Maul `2557`

## Fake UiMap Alias Research

These are the fake legacy ids from the imported corrections corpus that were
matched to specific `UiMapID`s before implementation.

How the matching was done:

1. take the fake id and Questie's floor/sub-zone label
2. map it to the Questie override `UiMapID`
3. look up that `UiMapID` in `dbc-output/dbc-source-v3.db`
4. read `ui_map.Name_lang` to confirm the DBC-side parent map name

Useful query:

```sql
SELECT "ID", "Name_lang"
FROM ui_map
WHERE "ID" IN (...);
```

Important note:

- many of these DBC names are the parent dungeon/raid name, not the specific
  floor label from Questie
- that is expected; the fake id is carrying floor/sub-zone meaning that the
  plain DBC `Name_lang` often does not preserve

### WotLK Fake IDs

| Fake ID | Questie Label | Matched UiMapID | DBC UiMap Name |
| --- | --- | --- | --- |
| `10002` | `Blackrock Depths - Shadowforge City` | `243` | `Blackrock Depths` |
| `10047` | `The Oculus - Band of Acceleration` | `144` | `The Oculus` |
| `10048` | `The Oculus - Band of Transmutation` | `145` | `The Oculus` |
| `10049` | `The Oculus - Band of Alignment` | `146` | `The Oculus` |
| `10050` | `Ulduar - The Descent of Madness` | `150` | `Ulduar` |
| `10051` | `Ulduar - The Spark of Imagination` | `151` | `Ulduar` |
| `10052` | `Ulduar - The Inner Sanctum of Ulduar` | `149` | `Ulduar` |
| `10053` | `Utgarde Pinnacle - Lower Level` | `136` | `Utgarde Pinnacle` |
| `10054` | `Halls of Lightning - The Terrestrial Watchtower` | `139` | `Halls of Lightning` |
| `10055` | `Azjol-Nerub - The Brood Pit` | `157` | `Azjol-Nerub` |
| `10056` | `Azjol-Nerub - Hadronox's Lair` | `158` | `Azjol-Nerub` |
| `10057` | `Utgarde Keep - Middle Level` | `134` | `Utgarde Keep` |
| `10058` | `Utgarde Keep - Upper Level` | `135` | `Utgarde Keep` |
| `10059` | `The Culling of Stratholme - City` | `131` | `The Culling of Stratholme` |
| `10060` | `Drak'Tharon Keep - Upper Level` | `161` | `Drak'Tharon Keep` |
| `10061` | `Gundrak - Lower Level` | `153` | `Gundrak` |
| `10062` | `Naxxramas - Construct Quarter` | `162` | `Naxxramas` |
| `10063` | `Naxxramas - Arachnid Quarter` | `163` | `Naxxramas` |
| `10064` | `Naxxramas - Military Quarter` | `164` | `Naxxramas` |
| `10065` | `Naxxramas - Plague Quarter` | `165` | `Naxxramas` |
| `10066` | `Naxxramas - Frostwyrm Lair` | `167` | `Naxxramas` |
| `10067` | `Icecrown Citadel - Rampart of Skulls` | `187` | `Icecrown Citadel` |
| `10068` | `Icecrown Citadel - Deathbringer's Rise` | `188` | `Icecrown Citadel` |
| `10069` | `Icecrown Citadel - Sindragosa` | `189` | `Icecrown Citadel` |
| `10070` | `Icecrown Citadel - Upper Spire` | `190` | `Icecrown Citadel` |
| `10071` | `Icecrown Citadel - Queen Lana'thel` | `191` | `Icecrown Citadel` |
| `10072` | `Icecrown Citadel - The Frozen Throne` | `192` | `Icecrown Citadel` |

## Commands

Build all outputs:

```bash
bash build-output-packs.sh
```

Build one version:

```bash
bash build-output-packs.sh 3
```

Run the standalone test:

```bash
uv run pytest tests/test_standalone.py -q
```

Run the bundled Python runtime example:

```bash
uv run python output/v3/runtime/python/example_convert.py
```

## Validation Already Performed

Completed in this workspace:

- `bash build-output-packs.sh`
- `uv run pytest tests/test_standalone.py -q`
- `uv run python -m py_compile src/*.py src/dbc_source/*.py`
- `uv run python output/v3/runtime/python/example_convert.py`

## Open Questions / Next Likely Work

These are the most likely follow-ups:

1. Decide whether parent-basis inheritance is still too broad for standalone usage.
2. Expand manual overrides if more fake / overloaded legacy keys are found.
3. Decide whether to keep generated `output/v1..v3` committed in the new repo.
4. Decide whether to keep the copied runtime assets exactly as-is or trim example files.
5. If desired later, add Cata / MoP support once matching DBC inputs are available.

## Notes For The Next Agent

- The package name is `src`.
- The repo directory name is `coordinate-converter`.
- `tests/conftest.py` injects the project root into `sys.path` so pytest works without packaging/install steps.
- `.gitignore` ignores:
  - `.venv/`
  - `*.egg-info/`
  - `__pycache__/`
  - `dbc-output/`
- `output/` is not ignored.

## Recommended First Check After Moving

After moving this code to its new repo, verify these in order:

1. `uv run pytest tests/test_standalone.py -q`
2. `bash build-output-packs.sh 3`
3. inspect `output/v3/legacy_bases.json` for:
   - `4395`
   - `4560`
   - `2257`
   - `7307`
   - `2557`
4. run `uv run python output/v3/runtime/python/example_convert.py`
