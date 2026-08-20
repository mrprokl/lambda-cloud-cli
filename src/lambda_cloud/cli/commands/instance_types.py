"""List available instance types, prices and capacity."""

from __future__ import annotations

import typer

from ...api import service
from ..state import CommandBase
from ..ui.tables import instance_types_table

app = typer.Typer(no_args_is_help=True, help="List instance types, prices and capacity.")


@app.command("list")
def list_instance_types_cmd(ctx: typer.Context) -> None:
    """List every instance type with its specs, price and regional availability."""
    cmd = CommandBase(ctx)
    offers = service.list_instance_types(cmd.client)
    cmd.emit(offers, instance_types_table(offers))
