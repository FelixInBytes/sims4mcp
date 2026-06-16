# sims4mcp

CLI and MCP adapter for inspecting The Sims 4 save files.  
Parse `.save` files to extract Sims, households, traits, careers, and more.

## Quick start

```sh
pip install -e .
```

List info from your latest save (auto-detected from `~/Documents/Electronic Arts/The Sims 4/saves/`):

```sh
sims4mcp info
```

Or target a specific file:

```sh
sims4mcp info ~/Documents/Electronic\ Arts/The\ Sims\ 4/saves/slot_00000002.save
sims4mcp sims ~/Documents/Electronic\ Arts/The\ Sims\ 4/saves/slot_00000002.save
sims4mcp sims --sim-id 123456 path/to/save.save
sims4mcp households path/to/save.save
```

## MCP server

```sh
mcp run src/sims4mcp/mcp_server.py
```

Exposes tools: `list_households`, `list_sims`, `get_sim`, `load_save`.

## Tests

```sh
pytest -v   # 28 tests, synthetic fixtures (no real save needed)
```

## Caveats

- **POC quality** — the binary parser uses reverse-engineered type IDs and approximate field offsets. Real save files may need tuning.
- **Single-Sim assumption** — trait/career resources are keyed by instance ID; the parser currently reads the first resource of each type. Multi-Sim saves need per-instance filtering.
- **Read-only** — no write support. You can inspect but not modify saves.
- **Format shifts** — game updates occasionally change the binary layout.

## Stack

Python 3.11+, click (CLI), lz4 (decompression), mcp (MCP SDK), pydantic (models).
