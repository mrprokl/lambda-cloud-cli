"""Shared pytest fixtures: isolated env, runner and sample API payloads."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from lambda_cloud.cli.app import app

BASE_URL = "https://cloud.lambda.ai/api/v1"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Isolate credentials, config dir and disable rate-limit sleeping."""
    monkeypatch.setenv("LAMBDA_API_KEY", "test-api-key")
    monkeypatch.setenv("LAMBDA_CLOUD_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("LAMBDA_CLOUD_MIN_INTERVAL", "0")
    monkeypatch.setenv("COLUMNS", "200")  # avoid rich table truncation in tests
    monkeypatch.delenv("LAMBDA_CLOUD_API_URL", raising=False)
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app


@pytest.fixture
def sample_instance() -> dict:
    return {
        "id": "0920582c7ff041399e34823a0be62549",
        "name": "training-run",
        "ip": "192.0.2.10",
        "private_ip": "10.0.0.5",
        "status": "active",
        "ssh_key_names": ["my-key"],
        "file_system_names": [],
        "region": {"name": "us-west-1", "description": "California, USA"},
        "instance_type": {
            "name": "gpu_1x_a10",
            "description": "1x NVIDIA A10",
            "gpu_description": "A10",
            "price_cents_per_hour": 60,
            "specs": {"vcpus": 30, "memory_gib": 200, "storage_gib": 1400, "gpus": 1},
            "architecture": "x86_64",
        },
        "hostname": "0920582c7ff041399e34823a0be62549",
    }


@pytest.fixture
def sample_instance_types() -> dict:
    return {
        "gpu_1x_a10": {
            "instance_type": {
                "name": "gpu_1x_a10",
                "description": "1x NVIDIA A10",
                "gpu_description": "A10",
                "price_cents_per_hour": 60,
                "specs": {"vcpus": 30, "memory_gib": 200, "storage_gib": 1400, "gpus": 1},
                "architecture": "x86_64",
            },
            "regions_with_capacity_available": [
                {"name": "us-west-1", "description": "California, USA"}
            ],
        }
    }
