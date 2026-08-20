"""Tests for the low-level HTTP client."""

from __future__ import annotations

import httpx
import pytest
import respx

from lambda_cloud.api.client import DEFAULT_BASE_URL, LambdaCloudClient
from lambda_cloud.core.errors import APIError


def make_client(**kwargs) -> LambdaCloudClient:
    return LambdaCloudClient("test-key", min_interval=0, **kwargs)


@respx.mock
def test_sends_bearer_token_and_unwraps_data():
    route = respx.get(f"{DEFAULT_BASE_URL}/instances").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "abc"}]})
    )
    with make_client() as client:
        data = client.get("/instances")
    assert data == [{"id": "abc"}]
    assert route.calls[0].request.headers["Authorization"] == "Bearer test-key"


@respx.mock
def test_error_response_becomes_api_error():
    respx.get(f"{DEFAULT_BASE_URL}/instances").mock(
        return_value=httpx.Response(
            401,
            json={
                "error": {
                    "code": "global/invalid-api-key",
                    "message": "Invalid API key",
                    "suggestion": "Generate a new one",
                }
            },
        )
    )
    with make_client() as client, pytest.raises(APIError) as exc_info:
        client.get("/instances")
    assert exc_info.value.code == "global/invalid-api-key"
    assert exc_info.value.status_code == 401
    assert exc_info.value.suggestion == "Generate a new one"


@respx.mock
def test_retries_on_429_with_retry_after():
    route = respx.get(f"{DEFAULT_BASE_URL}/instances").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}, json={"error": {}}),
            httpx.Response(200, json={"data": []}),
        ]
    )
    with make_client() as client:
        assert client.get("/instances") == []
    assert route.call_count == 2


@respx.mock
def test_get_page_returns_page_token():
    respx.get(f"{DEFAULT_BASE_URL}/audit-events").mock(
        return_value=httpx.Response(200, json={"data": [{"event_id": "e1"}], "page_token": "tok1"})
    )
    with make_client() as client:
        data, token = client.get_page("/audit-events")
    assert data == [{"event_id": "e1"}]
    assert token == "tok1"


@respx.mock
def test_non_json_error_body_still_raises_api_error():
    respx.get(f"{DEFAULT_BASE_URL}/instances").mock(
        return_value=httpx.Response(502, text="bad gateway")
    )
    with make_client() as client, pytest.raises(APIError) as exc_info:
        client.get("/instances")
    assert exc_info.value.status_code == 502
