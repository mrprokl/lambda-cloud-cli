"""Console output helpers: rich tables for humans, JSON for scripts."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, NoReturn

import typer
from pydantic import BaseModel
from rich.console import Console, RenderableType

from ...core.errors import APIError, LambdaCloudError

console = Console()
err_console = Console(stderr=True, style="bold red")


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"


def _normalize(data: Any) -> Any:
    """Convert pydantic models and containers to plain JSON-able data."""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_normalize(item) for item in data]
    if isinstance(data, dict):
        return {key: _normalize(value) for key, value in data.items()}
    return data


def emit(
    data: Any,
    output_format: OutputFormat,
    renderable: RenderableType | None = None,
) -> None:
    """Print ``data`` as JSON, or print ``renderable`` in table mode."""
    if output_format is OutputFormat.JSON:
        console.print(
            json.dumps(_normalize(data), indent=2, ensure_ascii=False),
            highlight=False,
            soft_wrap=True,
        )
    elif renderable is not None:
        console.print(renderable)


def success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def info(message: str) -> None:
    console.print(message)


def warn(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}")


def failure(header: str, message: str) -> NoReturn:
    """Print a failed action's details and exit with a non-zero code."""
    err_console.print(f"Action failed: {header}")
    err_console.print(f"Error: {message}")
    raise typer.Exit(code=1)


def confirm_or_exit(message: str, assume_yes: bool) -> None:
    """Ask for confirmation; abort the command when declined."""
    if assume_yes:
        return
    if not typer.confirm(message):
        console.print("Aborted.")
        raise typer.Exit(code=0)


def exit_with_error(exc: Exception) -> NoReturn:
    """Render an error nicely on stderr and exit with a non-zero code."""
    if isinstance(exc, APIError):
        err_console.print(f"Error: {exc.message} [dim]({exc.code}, HTTP {exc.status_code})[/dim]")
        if exc.suggestion:
            err_console.print(f"Suggestion: {exc.suggestion}", style="yellow")
        if exc.status_code == 401:
            err_console.print(
                "Hint: check your API key with `lambda-cloud login`.",
                style="dim",
            )
    elif isinstance(exc, LambdaCloudError):
        err_console.print(f"Error: {exc}")
    else:  # unexpected bug: keep the message but stay polite
        err_console.print(f"Unexpected error: {exc}")
    raise typer.Exit(code=1)
