"""Manage the local Lambda Cloud API key."""

from __future__ import annotations

import os

import typer

from ...api import LambdaCloudClient
from ...core.config import (
    API_KEY_ENV_VAR,
    delete_stored_config,
    describe_api_key_source,
    mask_api_key,
    save_api_key,
)
from ...core.errors import ConfigError, LambdaCloudError
from ..state import CommandBase
from ..ui.console import info, success, warn


def login(
    ctx: typer.Context,
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Skip the prompt by passing the key directly.",
    ),
) -> None:
    """Prompt for a key, validate it against the API, and save it."""
    CommandBase(ctx, needs_client=False)
    if api_key is None:
        api_key = typer.prompt("Lambda Cloud API key (input hidden)", hide_input=True)
    api_key = api_key.strip()
    if not api_key:
        raise LambdaCloudError("Empty API key.")

    with LambdaCloudClient(api_key) as client:
        client.get("/instances")

    path = save_api_key(api_key)
    success(f"Key is valid. Configuration written to {path}")


def logout(ctx: typer.Context) -> None:
    """Delete the stored config file, if any."""
    CommandBase(ctx, needs_client=False)
    if delete_stored_config():
        success("Stored configuration removed.")
    else:
        info("No stored configuration found.")
    if os.environ.get(API_KEY_ENV_VAR):
        warn(f"{API_KEY_ENV_VAR} is still set in your environment; unset it to fully log out.")


def whoami(ctx: typer.Context) -> None:
    """Show the credentials currently in use and verify they are valid."""
    CommandBase(ctx, needs_client=False)
    source = describe_api_key_source(ctx.obj.api_key)
    if source is None:
        raise ConfigError(
            "No API key configured. Run `lambda-cloud login` or set "
            f"{API_KEY_ENV_VAR}."
        )
    label, key = source
    info(f"Source: {label}")
    info(f"Key:    {mask_api_key(key)}")
    with LambdaCloudClient(key) as client:
        client.get("/instances")
    success("Key is valid.")
