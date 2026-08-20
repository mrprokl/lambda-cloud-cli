"""Manage SSH keys."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from ...api import service
from ...core.config import write_secret_file
from ...core.errors import LambdaCloudError
from ...mngr.models import GeneratedSSHKey
from ..state import CommandBase
from ..ui import history
from ..ui.console import confirm_or_exit, console, success, warn
from ..ui.tables import ssh_keys_table

app = typer.Typer(no_args_is_help=True, help="Manage SSH keys.")


@app.command("list")
def list_ssh_keys(ctx: typer.Context) -> None:
    """List your SSH keys."""
    cmd = CommandBase(ctx)
    keys = service.list_ssh_keys(cmd.client)
    cmd.state.history["ssh_key_ids"] = [key.id for key in keys]
    cmd.emit(keys, ssh_keys_table(keys))


@app.command("add")
def add_ssh_key(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Name for the key."),
    public_key: str | None = typer.Option(
        None, "--public-key", help="Public key material (ssh-ed25519 AAAA…)."
    ),
    key_file: Path | None = typer.Option(
        None,
        "--file",
        help="Path to a public key file, e.g. ~/.ssh/id_ed25519.pub.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    save_to: Path | None = typer.Option(
        None,
        "--save-to",
        help="Write the generated private key to this file (mode 0600).",
    ),
) -> None:
    """Add an SSH key; generates a new key pair when no public key is given.

    When a key pair is generated, the private key is returned once and is
    NOT stored by Lambda: save it immediately.
    """
    cmd = CommandBase(ctx)
    if public_key and key_file:
        raise LambdaCloudError("--public-key and --file are mutually exclusive.")

    key_material = public_key or (
        key_file.read_text(encoding="utf-8").strip() if key_file else None
    )
    key = service.add_ssh_key(cmd.client, name, public_key=key_material)
    history.record_result("ssh_keys.add", {"id": key.id, "name": key.name})

    if isinstance(key, GeneratedSSHKey):
        if cmd.output.value == "json":
            cmd.emit(key)
            return
        if save_to is not None:
            write_secret_file(save_to, key.private_key + "\n")
            os.chmod(save_to, 0o600)
            success(f"Key pair generated. Private key saved to {save_to} (mode 0600).")
        else:
            warn("Lambda does NOT store the private key. Save it now:")
            console.print(f"\n{key.private_key}\n", style="bold")
    elif cmd.output.value == "table":
        success(f"SSH key {key.name!r} added (id: {key.id}).")
    else:
        cmd.emit(key)


@app.command("delete")
def delete_ssh_key(
    ctx: typer.Context,
    key_id: str = typer.Argument(..., help="ID of the SSH key to delete."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Delete an SSH key."""
    cmd = CommandBase(ctx)
    confirm_or_exit(f"Delete SSH key {key_id}?", yes)
    service.delete_ssh_key(cmd.client, key_id)
    if cmd.output.value == "table":
        success(f"SSH key {key_id} deleted.")
    else:
        cmd.emit({"id": key_id})
