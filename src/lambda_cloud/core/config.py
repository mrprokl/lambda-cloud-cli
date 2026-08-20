"""Local configuration and API key resolution.

Resolution order for the API key:

1. ``--api-key`` command-line flag
2. ``LAMBDA_API_KEY`` environment variable
3. Config file written by ``lambda-cloud login``

The config directory is ``$LAMBDA_CLOUD_CONFIG_DIR`` if set, otherwise
``$XDG_CONFIG_HOME/lambda-cloud`` (defaulting to ``~/.config/lambda-cloud``).
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

API_KEY_ENV_VAR = "LAMBDA_API_KEY"
CONFIG_DIR_ENV_VAR = "LAMBDA_CLOUD_CONFIG_DIR"
_CONFIG_FILE_NAME = "config.json"


@dataclass(frozen=True)
class StoredConfig:
    """Content of the on-disk config file."""

    api_key: str


def config_dir() -> Path:
    """Return the directory where lambda-cloud stores its configuration."""
    override = os.environ.get(CONFIG_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser()
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_home).expanduser() if xdg_home else Path.home() / ".config"
    return base / "lambda-cloud"


def config_path() -> Path:
    """Return the path of the config file."""
    return config_dir() / _CONFIG_FILE_NAME


def load_stored_config() -> StoredConfig | None:
    """Load the config file, returning ``None`` if it does not exist."""
    path = config_path()
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ConfigError(f"Invalid config file {path}: {exc}") from exc
    api_key = raw.get("api_key")
    if not api_key:
        raise ConfigError(f"Config file {path} does not contain an API key.")
    return StoredConfig(api_key=api_key)


def write_secret_file(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` with owner-only permissions (0600)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


def save_api_key(api_key: str) -> Path:
    """Persist the API key with owner-only permissions (0600)."""
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = config_path()
    write_secret_file(path, json.dumps({"api_key": api_key}) + "\n")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def delete_stored_config() -> bool:
    """Delete the config file. Returns ``True`` if a file was removed."""
    path = config_path()
    if path.is_file():
        path.unlink()
        return True
    return False


def resolve_api_key(flag_value: str | None = None) -> str:
    """Resolve the API key from flag, environment, then config file."""
    if flag_value:
        return flag_value
    env_value = os.environ.get(API_KEY_ENV_VAR)
    if env_value:
        return env_value
    stored = load_stored_config()
    if stored:
        return stored.api_key
    raise ConfigError(
        "No API key configured. Run `lambda-cloud login`, "
        f"set the {API_KEY_ENV_VAR} environment variable, "
        "or pass --api-key."
    )


def mask_api_key(api_key: str) -> str:
    """Return a masked representation of an API key, safe to display."""
    if len(api_key) <= 8:
        return "…"
    return f"{api_key[:8]}…"


def describe_api_key_source(flag_value: str | None = None) -> tuple[str, str] | None:
    """Return ``(source, api_key)`` describing where the key comes from."""
    if flag_value:
        return "--api-key flag", flag_value
    env_value = os.environ.get(API_KEY_ENV_VAR)
    if env_value:
        return f"{API_KEY_ENV_VAR} environment variable", env_value
    stored = load_stored_config()
    if stored:
        return str(config_path()), stored.api_key
    return None
