"""List available machine images."""

from __future__ import annotations

import typer

from ...api import service
from ..state import CommandBase
from ..ui.tables import images_table

app = typer.Typer(no_args_is_help=True, help="List available machine images.")


@app.command("list")
def list_images(
    ctx: typer.Context,
    region: str | None = typer.Option(None, "--region", "-r", help="Only this region."),
    family: str | None = typer.Option(None, "--family", help="Only this image family."),
) -> None:
    """List available images (Lambda Stack and others)."""
    cmd = CommandBase(ctx)
    images = service.filter_images(service.list_images(cmd.client), region=region, family=family)
    cmd.emit(images, images_table(service.sort_images_by_updated(images)))
