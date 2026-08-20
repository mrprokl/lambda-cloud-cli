"""High-level API operations shared by commands and tests.

Every function takes a :class:`LambdaCloudClient` and returns validated
pydantic models, keeping commands free of HTTP details.
"""

from __future__ import annotations

from datetime import datetime

from ..core.errors import LambdaCloudError
from ..mngr.models import (
    AuditEvent,
    Filesystem,
    FirewallRule,
    FirewallRuleset,
    GeneratedSSHKey,
    GlobalFirewallRuleset,
    Image,
    Instance,
    InstanceTypeOffer,
    NetworkProtocol,
    Region,
    SSHKey,
    TagEntry,
)
from .client import LambdaCloudClient


def validate_tags(tags: list[TagEntry]) -> list[dict[str, str]]:
    """Serialize tags for the launch payload."""
    return [tag.model_dump() for tag in tags]


def validate_firewall_rules(rules: list[FirewallRule]) -> None:
    """Enforce the API's port_range constraints before submitting rules."""
    for rule in rules:
        if rule.protocol is NetworkProtocol.ICMP and rule.port_range is not None:
            raise LambdaCloudError(
                "Firewall rule with protocol 'icmp' must not define port_range."
            )
        if rule.protocol is not NetworkProtocol.ICMP and rule.port_range is None:
            raise LambdaCloudError(
                f"Firewall rule with protocol '{rule.protocol.value}' requires "
                "port_range [min, max]."
            )


def serialize_firewall_rules(rules: list[FirewallRule]) -> list[dict]:
    """Serialize rules, dropping an empty port_range for icmp."""
    payload = []
    for rule in rules:
        item = rule.model_dump(mode="json")
        if item.get("port_range") is None:
            item.pop("port_range", None)
        payload.append(item)
    return payload


def filter_images(
    images: list[Image],
    region: str | None = None,
    family: str | None = None,
) -> list[Image]:
    """Apply client-side filters to an image list."""
    if region:
        images = [img for img in images if img.region and img.region.name == region]
    if family:
        images = [img for img in images if img.family == family]
    return images


def sort_images_by_updated(images: list[Image]) -> list[Image]:
    """Sort images by last update, oldest first."""
    return sorted(images, key=lambda img: img.updated_time or img.created_time or datetime.min)


def parse_instance_types(data: dict[str, dict]) -> list[InstanceTypeOffer]:
    """Parse the dict response of ``GET /instance-types``."""
    offers = [InstanceTypeOffer.model_validate(value) for value in data.values()]
    return sorted(offers, key=lambda offer: offer.instance_type.price_cents_per_hour)


def list_instance_types(client: LambdaCloudClient) -> list[InstanceTypeOffer]:
    """Fetch and sort all instance type offers by hourly price."""
    return parse_instance_types(client.get("/instance-types"))


# ---------------------------------------------------------------- thin wrappers


def list_instances(
    client: LambdaCloudClient, cluster_id: str | None = None
) -> list[Instance]:
    params = {"cluster_id": cluster_id} if cluster_id else None
    data = client.get("/instances", params=params)
    return [Instance.model_validate(item) for item in data]


def get_instance(client: LambdaCloudClient, instance_id: str) -> Instance:
    return Instance.model_validate(client.get(f"/instances/{instance_id}"))


def launch_instances(client: LambdaCloudClient, payload: dict) -> list[str]:
    data = client.post("/instance-operations/launch", json=payload)
    return data["instance_ids"]


def restart_instances(client: LambdaCloudClient, instance_ids: list[str]) -> list[Instance]:
    data = client.post("/instance-operations/restart", json={"instance_ids": instance_ids})
    return [Instance.model_validate(item) for item in data["restarted_instances"]]


def terminate_instances(client: LambdaCloudClient, instance_ids: list[str]) -> list[Instance]:
    data = client.post(
        "/instance-operations/terminate", json={"instance_ids": instance_ids}
    )
    return [Instance.model_validate(item) for item in data["terminated_instances"]]


def rename_instance(client: LambdaCloudClient, instance_id: str, name: str) -> None:
    client.post(f"/instances/{instance_id}", json={"name": name})


def list_ssh_keys(client: LambdaCloudClient) -> list[SSHKey]:
    data = client.get("/ssh-keys")
    return [SSHKey.model_validate(item) for item in data]


def add_ssh_key(
    client: LambdaCloudClient, name: str, public_key: str | None = None
) -> SSHKey | GeneratedSSHKey:
    payload: dict[str, str] = {"name": name}
    if public_key:
        payload["public_key"] = public_key
    data = client.post("/ssh-keys", json=payload)
    if "private_key" in data:
        return GeneratedSSHKey.model_validate(data)
    return SSHKey.model_validate(data)


def delete_ssh_key(client: LambdaCloudClient, key_id: str) -> None:
    client.delete(f"/ssh-keys/{key_id}")


def list_filesystems(client: LambdaCloudClient) -> list[Filesystem]:
    data = client.get("/file-systems")
    return [Filesystem.model_validate(item) for item in data]


def create_filesystem(client: LambdaCloudClient, name: str, region: str) -> Filesystem:
    data = client.post("/filesystems", json={"name": name, "region": region})
    return Filesystem.model_validate(data)


def delete_filesystem(client: LambdaCloudClient, filesystem_id: str) -> None:
    client.delete(f"/filesystems/{filesystem_id}")


def list_images(client: LambdaCloudClient) -> list[Image]:
    data = client.get("/images")
    return [Image.model_validate(item) for item in data]


def list_regions(client: LambdaCloudClient) -> list[Region]:
    data = client.get("/regions")
    return [Region.model_validate(item) for item in data]


def list_firewall_rulesets(client: LambdaCloudClient) -> list[FirewallRuleset]:
    data = client.get("/firewall-rulesets")
    return [FirewallRuleset.model_validate(item) for item in data]


def get_firewall_ruleset(client: LambdaCloudClient, ruleset_id: str) -> FirewallRuleset:
    return FirewallRuleset.model_validate(client.get(f"/firewall-rulesets/{ruleset_id}"))


def create_firewall_ruleset(
    client: LambdaCloudClient, name: str, region: str, rules: list[FirewallRule]
) -> FirewallRuleset:
    validate_firewall_rules(rules)
    data = client.post(
        "/firewall-rulesets",
        json={"name": name, "region": region, "rules": serialize_firewall_rules(rules)},
    )
    return FirewallRuleset.model_validate(data)


def update_firewall_ruleset(
    client: LambdaCloudClient,
    ruleset_id: str,
    name: str | None = None,
    rules: list[FirewallRule] | None = None,
) -> FirewallRuleset:
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if rules is not None:
        validate_firewall_rules(rules)
        payload["rules"] = serialize_firewall_rules(rules)
    data = client.patch(f"/firewall-rulesets/{ruleset_id}", json=payload)
    return FirewallRuleset.model_validate(data)


def delete_firewall_ruleset(client: LambdaCloudClient, ruleset_id: str) -> None:
    client.delete(f"/firewall-rulesets/{ruleset_id}")


def get_global_firewall_ruleset(client: LambdaCloudClient) -> GlobalFirewallRuleset:
    return GlobalFirewallRuleset.model_validate(client.get("/firewall-rulesets/global"))


def update_global_firewall_ruleset(
    client: LambdaCloudClient, rules: list[FirewallRule]
) -> GlobalFirewallRuleset:
    validate_firewall_rules(rules)
    data = client.patch(
        "/firewall-rulesets/global", json={"rules": serialize_firewall_rules(rules)}
    )
    return GlobalFirewallRuleset.model_validate(data)


def list_audit_events(
    client: LambdaCloudClient,
    start: str | None = None,
    end: str | None = None,
    resource_type: str | None = None,
    all_pages: bool = False,
) -> list[AuditEvent]:
    params = {
        key: value
        for key, value in {
            "start": start,
            "end": end,
            "resource_type": resource_type,
        }.items()
        if value is not None
    }
    events: list[AuditEvent] = []
    data, page_token = client.get_page("/audit-events", params=params)
    events.extend(AuditEvent.model_validate(item) for item in data)
    while all_pages and page_token:
        data, page_token = client.get_page(
            "/audit-events", params={**params, "page_token": page_token}
        )
        events.extend(AuditEvent.model_validate(item) for item in data)
    return events
