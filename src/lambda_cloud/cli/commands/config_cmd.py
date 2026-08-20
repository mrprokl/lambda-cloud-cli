"""Inspect lambda-cloud CLI configuration."""

from __future__ import annotations

import typer
from rich.table import Table

from ...api.client import BASE_URL_ENV_VAR, DEFAULT_BASE_URL
from ...core.config import (
    API_KEY_ENV_VAR,
    config_path,
    describe_api_key_source,
    mask_api_key,
)
from ..state import CommandBase
from ..ui import history

app = typer.Typer(no_args_is_help=True, help="Inspect lambda-cloud configuration.")


@app.command("show")
def show(ctx: typer.Context) -> None:
    """Show where the CLI reads its configuration from."""
    import os

    cmd = CommandBase(ctx, needs_client=False)
    source = describe_api_key_source(cmd.state.api_key)

    table = Table(title="lambda-cloud configuration", show_header=False)
    table.add_column("FIELD", style="bold cyan")
    table.add_column("VALUE")
    table.add_row("Config file", str(config_path()))
    table.add_row("API base URL", os.environ.get(BASE_URL_ENV_VAR, DEFAULT_BASE_URL))
    if source:
        label, key = source
        table.add_row("Key source", label)
        table.add_row("API key", mask_api_key(key))
    else:
        table.add_row("Key source", f"not configured (login or set {API_KEY_ENV_VAR})")

    last_launch = history.last_result("instances.launch")
    if last_launch:
        table.add_row("Last launch", str(last_launch["data"].get("instance_ids", "-")))

    cmd.emit({"config_file": str(config_path())}, table)
