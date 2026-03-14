# Runtime Bundle

This folder is copied into each built coordinate pack.

## Included Runtimes

- `python/`
- `typescript/`
- `lua/`

Each runtime includes:

- a JSON pack loader
- a standalone converter implementation
- example scripts for loading and converting data

The Lua runtime includes a bundled pure-Lua JSON decoder and has no external
dependency requirement.
