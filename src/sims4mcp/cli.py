from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from sims4mcp.parser import load_save, find_saves
from sims4mcp.models import SaveFile


def _resolve_save(path: Optional[str], save_dir: Optional[str]) -> SaveFile:
    if path:
        return load_save(Path(path))
    saves = find_saves(Path(save_dir) if save_dir else None)
    if not saves:
        raise click.UsageError(
            "No save files found. Provide a SAVE path or use --dir."
        )
    return load_save(saves[-1])


@click.group()
def cli() -> None:
    """sims4mcp — inspect The Sims 4 save files from the command line."""


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False), required=False)
@click.option(
    "-d",
    "--dir",
    "save_dir",
    type=click.Path(exists=True, file_okay=False),
    help="Search for save files in DIR instead of the default Sims 4 directory.",
)
def info(path: Optional[str], save_dir: Optional[str]) -> None:
    """Show a high-level overview of a save file."""
    sf = _resolve_save(path, save_dir)
    click.echo(f"Save:         {sf.name}")
    click.echo(f"File:         {sf.path}")
    click.echo(f"Households:   {len(sf.households)}")
    click.echo(f"Total Sims:   {len(sf.sims)}")

    for hh in sf.households:
        click.echo(f"\n  {click.style(hh.name, bold=True)}")
        funds = f" (\u00a7{hh.funds.simoleons:,.0f})" if hh.funds else ""
        click.echo(f"  Funds:{funds}")
        for sim in hh.sims:
            age = f" ({sim.age.value})" if sim.age else ""
            click.echo(f"    {sim.first_name} {sim.last_name}{age}")


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False), required=False)
@click.option("--sim-id", type=int, help="Display only the Sim with this ID.")
@click.option(
    "-d",
    "--dir",
    "save_dir",
    type=click.Path(exists=True, file_okay=False),
    help="Search for save files in DIR.",
)
def sims(path: Optional[str], sim_id: Optional[int], save_dir: Optional[str]) -> None:
    """List all Sims in a save, or a single Sim with --sim-id."""
    sf = _resolve_save(path, save_dir)

    found = False
    for hh in sf.households:
        for sim in hh.sims:
            if sim_id is not None and sim.id != sim_id:
                continue
            found = True
            click.echo(f"[{sim.id}] {click.style(f'{sim.first_name} {sim.last_name}', bold=True)}")
            if sim.age:
                click.echo(f"  Age:     {sim.age.value}")
            if sim.gender:
                click.echo(f"  Gender:  {sim.gender.value}")
            if sim.traits:
                click.echo(f"  Traits:  {', '.join(sim.traits)}")
            if sim.career:
                click.echo(f"  Career:  {sim.career.name} (Lv.{sim.career.level})")
            if sim.skills:
                click.echo(f"  Skills:  {', '.join(f'{s.name}={s.level}' for s in sim.skills)}")
            if sim.moodlets:
                click.echo(f"  Moodlets: {', '.join(m.name for m in sim.moodlets)}")
            if sim.money:
                click.echo(f"  Money:   \u00a7{sim.money:,.0f}")
            if sim.is_death:
                click.echo(f"  Status:  Deceased ({sim.death_type or 'unknown cause'})")
            click.echo(f"  Household: {hh.name}")
            click.echo("")

    if not found:
        msg = f"Sim with ID {sim_id} not found." if sim_id else ""
        click.echo(msg)


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False), required=False)
@click.option(
    "-d",
    "--dir",
    "save_dir",
    type=click.Path(exists=True, file_okay=False),
    help="Search for save files in DIR.",
)
def households(path: Optional[str], save_dir: Optional[str]) -> None:
    """List all households in a save file."""
    sf = _resolve_save(path, save_dir)

    for hh in sf.households:
        sims_list = ", ".join(f"{s.first_name} {s.last_name}" for s in hh.sims)
        funds = f" \u00a7{hh.funds.simoleons:,.0f}" if hh.funds else ""
        click.echo(f"  {click.style(hh.name, bold=True)}{funds}")
        click.echo(f"    Sims: {sims_list}")


if __name__ == "__main__":
    cli()
