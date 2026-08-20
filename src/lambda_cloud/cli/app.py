"""Root Typer application assembling every command group."""

from __future__ import annotations

import httpx
import typer

from .. import __version__
from ..core.errors import LambdaCloudError
from .commands import (
    audit,
    auth,
    completion,
    config_cmd,
    filesystems,
    firewall,
    images,
    instance_types,
    instances,
    regions,
    ssh_keys,
)
from .state import State
from .ui.console import OutputFormat, console, err_console, exit_with_error


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"lambda-cloud {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="lambda-cloud",
    help=(
        "Unofficial community CLI for the Lambda Cloud API "
        "(https://cloud.lambda.ai)."
        "\n\nManage on-demand GPU instances, SSH keys, filesystems, images, "
        "regions and firewall rulesets."
    ),
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback()
def callback(
    ctx: typer.Context,
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="API key. Overrides LAMBDA_API_KEY and the stored config.",
        show_envvar=False,
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--output",
        "-o",
        help="Output format.",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output."),
    show_completion: str | None = typer.Option(
        None,
        "--show-completion",
        help="Print shell completion instructions (bash, zsh, fish, powershell).",
        is_eager=True,
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Store global options on the context; commands pick them up lazily."""
    completion.handle_completion(show_completion)
    state = State(api_key=api_key, output=output_format, verbose=verbose)
    ctx.obj = state
    ctx.call_on_close(state.close)


app.add_typer(instances.app, name="instances")
app.add_typer(instance_types.app, name="types")
app.add_typer(ssh_keys.app, name="ssh-keys")
app.add_typer(filesystems.app, name="filesystems")
app.add_typer(images.app, name="images")
app.add_typer(regions.app, name="regions")
app.add_typer(firewall.app, name="firewall")
app.add_typer(audit.app, name="audit")
app.add_typer(config_cmd.app, name="config")

app.command("login", help="Store and validate your Lambda Cloud API key.")(auth.login)
app.command("logout", help="Remove the stored API key.")(auth.logout)
app.command("whoami", help="Show which credentials are in use and validate them.")(auth.whoami)


def main() -> None:
    """Console entry point: convert errors into clean exits."""
    try:
        app()
    except LambdaCloudError as exc:
        exit_with_error(exc)
    except httpx.HTTPError as exc:
        err_console.print(f"Network error: {exc}", style="bold red")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
