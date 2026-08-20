"""Rich table renderers for every API resource."""

from __future__ import annotations

from datetime import datetime

from rich.table import Table

from ...mngr.models import (
    AuditEvent,
    Filesystem,
    FirewallRule,
    FirewallRuleset,
    Image,
    Instance,
    InstanceStatus,
    InstanceTypeOffer,
    Region,
    SSHKey,
)

_STATUS_STYLES = {
    InstanceStatus.ACTIVE: "green",
    InstanceStatus.BOOTING: "cyan",
    InstanceStatus.UNHEALTHY: "yellow",
    InstanceStatus.TERMINATING: "magenta",
    InstanceStatus.TERMINATED: "red",
    InstanceStatus.PREEMPTED: "red",
}


def _styled_status(status: InstanceStatus) -> str:
    style = _STATUS_STYLES.get(status, "default")
    return f"[{style}]{status.value}[/{style}]"


def _short(value: str | None, length: int = 40) -> str:
    if not value:
        return "-"
    return value if len(value) <= length else value[: length - 1] + "…"


def _fmt_dt(value: datetime | str | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value[:19].replace("T", " ")
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_bytes(value: int | None) -> str:
    if value is None:
        return "-"
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return "-"


def instance_detail_table(instance: Instance) -> Table:
    """Key/value detail view for a single instance."""
    table = Table(title=f"Instance {instance.id}", show_header=False)
    table.add_column("FIELD", style="bold cyan")
    table.add_column("VALUE")

    rows: list[tuple[str, str]] = [
        ("ID", instance.id),
        ("Name", instance.name or "-"),
        ("Status", _styled_status(instance.status)),
        ("Type", instance.instance_type.name if instance.instance_type else "-"),
        ("Region", instance.region.name if instance.region else "-"),
        ("IP", instance.ip or "-"),
        ("Private IP", instance.private_ip or "-"),
        ("Hostname", instance.hostname or "-"),
        ("SSH keys", ", ".join(instance.ssh_key_names) or "-"),
        ("Filesystems", ", ".join(instance.file_system_names) or "-"),
        ("Jupyter", instance.jupyter_url or "-"),
        (
            "Tags",
            ", ".join(f"{tag.key}={tag.value}" for tag in instance.tags or []) or "-",
        ),
    ]
    if instance.instance_type:
        rows.append(
            ("Price/hour", f"${instance.instance_type.price_per_hour:.2f}"),
        )
    for field, value in rows:
        table.add_row(field, value)
    return table


def instances_table(instances: list[Instance]) -> Table:
    table = Table(title="Instances")
    table.add_column("ID", style="cyan")
    table.add_column("NAME")
    table.add_column("TYPE")
    table.add_column("REGION")
    table.add_column("STATUS")
    table.add_column("IP")
    table.add_column("PRICE/H", justify="right")
    for instance in instances:
        price = (
            f"${instance.instance_type.price_per_hour:.2f}" if instance.instance_type else "-"
        )
        table.add_row(
            instance.id,
            instance.name or "-",
            instance.instance_type.name if instance.instance_type else "-",
            instance.region.name if instance.region else "-",
            _styled_status(instance.status),
            instance.ip or "-",
            price,
        )
    return table


def instance_types_table(offers: list[InstanceTypeOffer]) -> Table:
    table = Table(title="Instance types")
    table.add_column("NAME", style="cyan")
    table.add_column("DESCRIPTION")
    table.add_column("GPUS", justify="right")
    table.add_column("VCPUS", justify="right")
    table.add_column("MEM (GiB)", justify="right")
    table.add_column("STORAGE (GiB)", justify="right")
    table.add_column("PRICE/H", justify="right")
    table.add_column("REGIONS AVAILABLE")
    for offer in offers:
        instance_type = offer.instance_type
        regions = ", ".join(r.name for r in offer.regions_with_capacity_available) or "-"
        table.add_row(
            instance_type.name,
            _short(instance_type.description, 32),
            str(instance_type.specs.gpus),
            str(instance_type.specs.vcpus),
            str(instance_type.specs.memory_gib),
            str(instance_type.specs.storage_gib),
            f"${instance_type.price_per_hour:.2f}",
            regions,
        )
    return table


def ssh_keys_table(keys: list[SSHKey]) -> Table:
    table = Table(title="SSH keys")
    table.add_column("ID", style="cyan")
    table.add_column("NAME")
    table.add_column("PUBLIC KEY")
    for key in keys:
        table.add_row(key.id, key.name, _short(key.public_key, 60))
    return table


def filesystems_table(filesystems: list[Filesystem]) -> Table:
    table = Table(title="Filesystems")
    table.add_column("ID", style="cyan")
    table.add_column("NAME")
    table.add_column("REGION")
    table.add_column("MOUNT POINT")
    table.add_column("USED", justify="right")
    table.add_column("IN USE")
    table.add_column("CREATED")
    for filesystem in filesystems:
        table.add_row(
            filesystem.id,
            filesystem.name,
            filesystem.region.name if filesystem.region else "-",
            filesystem.mount_point,
            _fmt_bytes(filesystem.bytes_used),
            "yes" if filesystem.is_in_use else "no",
            _fmt_dt(filesystem.created),
        )
    return table


def images_table(images: list[Image]) -> Table:
    table = Table(title="Images")
    table.add_column("ID", style="cyan")
    table.add_column("NAME")
    table.add_column("FAMILY")
    table.add_column("VERSION")
    table.add_column("ARCH")
    table.add_column("REGION")
    table.add_column("UPDATED")
    for image in images:
        table.add_row(
            image.id,
            _short(image.name, 40),
            image.family,
            image.version,
            image.architecture,
            image.region.name if image.region else "-",
            _fmt_dt(image.updated_time),
        )
    return table


def regions_table(regions: list[Region]) -> Table:
    table = Table(title="Regions")
    table.add_column("NAME", style="cyan")
    table.add_column("DESCRIPTION")
    for region in regions:
        table.add_row(region.name, region.description)
    return table


def firewall_rules_table(rules: list[FirewallRule]) -> Table:
    table = Table()
    table.add_column("PROTOCOL", style="cyan")
    table.add_column("PORTS")
    table.add_column("SOURCE")
    table.add_column("DESCRIPTION")
    for rule in rules:
        table.add_row(
            rule.protocol.value, rule.ports_display, rule.source_network, rule.description
        )
    return table


def rulesets_table(rulesets: list[FirewallRuleset]) -> Table:
    table = Table(title="Firewall rulesets")
    table.add_column("ID", style="cyan")
    table.add_column("NAME")
    table.add_column("REGION")
    table.add_column("RULES", justify="right")
    table.add_column("INSTANCES", justify="right")
    table.add_column("CREATED")
    for ruleset in rulesets:
        table.add_row(
            ruleset.id,
            ruleset.name,
            ruleset.region.name if ruleset.region else "-",
            str(len(ruleset.rules)),
            str(len(ruleset.instance_ids)),
            _fmt_dt(ruleset.created),
        )
    return table


def audit_events_table(events: list[AuditEvent]) -> Table:
    table = Table(title="Audit events")
    table.add_column("TIME")
    table.add_column("ACTION", style="cyan")
    table.add_column("RESOURCE")
    table.add_column("ACTOR")
    table.add_column("SURFACE")
    table.add_column("RESULT")
    for event in events:
        result = event.result.status if event.result else "-"
        styled = f"[green]{result}[/green]" if result == "success" else result
        table.add_row(
            _fmt_dt(event.event_time),
            event.action,
            event.resource_name,
            event.actor_email or event.actor_display_name or "-",
            event.surface or "-",
            styled,
        )
    return table
