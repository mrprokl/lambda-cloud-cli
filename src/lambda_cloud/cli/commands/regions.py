"""List available regions."""

from __future__ import annotations

import typer

from ...api import service
from ..state import CommandBase
from ..ui.tables import regions_table

app = typer.Typer(no_args_is_help=True, help="List available regions.")


@app.command("list")
def list_regions(ctx: typer.Context) -> None:
    """List every region where instances can be launched."""
    cmd = CommandBase(ctx)
    regions = service.list_regions(cmd.client)
    cmd.emit(regions, regions_table(regions))
