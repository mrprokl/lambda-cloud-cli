"""Shell completion support."""

from __future__ import annotations

import typer

from ...core.errors import LambdaCloudError
from ..ui.console import console

SUPPORTED_SHELLS = ("bash", "zsh", "fish", "powershell")

_SNIPPETS = {
    "bash": 'eval "$(_LAMBDA_CLOUD_COMPLETE=bash_source lambda-cloud)"',
    "zsh": 'eval "$(_LAMBDA_CLOUD_COMPLETE=zsh_source lambda-cloud)"',
    "fish": "_LAMBDA_CLOUD_COMPLETE=fish_source lambda-cloud | source",
    "powershell": (
        "$env:_LAMBDA_CLOUD_COMPLETE='powershell_source'; "
        "lambda-cloud | Out-String | Invoke-Expression; "
        "Remove-Item Env:_LAMBDA_CLOUD_COMPLETE"
    ),
}


def handle_completion(shell: str | None) -> None:
    """Print activation instructions for shell completion, then exit."""
    if shell is None:
        return
    normalized = shell.lower()
    if normalized not in _SNIPPETS:
        raise LambdaCloudError(
            f"Unsupported shell {shell!r}. Choose from: {', '.join(SUPPORTED_SHELLS)}."
        )
    console.print(
        f"Run the following to enable completion for [bold]{normalized}[/bold]:\n\n"
        f"  {_SNIPPETS[normalized]}\n"
    )
    raise typer.Exit()
