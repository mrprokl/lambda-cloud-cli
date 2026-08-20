"""Manage shared filesystems."""

from __future__ import annotations

import typer

from ...api import service
from ..state import CommandBase
from ..ui.console import confirm_or_exit, success
from ..ui.tables import filesystems_table

app = typer.Typer(no_args_is_help=True, help="Manage shared filesystems.")


@app.command("list")
def list_filesystems(ctx: typer.Context) -> None:
    """List your filesystems."""
    cmd = CommandBase(ctx)
    filesystems = service.list_filesystems(cmd.client)
    cmd.emit(filesystems, filesystems_table(filesystems))


@app.command("create")
def create_filesystem(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Filesystem name."),
    region: str = typer.Option(
        ..., "--region", "-r", help="Region (see `lambda-cloud regions list`)."
    ),
) -> None:
    """Create a new filesystem."""
    cmd = CommandBase(ctx)
    filesystem = service.create_filesystem(cmd.client, name=name, region=region)
    if cmd.output.value == "table":
        success(f"Filesystem {filesystem.name!r} created (id: {filesystem.id}).")
    else:
        cmd.emit(filesystem)


@app.command("delete")
def delete_filesystem(
    ctx: typer.Context,
    filesystem_id: str = typer.Argument(..., help="ID of the filesystem to delete."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Delete a filesystem. It must not be mounted on any running instance."""
    cmd = CommandBase(ctx)
    confirm_or_exit(f"Delete filesystem {filesystem_id}?", yes)
    service.delete_filesystem(cmd.client, filesystem_id)
    if cmd.output.value == "table":
        success(f"Filesystem {filesystem_id} deleted.")
    else:
        cmd.emit({"id": filesystem_id})
