"""Lightweight result history stored under the config directory.

Best-effort: history write failures never break a command.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ...core.config import config_dir

_HISTORY_FILE = "history.json"
_MAX_ENTRIES = 25


def _history_path():
    return config_dir() / _HISTORY_FILE


def _default_entry(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "data": data,
        "result_preview": str(data)[:80],
    }


def record_result(kind: str, data: dict[str, Any]) -> None:
    """Append a result entry to the local history file (best-effort)."""
    path = _history_path()
    try:
        history = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    except (OSError, ValueError):
        history = []
    history.append(_default_entry(kind, data))
    history = history[-_MAX_ENTRIES:]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(history, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def last_result(kind: str) -> dict[str, Any] | None:
    """Return the most recent recorded result for ``kind``, if any."""
    path = _history_path()
    if not path.is_file():
        return None
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for entry in reversed(history):
        if entry.get("kind") == kind:
            return entry
    return None
