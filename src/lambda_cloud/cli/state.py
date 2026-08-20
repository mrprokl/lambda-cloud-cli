"""Runtime state shared by all commands (built once per invocation)."""

from __future__ import annotations

from typing import Any, NoReturn

import typer
from rich.console import RenderableType

from ..api import LambdaCloudClient
from ..core.config import resolve_api_key
from .ui.console import OutputFormat, emit, failure


class State:
    """Holds global CLI options and lazily builds the API client."""

    def __init__(self, api_key: str | None, output: OutputFormat, verbose: bool) -> None:
        self.api_key = api_key
        self.output = output
        self.verbose = verbose
        self.history: dict[str, Any] = {}
        self._client: LambdaCloudClient | None = None

    @property
    def client(self) -> LambdaCloudClient:
        """API client, created on first use (so --help works without a key)."""
        if self._client is None:
            self._client = LambdaCloudClient(resolve_api_key(self.api_key))
        return self._client

    def close(self) -> None:
        """Release any resource allocated lazily (HTTP connections)."""
        if self._client is not None:
            self._client.close()
            self._client = None


class CommandBase:
    """Per-command helper wrapping the global :class:`State`.

    Attributes:
        state: The global state built in the root callback.
        command: Name of the invoked command.
        output: The resolved output format.
    """

    def __init__(self, ctx: typer.Context, *, needs_client: bool = True) -> None:
        state: State = ctx.obj
        if needs_client:
            _ = state.client  # resolve early → clear failure on missing key
        self.state = state
        self.command = ctx.info_name or ""
        self.output = state.output

    @property
    def client(self) -> LambdaCloudClient:
        return self.state.client

    def emit(self, data: Any, renderable: RenderableType | None = None) -> None:
        """Print ``data`` according to the configured output format."""
        emit(data, self.output, renderable)

    def failure(self, action: str, message: str) -> NoReturn:
        """Report a failed action and exit."""
        failure(action, message)
