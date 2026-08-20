"""Query account audit events."""

from __future__ import annotations

import typer

from ...api import service
from ..state import CommandBase
from ..ui.tables import audit_events_table

app = typer.Typer(no_args_is_help=True, help="Query account audit events.")


@app.command("list")
def list_audit_events(
    ctx: typer.Context,
    start: str | None = typer.Option(
        None, "--start", help="ISO 8601 timestamp, inclusive (e.g. 2025-09-01T00:00:00Z)."
    ),
    end: str | None = typer.Option(None, "--end", help="ISO 8601 timestamp, inclusive."),
    resource_type: str | None = typer.Option(
        None, "--resource-type", help="Filter by resource type, e.g. cloud.api_key."
    ),
    all_pages: bool = typer.Option(
        False, "--all", help="Follow pagination until all events are fetched."
    ),
) -> None:
    """List audit events (newest time range by default)."""
    cmd = CommandBase(ctx)
    events = service.list_audit_events(
        cmd.client,
        start=start,
        end=end,
        resource_type=resource_type,
        all_pages=all_pages,
    )
    cmd.emit(events, audit_events_table(events))
