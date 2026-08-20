"""Manage on-demand GPU instances."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel

from ...api import service
from ...core.errors import LambdaCloudError
from ...mngr.models import TagEntry
from ..state import CommandBase
from ..ui import history
from ..ui.console import confirm_or_exit, console, success
from ..ui.tables import instance_detail_table, instances_table

app = typer.Typer(no_args_is_help=True, help="Manage on-demand GPU instances.")


def parse_tag(tag: str) -> TagEntry:
    """Parse a ``key=value`` tag option."""
    if "=" not in tag:
        raise LambdaCloudError(f"Invalid tag {tag!r}: expected format key=value.")
    key, value = tag.split("=", 1)
    if not key:
        raise LambdaCloudError(f"Invalid tag {tag!r}: key must not be empty.")
    return TagEntry(key=key, value=value)


def build_launch_payload(
    *,
    region: str,
    instance_type: str,
    ssh_key: str,
    name: str | None = None,
    hostname: str | None = None,
    filesystems: list[str] | None = None,
    image_id: str | None = None,
    image_family: str | None = None,
    user_data: str | None = None,
    tags: list[TagEntry] | None = None,
    firewall_rulesets: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble the request body for ``POST /instance-operations/launch``."""
    if image_id and image_family:
        raise LambdaCloudError("--image-id and --image-family are mutually exclusive.")

    payload: dict[str, Any] = {
        "region_name": region,
        "instance_type_name": instance_type,
        "ssh_key_names": [ssh_key],
    }
    if name is not None:
        payload["name"] = name
    if hostname is not None:
        payload["hostname"] = hostname
    if filesystems:
        payload["file_system_names"] = filesystems
    if image_id is not None:
        payload["image"] = {"id": image_id}
    elif image_family is not None:
        payload["image"] = {"family": image_family}
    if user_data is not None:
        payload["user_data"] = user_data
    if tags:
        payload["tags"] = [tag.model_dump() for tag in tags]
    if firewall_rulesets:
        payload["firewall_rulesets"] = [{"id": ruleset_id} for ruleset_id in firewall_rulesets]
    return payload


@app.command("list")
def list_instances_cmd(
    ctx: typer.Context,
    cluster_id: str | None = typer.Option(None, "--cluster-id", help="Filter by cluster ID."),
) -> None:
    """List running instances."""
    cmd = CommandBase(ctx)
    instances = service.list_instances(cmd.client, cluster_id=cluster_id)
    cmd.state.history["instances"] = [instance.id for instance in instances]
    cmd.emit(instances, instances_table(instances))


@app.command("get")
def get_instance(ctx: typer.Context, instance_id: str = typer.Argument(...)) -> None:
    """Show details of a single instance."""
    cmd = CommandBase(ctx)
    instance = service.get_instance(cmd.client, instance_id)
    cmd.state.history["instance"] = instance.id
    cmd.emit(instance, instance_detail_table(instance))


@app.command("launch")
def launch_instance(
    ctx: typer.Context,
    instance_type: str = typer.Option(
        ..., "--type", "-t", help="Instance type name (see `lambda-cloud types list`)."
    ),
    region: str = typer.Option(
        ..., "--region", "-r", help="Region name (see `lambda-cloud regions list`)."
    ),
    ssh_key: str = typer.Option(
        ...,
        "--ssh-key",
        "-s",
        help="Name of an existing SSH key (see `lambda-cloud ssh-keys list`).",
    ),
    name: str | None = typer.Option(None, "--name", help="Friendly name for the instance."),
    hostname: str | None = typer.Option(
        None, "--hostname", help="Hostname written to /etc/hostname."
    ),
    filesystems: list[str] = typer.Option(
        None, "--filesystem", "-f", help="Filesystem name to mount. Repeatable."
    ),
    image_id: str | None = typer.Option(None, "--image-id", help="ID of a specific image."),
    image_family: str | None = typer.Option(
        None, "--image-family", help="Image family (defaults to the latest Lambda Stack)."
    ),
    user_data: Path | None = typer.Option(
        None,
        "--user-data",
        help="Path to a cloud-init user-data file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    tags: list[str] = typer.Option(None, "--tag", help="Tag as key=value. Repeatable."),
    firewall_rulesets: list[str] = typer.Option(
        None, "--firewall-ruleset", help="Firewall ruleset ID (same region). Repeatable."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Launch a new on-demand instance."""
    cmd = CommandBase(ctx)
    payload = build_launch_payload(
        region=region,
        instance_type=instance_type,
        ssh_key=ssh_key,
        name=name,
        hostname=hostname,
        filesystems=filesystems,
        image_id=image_id,
        image_family=image_family,
        user_data=user_data.read_text() if user_data else None,
        tags=[parse_tag(tag) for tag in tags or []],
        firewall_rulesets=firewall_rulesets,
    )

    if cmd.output.value == "table":
        summary = (
            f"[bold]Type:[/bold] {instance_type}\n"
            f"[bold]Region:[/bold] {region}\n"
            f"[bold]SSH key:[/bold] {ssh_key}\n"
            f"[bold]Name:[/bold] {name or '-'}"
        )
        console.print(Panel(summary, title="Launch instance"))
    confirm_or_exit("Proceed with launch?", yes)

    instance_ids = service.launch_instances(cmd.client, payload)
    history.record_result("instances.launch", {"instance_ids": instance_ids})
    if cmd.output.value == "table":
        for instance_id in instance_ids:
            success(f"Launch requested for instance {instance_id}")
    else:
        cmd.emit({"instance_ids": instance_ids})


@app.command("restart")
def restart_instances_cmd(
    ctx: typer.Context,
    instance_ids: list[str] = typer.Argument(..., help="IDs of instances to restart."),
) -> None:
    """Restart one or more instances."""
    cmd = CommandBase(ctx)
    restarted = service.restart_instances(cmd.client, instance_ids)
    cmd.emit(restarted, instances_table(restarted))


@app.command("terminate")
def terminate_instances_cmd(
    ctx: typer.Context,
    instance_ids: list[str] = typer.Argument(..., help="IDs of instances to terminate."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Terminate one or more instances. This cannot be undone."""
    cmd = CommandBase(ctx)
    confirm_or_exit(
        f"Terminate {len(instance_ids)} instance(s): {', '.join(instance_ids)}?",
        yes,
    )
    terminated = service.terminate_instances(cmd.client, instance_ids)
    if cmd.output.value == "table":
        for instance in terminated:
            success(f"Terminating instance {instance.id}")
    else:
        cmd.emit({"terminated_instances": terminated})


@app.command("rename")
def rename_instance(
    ctx: typer.Context,
    instance_id: str = typer.Argument(...),
    name: str = typer.Option(..., "--name", help="New name (empty string to clear)."),
) -> None:
    """Rename an instance."""
    cmd = CommandBase(ctx)
    service.rename_instance(cmd.client, instance_id, name)
    if cmd.output.value == "table":
        success(f"Instance {instance_id} renamed to {name!r}.")
    else:
        cmd.emit({"id": instance_id, "name": name})
