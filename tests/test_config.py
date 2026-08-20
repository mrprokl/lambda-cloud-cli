"""Tests for API key resolution and config storage."""

from __future__ import annotations

import os
import stat

import pytest

from lambda_cloud.core.config import (
    config_path,
    delete_stored_config,
    describe_api_key_source,
    load_stored_config,
    resolve_api_key,
    save_api_key,
)
from lambda_cloud.core.errors import ConfigError


def test_resolve_prefers_flag(monkeypatch):
    monkeypatch.setenv("LAMBDA_API_KEY", "env-key")
    assert resolve_api_key("flag-key") == "flag-key"


def test_resolve_uses_env():
    assert resolve_api_key() == "test-api-key"  # set by isolated_env fixture


def test_resolve_uses_stored_config(monkeypatch):
    monkeypatch.delenv("LAMBDA_API_KEY")
    save_api_key("stored-key")
    assert resolve_api_key() == "stored-key"


def test_resolve_raises_when_missing(monkeypatch):
    monkeypatch.delenv("LAMBDA_API_KEY")
    with pytest.raises(ConfigError, match="lambda-cloud login"):
        resolve_api_key()


def test_save_writes_owner_only_file():
    path = save_api_key("k")
    assert path == config_path()
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600
    assert load_stored_config().api_key == "k"


def test_delete_stored_config():
    save_api_key("k")
    assert delete_stored_config() is True
    assert delete_stored_config() is False
    assert load_stored_config() is None


def test_describe_sources(monkeypatch):
    monkeypatch.delenv("LAMBDA_API_KEY")
    assert describe_api_key_source() is None
    assert describe_api_key_source("flag") == ("--api-key flag", "flag")
    save_api_key("stored")
    source, key = describe_api_key_source()
    assert key == "stored"
    assert str(config_path()) == source
