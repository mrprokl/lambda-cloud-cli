"""Tests for the `instances` command group."""

from __future__ import annotations

import httpx
import pytest
import respx
from tests.conftest import BASE_URL
from typer.testing import CliRunner

from lambda_cloud.cli.commands.instances import build_launch_payload
from lambda_cloud.core.errors import APIError, LambdaCloudError


class TestLaunchPayload:
    def test_minimal_payload(self):
        payload = build_launch_payload(
            region="us-west-1", instance_type="gpu_1x_a10", ssh_key="my-key"
        )
        assert payload == {
            "region_name": "us-west-1",
            "instance_type_name": "gpu_1x_a10",
            "ssh_key_names": ["my-key"],
        }

    def test_image_id_and_family_are_exclusive(self):
        with pytest.raises(LambdaCloudError, match="mutually exclusive"):
            build_launch_payload(
                region="us-west-1",
                instance_type="gpu_1x_a10",
                ssh_key="my-key",
                image_id="img-1",
                image_family="lambda-stack",
            )

    def test_tags_and_firewall_rulesets(self):
        from lambda_cloud.cli.commands.instances import parse_tag

        tags = [parse_tag("env=prod"), parse_tag("team=ml-research")]
        payload = build_launch_payload(
            region="us-west-1",
            instance_type="gpu_1x_a10",
            ssh_key="my-key",
            tags=tags,
            firewall_rulesets=["rs-1"],
        )
        assert payload["tags"] == [
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "ml-research"},
        ]
        assert payload["firewall_rulesets"] == [{"id": "rs-1"}]

    def test_invalid_tag_rejected(self):
        from lambda_cloud.cli.commands.instances import parse_tag

        with pytest.raises(LambdaCloudError, match="key=value"):
            parse_tag("noequals")


class TestCommands:
    @respx.mock
    def test_list_table(self, runner: CliRunner, cli_app, sample_instance):
        respx.get(f"{BASE_URL}/instances").mock(
            return_value=httpx.Response(200, json={"data": [sample_instance]})
        )
        result = runner.invoke(cli_app, ["instances", "list"])
        assert result.exit_code == 0
        assert "0920582c7ff041399e34823a0be62549" in result.output
        assert "gpu_1x_a10" in result.output
        assert "active" in result.output

    @respx.mock
    def test_list_json(self, runner: CliRunner, cli_app, sample_instance):
        respx.get(f"{BASE_URL}/instances").mock(
            return_value=httpx.Response(200, json={"data": [sample_instance]})
        )
        result = runner.invoke(cli_app, ["--output", "json", "instances", "list"])
        assert result.exit_code == 0
        assert '"id": "0920582c7ff041399e34823a0be62549"' in result.output

    @respx.mock
    def test_get(self, runner: CliRunner, cli_app, sample_instance):
        respx.get(f"{BASE_URL}/instances/{sample_instance['id']}").mock(
            return_value=httpx.Response(200, json={"data": sample_instance})
        )
        result = runner.invoke(cli_app, ["instances", "get", sample_instance["id"]])
        assert result.exit_code == 0
        assert "192.0.2.10" in result.output

    @respx.mock
    def test_launch_minimal(self, runner: CliRunner, cli_app):
        respx.post(f"{BASE_URL}/instance-operations/launch").mock(
            return_value=httpx.Response(200, json={"data": {"instance_ids": ["i-min"]}})
        )
        result = runner.invoke(
            cli_app,
            [
                "instances",
                "launch",
                "--type",
                "gpu_1x_a10",
                "--region",
                "us-west-1",
                "--ssh-key",
                "my-key",
                "-y",
            ],
        )
        assert result.exit_code == 0
        assert "i-min" in result.output

    @respx.mock
    def test_launch(self, runner: CliRunner, cli_app):
        route = respx.post(f"{BASE_URL}/instance-operations/launch").mock(
            return_value=httpx.Response(200, json={"data": {"instance_ids": ["new-id"]}})
        )
        result = runner.invoke(
            cli_app,
            [
                "instances",
                "launch",
                "--type",
                "gpu_1x_a10",
                "--region",
                "us-west-1",
                "--ssh-key",
                "my-key",
                "--tag",
                "env=prod",
                "--yes",
            ],
        )
        assert result.exit_code == 0
        assert "new-id" in result.output
        sent = route.calls[0].request
        import json as std_json

        body = std_json.loads(sent.content)
        assert body["instance_type_name"] == "gpu_1x_a10"
        assert body["tags"] == [{"key": "env", "value": "prod"}]

    @respx.mock
    def test_terminate_aborts_without_confirmation(self, runner: CliRunner, cli_app):
        route = respx.post(f"{BASE_URL}/instance-operations/terminate").mock(
            return_value=httpx.Response(200, json={"data": {"terminated_instances": []}})
        )
        result = runner.invoke(cli_app, ["instances", "terminate", "some-id"], input="n\n")
        assert result.exit_code == 0
        assert "Aborted" in result.output
        assert route.call_count == 0

    @respx.mock
    def test_terminate_with_yes(self, runner: CliRunner, cli_app):
        respx.post(f"{BASE_URL}/instance-operations/terminate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {"terminated_instances": [{"id": "some-id", "status": "terminating"}]}
                },
            )
        )
        result = runner.invoke(cli_app, ["instances", "terminate", "some-id", "--yes"])
        assert result.exit_code == 0
        assert "some-id" in result.output

    @respx.mock
    def test_rename(self, runner: CliRunner, cli_app):
        route = respx.post(f"{BASE_URL}/instances/some-id").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        result = runner.invoke(cli_app, ["instances", "rename", "some-id", "--name", "new-name"])
        assert result.exit_code == 0
        import json as std_json

        assert std_json.loads(route.calls[0].request.content) == {"name": "new-name"}

    @respx.mock
    def test_api_error_is_typed(self, runner: CliRunner, cli_app):
        respx.get(f"{BASE_URL}/instances").mock(
            return_value=httpx.Response(
                401,
                json={"error": {"code": "global/invalid-api-key", "message": "Invalid API key"}},
            )
        )
        result = runner.invoke(cli_app, ["instances", "list"], catch_exceptions=True)
        assert result.exit_code == 1
        assert isinstance(result.exception, APIError)
        assert result.exception.code == "global/invalid-api-key"
