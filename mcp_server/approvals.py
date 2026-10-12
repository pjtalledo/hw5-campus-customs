"""File-based pending-approval store for payment authorization.

This module deliberately exposes no way for an agent to grant its own
approval. `create_pending_approval` is reachable from an MCP tool (an agent
may REQUEST approval). `approve_pending` is the one trusted, human-only
action -- it is only ever called from backend/approve_payment.py, a
separate CLI script that is never registered as an agent tool or exposed
through MCP. `consume_approval` enforces single-use: an approval can be
spent by record_approved_payment exactly once.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

# CAMPUS_CUSTOMS_APPROVALS_PATH lets tests point this store at a disposable
# scratch file instead of the real one. Unset in normal operation.
APPROVALS_PATH = Path(
    os.environ.get("CAMPUS_CUSTOMS_APPROVALS_PATH")
    or (Path(__file__).resolve().parent.parent / "output" / "pending_approvals.json")
)
_lock = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict]:
    if not APPROVALS_PATH.exists():
        return []
    text = APPROVALS_PATH.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else []


def _save(items: list[dict]) -> None:
    APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVALS_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def create_pending_approval(
    kind: str, ref_id: int, amount: float, account: str, reason: str, requested_by: str
) -> dict:
    """Called from an MCP tool when an agent wants to request a payment be approved.

    Creates a 'pending' record. Does NOT authorize anything by itself.
    """
    with _lock:
        items = _load()
        approval = {
            "approval_id": str(uuid.uuid4()),
            "kind": kind,
            "ref_id": ref_id,
            "amount": amount,
            "account": account,
            "reason": reason,
            "requested_by": requested_by,
            "status": "pending",
            "created_at": _now(),
            "approved_by": None,
            "approved_at": None,
            "consumed_at": None,
        }
        items.append(approval)
        _save(items)
        return approval


def list_approvals(status: str | None = None) -> list[dict]:
    """Read-only listing of approval requests, optionally filtered by status
    ('pending', 'approved', 'consumed', 'rejected'). Used by the Problem 8
    dashboard to show genuine pending approvals -- never fabricated."""
    items = _load()
    if status is not None:
        items = [a for a in items if a["status"] == status]
    return items


def get_approval(approval_id: str) -> dict | None:
    for a in _load():
        if a["approval_id"] == approval_id:
            return a
    return None


def approve_pending(approval_id: str, approver_name: str) -> dict:
    """HUMAN-ONLY action. Never call this from agent code or an MCP tool."""
    if not approver_name or not approver_name.strip():
        raise ValueError("approver_name is required.")
    with _lock:
        items = _load()
        for a in items:
            if a["approval_id"] == approval_id:
                if a["status"] != "pending":
                    raise ValueError(f"Approval {approval_id} is '{a['status']}', not pending; refusing.")
                a["status"] = "approved"
                a["approved_by"] = approver_name
                a["approved_at"] = _now()
                _save(items)
                return a
        raise ValueError(f"Approval {approval_id} not found.")


def invalidate_unconsumed_approvals(reason: str) -> list[str]:
    """Called when the working database is reset (Problem 7).

    Any approval still 'pending' or 'approved' (i.e. not yet spent) is
    forced to 'rejected', so it can never be consumed against the
    freshly-reset database -- a stale approval could otherwise reference an
    invoice/amount that no longer matches post-reset reality, or could
    double-spend against a balance that has just been restored. Already
    'consumed' or already 'rejected' approvals are left untouched as
    historical record. Returns the list of approval_ids that were
    invalidated.
    """
    with _lock:
        items = _load()
        invalidated = []
        for a in items:
            if a["status"] in ("pending", "approved"):
                a["status"] = "rejected"
                a["rejected_reason"] = reason
                a["rejected_at"] = _now()
                invalidated.append(a["approval_id"])
        _save(items)
        return invalidated


def consume_approval(approval_id: str) -> dict:
    """Marks an approved request as spent. Raises if it is not currently 'approved'
    (blocks replay: an already-consumed, still-pending, or rejected approval cannot
    be consumed again or for the first time)."""
    with _lock:
        items = _load()
        for a in items:
            if a["approval_id"] == approval_id:
                if a["status"] != "approved":
                    raise ValueError(
                        f"Approval {approval_id} is '{a['status']}', not 'approved'; cannot consume."
                    )
                a["status"] = "consumed"
                a["consumed_at"] = _now()
                _save(items)
                return a
        raise ValueError(f"Approval {approval_id} not found.")
