# sims4mcp — AGENTS.md

## Stack

Python 3.11+ project. Package manager: pip / hatchling.

Key dependencies: `click` (CLI), `lz4` (save decompression), `mcp` (MCP server), `pydantic` (models).

Entrypoints:
- `sims4mcp` CLI — `src/sims4mcp/cli.py` via `pyproject.toml` `[project.scripts]`
- MCP server — `src/sims4mcp/mcp_server.py` run via `mcp run src/sims4mcp/mcp_server.py`
- Library API — `from sims4mcp import load_save, SaveFile, Sim, ...`

## Dev commands

```sh
pip install -e .                    # install in editable mode
python -m sims4mcp info <save>     # CLI usage
mcp run src/sims4mcp/mcp_server.py # start MCP server over stdio
```

## Architecture

```
src/sims4mcp/
  __init__.py   — public API re-exports
  __main__.py   — `python -m sims4mcp` entry
  models.py     — pydantic / dataclass models (Sim, Household, …)
  parser.py     — DBPF v2 container reader + save file parsing
  cli.py        — click-based CLI (info, sims, households)
  mcp_server.py — MCP server wrapping the same parser API
```

Save file parsing chain:
1. `DBPFReader` — low-level container: reads header, parses index, decompresses LZ4 resources
2. `SaveFileParser` — walks known resource type IDs to extract Sims, households, careers, traits
3. `load_save()` — convenience function, returns `SaveFile`

## Conventions

- Prefer dataclasses over pydantic models for parsed save data (simpler serialization)
- CLI uses click, not argparse
- MCP tools mirror CLI commands for consistency
- Type hints required everywhere; `from __future__ import annotations` in every module
- Line length 100, target Python 3.11+

## Save file info

Standard location: `~/Documents/Electronic Arts/The Sims 4/saves/`

Files are `.save` or `.save.ver{N}` (versioned backups). Format: DBPF v2 with LZ4-compressed resources.

## Quirks / gotchas

- **No test save files in repo** — testing requires a real save or a minimal DBPF fixture
- Resource alignment in DBPF is approximated; the offset table is not fully parsed by the scaffold
- Trait/career resources are keyed by Sim instance ID; the current parser reads the *first* resource of each type, which is incorrect for multi-Sim saves — needs filtering by `instance_id`
- `mcp>=1.0` may not exist on PyPI yet; pin to `mcp>=0.1` if MCP SDK uses different version scheme
