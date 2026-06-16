"""MCP server — exposes Sims 4 save data as AI-accessible resources/tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from sims4mcp.parser import load_save, find_saves

server = Server("sims4mcp")
_current_save = None


def _get_save() -> Any:
    global _current_save
    if _current_save is None:
        saves = find_saves()
        if not saves:
            raise RuntimeError("No save files found")
        _current_save = load_save(saves[-1])
    return _current_save


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_households",
            description="List all households in the current save",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list_sims",
            description="List all Sims (optionally filter by household)",
            inputSchema={
                "type": "object",
                "properties": {
                    "household_name": {
                        "type": "string",
                        "description": "Optional household name to filter by",
                    }
                },
            },
        ),
        types.Tool(
            name="get_sim",
            description="Get detailed info about a specific Sim",
            inputSchema={
                "type": "object",
                "properties": {
                    "sim_id": {
                        "type": "integer",
                        "description": "The Sim's unique ID",
                    },
                    "sim_name": {
                        "type": "string",
                        "description": "The Sim's first or full name",
                    },
                },
            },
        ),
        types.Tool(
            name="load_save",
            description="Load a different save file by path or pick the latest",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional path to a .save file",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    global _current_save

    if name == "load_save":
        p = arguments.get("path")
        if p:
            _current_save = load_save(Path(p))
        else:
            saves = find_saves()
            if not saves:
                return [types.TextContent(type="text", text="No save files found")]
            _current_save = load_save(saves[-1])
        return [types.TextContent(type="text", text=f"Loaded: {_current_save.name}")]

    sf = _get_save()

    if name == "list_households":
        lines = []
        for hh in sf.households:
            sims_list = ", ".join(f"{s.first_name} {s.last_name}" for s in hh.sims)
            funds = f" \u00a7{hh.funds.simoleons:,.0f}" if hh.funds else ""
            lines.append(f"  {hh.name}{funds} — {sims_list}")
        return [types.TextContent(type="text", text="\n".join(lines) or "(none)")]

    if name == "list_sims":
        filter_hh = arguments.get("household_name", "").strip().lower()
        lines = []
        for hh in sf.households:
            if filter_hh and filter_hh not in hh.name.lower():
                continue
            for sim in hh.sims:
                age = f" ({sim.age.value})" if sim.age else ""
                lines.append(
                    f"  [{sim.id}] {sim.first_name} {sim.last_name}{age}"
                    f" — {hh.name}"
                )
        return [types.TextContent(type="text", text="\n".join(lines) or "(none)")]

    if name == "get_sim":
        sim_id = arguments.get("sim_id")
        sim_name = arguments.get("sim_name", "").strip().lower()
        candidates = []
        for sim in sf.sims:
            if sim_id is not None and sim.id == sim_id:
                candidates.append(sim)
            elif sim_name and (sim_name in sim.first_name.lower() or
                               sim_name in sim.last_name.lower() or
                               sim_name == f"{sim.first_name} {sim.last_name}".lower()):
                candidates.append(sim)

        if not candidates:
            return [types.TextContent(type="text", text="Sim not found")]
        lines = []
        for sim in candidates:
            lines.append(f"[{sim.id}] {sim.first_name} {sim.last_name}")
            if sim.age:
                lines.append(f"  Age: {sim.age.value}")
            if sim.gender:
                lines.append(f"  Gender: {sim.gender.value}")
            if sim.traits:
                lines.append(f"  Traits: {', '.join(sim.traits)}")
            if sim.career:
                lines.append(f"  Career: {sim.career.name} (Lv.{sim.career.level})")
            if sim.moodlets:
                lines.append(f"  Moodlets: {', '.join(m.name for m in sim.moodlets)}")
            if sim.skills:
                lines.append(f"  Skills: {', '.join(f'{s.name}={s.level}' for s in sim.skills)}")
            if sim.money:
                lines.append(f"  Money: \u00a7{sim.money:,.0f}")
            if sim.relationships:
                lines.append("  Relationships:")
                for r in sim.relationships:
                    lines.append(f"    {r.sim_name}: friend={r.friendship:.0%} romance={r.romance:.0%}")
            lines.append("")
        return [types.TextContent(type="text", text="\n".join(lines))]

    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sims4mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
