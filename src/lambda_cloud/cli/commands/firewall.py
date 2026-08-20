"""Manage firewall rulesets (regional and global)."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from ...api import service
from ...core.errors import LambdaCloudError
from ...mngr.models import FirewallRule
from ..state import CommandBase
from ..ui.console import confirm_or_exit, success
from ..ui.tables import firewall_rules_table, rulesets_table

app = typer.Typer(no_args_is_help=True, help="Manage firewall rulesets.")
rulesets_app = typer.Typer(no_args_is_help=True, help="Manage regional firewall rulesets.")
global_app = typer.Typer(no_args_is_help=True, help="Manage the global firewall ruleset.")
app.add_typer(rulesets_app, name="rulesets")
app.add_typer(global_app, name="global")

_RULES_FILE_HELP = (
    "Path to a JSON file containing a list of firewall rules, e.g. "
    '[{"protocol": "tcp", "port_range": [22, 22], "source_network": "0.0.0.0/0", '
    '"description": "SSH"}].'
)

_RULES_FILE_OPTION = dict(
    exists=True,
    file_okay=True,
    dir_okay=False,
    readable=True,
    resolve_path=True,
)


def load_rules_file(path: Path) -> list[FirewallRule]:
    """Load and validate firewall rules from a JSON file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LambdaCloudError(f"Cannot read rules file {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise LambdaCloudError(f"Rules file {path} must contain a JSON list of rules.")
    try:
        return [FirewallRule.model_validate(item) for item in raw]
    except ValidationError as exc:
        raise LambdaCloudError(f"Invalid firewall rule in {path}: {exc}") from exc


@rulesets_app.command("list")
def list_rulesets(ctx: typer.Context) -> None:
    """List your firewall rulesets."""
    cmd = CommandBase(ctx)
    rulesets = service.list_firewall_rulesets(cmd.client)
    cmd.emit(rulesets, rulesets_table(rulesets))


@rulesets_app.command("get")
def get_ruleset(
    ctx: typer.Context, ruleset_id: str = typer.Argument(..., help="Ruleset ID.")
) -> None:
    """Show a ruleset and its rules."""
    cmd = CommandBase(ctx)
    ruleset = service.get_firewall_ruleset(cmd.client, ruleset_id)
    if cmd.output.value == "table":
        cmd.emit(ruleset.rules, firewall_rules_table(ruleset.rules))
    else:
        cmd.emit(ruleset)


@rulesets_app.command("create")
def create_ruleset(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Ruleset name."),
    region: str = typer.Option(..., "--region", "-r", help="Region name."),
    rules_file: Path = typer.Option(
        ..., "--rules-file", help=_RULES_FILE_HELP, **_RULES_FILE_OPTION
    ),
) -> None:
    """Create a firewall ruleset from a JSON rules file."""
    cmd = CommandBase(ctx)
    rules = load_rules_file(rules_file)
    ruleset = service.create_firewall_ruleset(cmd.client, name, region, rules)
    if cmd.output.value == "table":
        success(f"Ruleset {ruleset.name!r} created (id: {ruleset.id}).")
    else:
        cmd.emit(ruleset)


@rulesets_app.command("update")
def update_ruleset(
    ctx: typer.Context,
    ruleset_id: str = typer.Argument(..., help="Ruleset ID."),
    name: str | None = typer.Option(None, "--name", "-n", help="New ruleset name."),
    rules_file: Path | None = typer.Option(
        None, "--rules-file", help=_RULES_FILE_HELP, **_RULES_FILE_OPTION
    ),
) -> None:
    """Update a ruleset's name and/or rules (omitted fields stay unchanged)."""
    cmd = CommandBase(ctx)
    if name is None and rules_file is None:
        raise LambdaCloudError("Nothing to update: pass --name and/or --rules-file.")
    rules = load_rules_file(rules_file) if rules_file else None
    ruleset = service.update_firewall_ruleset(cmd.client, ruleset_id, name=name, rules=rules)
    if cmd.output.value == "table":
        success(f"Ruleset {ruleset_id} updated.")
    else:
        cmd.emit(ruleset)


@rulesets_app.command("delete")
def delete_ruleset(
    ctx: typer.Context,
    ruleset_id: str = typer.Argument(..., help="Ruleset ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Delete a firewall ruleset."""
    cmd = CommandBase(ctx)
    confirm_or_exit(f"Delete firewall ruleset {ruleset_id}?", yes)
    service.delete_firewall_ruleset(cmd.client, ruleset_id)
    if cmd.output.value == "table":
        success(f"Ruleset {ruleset_id} deleted.")
    else:
        cmd.emit({"id": ruleset_id})


@global_app.command("get")
def get_global_ruleset(ctx: typer.Context) -> None:
    """Show the global firewall ruleset."""
    cmd = CommandBase(ctx)
    ruleset = service.get_global_firewall_ruleset(cmd.client)
    if cmd.output.value == "table":
        cmd.emit(ruleset.rules, firewall_rules_table(ruleset.rules))
    else:
        cmd.emit(ruleset)


@global_app.command("update")
def update_global_ruleset(
    ctx: typer.Context,
    rules_file: Path = typer.Option(
        ..., "--rules-file", help=_RULES_FILE_HELP, **_RULES_FILE_OPTION
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Replace the rules of the global firewall ruleset."""
    cmd = CommandBase(ctx)
    rules = load_rules_file(rules_file)
    confirm_or_exit(f"Replace the global firewall ruleset with {len(rules)} rule(s)?", yes)
    service.update_global_firewall_ruleset(cmd.client, rules)
    if cmd.output.value == "table":
        success("Global firewall ruleset updated.")
    else:
        cmd.emit(service.get_global_firewall_ruleset(cmd.client))
