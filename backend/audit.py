"""Append-only JSON audit trail for the Campus Customs agent team.

output/audit_trail.json holds a single JSON array. Every call to
append_event() reads the existing array (treating a missing/empty file as
[]), appends one event, and writes the whole array back -- it never
truncates or drops prior runs' events.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .models import AuditEvent

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

_lock = Lock()


def _load_existing() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    text = AUDIT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return []
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{AUDIT_PATH} does not contain a JSON array; refusing to overwrite it.")
    return data


def append_event(event: AuditEvent) -> None:
    """Append one audit event to output/audit_trail.json, never overwriting prior events."""
    with _lock:
        events = _load_existing()
        events.append(event.model_dump())
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_PATH.write_text(json.dumps(events, indent=2), encoding="utf-8")


def read_all_events() -> list[dict]:
    with _lock:
        return _load_existing()
