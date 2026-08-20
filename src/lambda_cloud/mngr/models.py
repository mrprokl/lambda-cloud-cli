"""Pydantic models for Lambda Cloud API resources.

All models ignore unknown fields so the CLI keeps working when the API adds
new attributes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base model that tolerates unknown fields from the API."""

    model_config = ConfigDict(extra="ignore")


class Region(APIModel):
    name: str
    description: str = ""


class InstanceTypeSpecs(APIModel):
    vcpus: int
    memory_gib: int
    storage_gib: int
    gpus: int


class InstanceType(APIModel):
    name: str
    description: str = ""
    gpu_description: str = ""
    price_cents_per_hour: int
    specs: InstanceTypeSpecs
    architecture: str = ""

    @property
    def price_per_hour(self) -> float:
        return self.price_cents_per_hour / 100


class InstanceTypeOffer(APIModel):
    """An instance type together with the regions where capacity is available."""

    instance_type: InstanceType
    regions_with_capacity_available: list[Region] = []


class InstanceStatus(str, Enum):
    BOOTING = "booting"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    TERMINATED = "terminated"
    TERMINATING = "terminating"
    PREEMPTED = "preempted"


class FilesystemMountEntry(APIModel):
    mount_point: str
    file_system_id: str


class TagEntry(APIModel):
    key: str
    value: str


class FirewallRulesetEntry(APIModel):
    id: str


class Instance(APIModel):
    id: str
    name: str | None = None
    ip: str | None = None
    private_ip: str | None = None
    status: InstanceStatus
    ssh_key_names: list[str] = []
    file_system_names: list[str] = []
    file_system_mounts: list[FilesystemMountEntry] | None = None
    region: Region | None = None
    instance_type: InstanceType | None = None
    hostname: str | None = None
    jupyter_url: str | None = None
    tags: list[TagEntry] | None = None
    firewall_rulesets: list[FirewallRulesetEntry] | None = None


class InstanceLaunchResponse(APIModel):
    instance_ids: list[str]


class InstanceRestartResponse(APIModel):
    restarted_instances: list[Instance]


class InstanceTerminateResponse(APIModel):
    terminated_instances: list[Instance]


class SSHKey(APIModel):
    id: str
    name: str
    public_key: str


class GeneratedSSHKey(SSHKey):
    private_key: str


class User(APIModel):
    id: str
    email: str
    status: str = ""


class Filesystem(APIModel):
    id: str
    name: str
    mount_point: str
    created: datetime | None = None
    created_by: User | None = None
    is_in_use: bool = False
    region: Region | None = None
    bytes_used: int | None = None


class Image(APIModel):
    id: str
    name: str
    description: str = ""
    family: str = ""
    version: str = ""
    architecture: str = ""
    region: Region | None = None
    created_time: datetime | None = None
    updated_time: datetime | None = None


class NetworkProtocol(str, Enum):
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ALL = "all"


class FirewallRule(APIModel):
    protocol: NetworkProtocol
    port_range: tuple[int, int] | None = None
    source_network: str
    description: str = ""

    @property
    def ports_display(self) -> str:
        if self.protocol is NetworkProtocol.ICMP or self.port_range is None:
            return "-"
        low, high = self.port_range
        return str(low) if low == high else f"{low}-{high}"


class FirewallRuleset(APIModel):
    id: str
    name: str
    region: Region | None = None
    rules: list[FirewallRule] = []
    created: datetime | None = None
    instance_ids: list[str] = []


class GlobalFirewallRuleset(APIModel):
    id: str
    name: str = ""
    rules: list[FirewallRule] = []


class AuditResult(APIModel):
    status: str
    status_code: int | None = None


class AuditEvent(APIModel):
    event_id: str
    event_time: datetime | str
    action: str
    service_name: str = ""
    resource_name: str = ""
    catalog_version: str = ""
    actor_email: str | None = None
    actor_display_name: str | None = None
    resource_lrns: list[str] = []
    client_ip: str | None = None
    client_user_agent: str | None = None
    surface: str | None = None
    result: AuditResult | None = None
