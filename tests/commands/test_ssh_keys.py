"""Tests for the `ssh-keys` and auth commands."""

from __future__ import annotations

import os
import stat

import httpx
import respx
from tests.conftest import BASE_URL
from typer.testing import CliRunner

from lambda_cloud.core.config import config_path
from lambda_cloud.core.errors import LambdaCloudError


class TestSSHKeys:
    @respx.mock
    def test_add_with_public_key(self, runner: CliRunner, cli_app):
        route = respx.post(f"{BASE_URL}/ssh-keys").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"id": "k1", "name": "work", "public_key": "ssh-ed25519 AAAA"}},
            )
        )
        result = runner.invoke(
            cli_app, ["ssh-keys", "add", "--name", "work", "--public-key", "ssh-ed25519 AAAA"]
        )
        assert result.exit_code == 0
        import json as std_json

        assert std_json.loads(route.calls[0].request.content) == {
            "name": "work",
            "public_key": "ssh-ed25519 AAAA",
        }

    @respx.mock
    def test_add_generated_saves_private_key(self, runner: CliRunner, cli_app, tmp_path):
        respx.post(f"{BASE_URL}/ssh-keys").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "id": "k2",
                        "name": "generated",
                        "public_key": "ssh-ed25519 BBBB",
                        "private_key": "PRIVATE-KEY-MATERIAL",
                    }
                },
            )
        )
        target = tmp_path / "id_lambda"
        result = runner.invoke(
            cli_app, ["ssh-keys", "add", "--name", "generated", "--save-to", str(target)]
        )
        assert result.exit_code == 0
        assert target.read_text().strip() == "PRIVATE-KEY-MATERIAL"
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o600

    def test_add_conflicting_key_sources(self, runner: CliRunner, cli_app, tmp_path):
        key_file = tmp_path / "id.pub"
        key_file.write_text("ssh-ed25519 CCCC")
        result = runner.invoke(
            cli_app,
            ["ssh-keys", "add", "--name", "x", "--public-key", "y", "--file", str(key_file)],
        )
        assert result.exit_code == 1
        assert isinstance(result.exception, LambdaCloudError)
        assert "mutually exclusive" in str(result.exception)

    @respx.mock
    def test_delete_requires_confirmation(self, runner: CliRunner, cli_app):
        route = respx.delete(f"{BASE_URL}/ssh-keys/k1").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        result = runner.invoke(cli_app, ["ssh-keys", "delete", "k1"], input="n\n")
        assert result.exit_code == 0
        assert route.call_count == 0


class TestAuth:
    @respx.mock
    def test_login_saves_key(self, runner: CliRunner, cli_app):
        respx.get(f"{BASE_URL}/instances").mock(return_value=httpx.Response(200, json={"data": []}))
        result = runner.invoke(cli_app, ["login", "--api-key", "fresh-key"])
        assert result.exit_code == 0
        import json as std_json

        saved = std_json.loads(config_path().read_text())
        assert saved == {"api_key": "fresh-key"}

    @respx.mock
    def test_login_rejects_invalid_key(self, runner: CliRunner, cli_app):
        respx.get(f"{BASE_URL}/instances").mock(
            return_value=httpx.Response(
                401, json={"error": {"code": "global/invalid-api-key", "message": "nope"}}
            )
        )
        result = runner.invoke(cli_app, ["login", "--api-key", "bad-key"])
        assert result.exit_code == 1
        assert not config_path().exists()

    @respx.mock
    def test_whoami(self, runner: CliRunner, cli_app):
        respx.get(f"{BASE_URL}/instances").mock(return_value=httpx.Response(200, json={"data": []}))
        result = runner.invoke(cli_app, ["whoami"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()
        assert "LAMBDA_API_KEY" in result.output
