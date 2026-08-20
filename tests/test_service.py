"""Tests for the api.service layer (pure logic + request shaping)."""

from __future__ import annotations

import httpx
import pytest
import respx

from lambda_cloud.api import service
from lambda_cloud.api.client import DEFAULT_BASE_URL, LambdaCloudClient
from lambda_cloud.core.errors import LambdaCloudError
from lambda_cloud.mngr.models import FirewallRule, NetworkProtocol


def _audit_event(event_id: str) -> dict:
    return {
        "event_id": event_id,
        "event_time": "2025-09-15T10:30:45Z",
        "action": "instances.launch",
        "service_name": "cloud",
        "resource_name": "instance",
        "catalog_version": "2025-11-18",
        "actor_lrn": None,
        "actor_email": None,
        "actor_display_name": None,
        "resource_lrns": [],
        "resource_owner_lrn": None,
        "request_api_key_lrn": None,
        "workspace_lrn": None,
        "client_ip": None,
        "client_user_agent": None,
        "surface": "api",
        "result": {"status": "success", "status_code": 200},
        "additional_details": {},
    }


@respx.mock
def test_audit_follows_all_pages():
    respx.get(f"{DEFAULT_BASE_URL}/audit-events").mock(
        side_effect=[
            httpx.Response(
                200, json={"data": [_audit_event("e1")], "page_token": "tok1"}
            ),
            httpx.Response(200, json={"data": [_audit_event("e2")], "page_token": None}),
        ]
    )
    with LambdaCloudClient("k", min_interval=0) as client:
        events = service.list_audit_events(client, all_pages=True)
    assert [e.event_id for e in events] == ["e1", "e2"]


@respx.mock
def test_audit_stops_after_first_page_by_default():
    respx.get(f"{DEFAULT_BASE_URL}/audit-events").mock(
        return_value=httpx.Response(
            200, json={"data": [_audit_event("e1")], "page_token": "tok1"}
        )
    )
    with LambdaCloudClient("k", min_interval=0) as client:
        events = service.list_audit_events(client)
    assert len(events) == 1


def test_validate_firewall_rules_rejects_icmp_with_ports():
    rule = FirewallRule.model_validate(
        {"protocol": "icmp", "port_range": [22, 22], "source_network": "0.0.0.0/0"}
    )
    with pytest.raises(LambdaCloudError, match="icmp"):
        service.validate_firewall_rules([rule])


def test_validate_firewall_rules_requires_ports_for_tcp():
    rule = FirewallRule(protocol=NetworkProtocol.TCP, source_network="0.0.0.0/0")
    with pytest.raises(LambdaCloudError, match="port_range"):
        service.validate_firewall_rules([rule])


def test_serialize_rules_drops_none_port_range():
    rule = FirewallRule(protocol=NetworkProtocol.ICMP, source_network="0.0.0.0/0")
    payload = service.serialize_firewall_rules([rule])
    assert payload == [
        {"protocol": "icmp", "source_network": "0.0.0.0/0", "description": ""}
    ]


def test_parse_instance_types_sorts_by_price(sample_instance_types):
    offers = service.parse_instance_types(sample_instance_types)
    assert len(offers) == 1
    assert offers[0].instance_type.name == "gpu_1x_a10"
    assert offers[0].regions_with_capacity_available[0].name == "us-west-1"
