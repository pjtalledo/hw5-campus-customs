"""Campus Customs FastAPI backend (Problem 7).

Start from the backend/ directory with:
    uvicorn main:app --reload --port 8000
(The professor's command `uvicorn main --reload --port 8000` resolves to
the same thing -- uvicorn's string-target form infers the `app` attribute
in main.py when none is given.)

Reuses the existing agent orchestrator (backend.orchestrator) and the
existing MCP server (mcp_server/server.py) -- no duplicate agent logic, no
direct-SQLite business-data layer. The only state this module owns
directly is a single in-process lock that serializes runs/approvals/resets
so they cannot race each other.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# main.py must work both as `python -m backend.main` (package context) and
# as the professor's required `uvicorn main --reload --port 8000` run from
# inside backend/ (where uvicorn imports "main" as a bare top-level module,
# with no package context at all -- relative imports like `from .audit`
# would fail there). To support both without duplicating any logic, we put
# the project root on sys.path and import everything through the real
# "backend" package by its full name, regardless of the process's cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_MCP_SERVER_DIR = _PROJECT_ROOT / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))

import approvals  # noqa: E402  -- the Problem 5 pending-approval store, reused as-is
from backend.audit import append_event, read_all_events  # noqa: E402
from backend.mcp_call import call_tool  # noqa: E402
from backend.models import AuditEvent  # noqa: E402
from backend.orchestrator import run_ticket_team  # noqa: E402

import os as _os  # noqa: E402

# CAMPUS_CUSTOMS_ORIGINAL_DB / CAMPUS_CUSTOMS_WORKING_DB let tests point the
# reset route at disposable scratch files instead of the real databases.
# Unset in normal operation, so normal behavior is unchanged.
ORIGINAL_DB = Path(_os.environ.get("CAMPUS_CUSTOMS_ORIGINAL_DB") or (_PROJECT_ROOT / "data" / "campus_customs.db"))
WORKING_DB = Path(_os.environ.get("CAMPUS_CUSTOMS_WORKING_DB") or (_PROJECT_ROOT / "data" / "campus_customs_new.db"))
KNOWN_TICKET_IDS = (101, 102, 103)

app = FastAPI(title="Campus Customs Backend", version="1.0.0")

# Local-dev CORS: the Problem 8 React dev server runs on one of these origins.
# This is intentionally a short, explicit allowlist, not a wildcard -- see
# the trust-boundary note on the approval route below.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serializes ticket runs, payment approvals, and database resets so none of
# them can execute concurrently with another (Correction/requirement 24).
_mutation_lock = asyncio.Lock()


def _busy_error() -> HTTPException:
    return HTTPException(status_code=409, detail="Another run, approval, or reset is already in progress. Try again shortly.")


# ---------------------------------------------------------------------------
# 1. Tickets: open/resolved status
# ---------------------------------------------------------------------------


@app.get("/tickets")
async def get_tickets():
    """Return all three tickets and whether each is open or resolved, read
    live from the working database through the MCP server's list_all_tickets
    tool (not cached, not hardcoded)."""
    tickets = await call_tool("list_all_tickets")
    return {"tickets": tickets}


# ---------------------------------------------------------------------------
# 2. Run the agent team on a ticket
# ---------------------------------------------------------------------------


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int):
    """Run the existing agent team (backend.orchestrator.run_ticket_team) on
    a ticket. Validates the ticket id, executes the real PydanticAI/MCP
    workflow (no simulated tool calls), and returns the run_id plus the
    structured TicketResolution. Every step is appended to the audit trail
    by the orchestrator/mcp_client as it already does."""
    if ticket_id not in KNOWN_TICKET_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown ticket id {ticket_id}.")
    if _mutation_lock.locked():
        raise _busy_error()
    async with _mutation_lock:
        try:
            resolution = await run_ticket_team(ticket_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Agent run failed: {exc}") from exc
    return {"run_id": resolution.run_id, "result": resolution.model_dump()}


# ---------------------------------------------------------------------------
# 3. Recent agent/tool events for the dashboard to refresh against
# ---------------------------------------------------------------------------


@app.get("/events")
async def get_events(
    limit: int = 50,
    ticket_id: int | None = None,
    agent: str | None = None,
    run_id: str | None = None,
):
    """Return recent events from the existing append-only audit trail, in
    chronological order (oldest of the returned window first), optionally
    filtered by ticket_id / agent / run_id, capped at `limit`."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")
    events = read_all_events()
    if ticket_id is not None:
        events = [e for e in events if e.get("ticket_id") == ticket_id]
    if agent is not None:
        events = [e for e in events if e.get("agent") == agent]
    if run_id is not None:
        events = [e for e in events if e.get("run_id") == run_id]
    windowed = events[-limit:]
    return {"events": windowed, "count": len(windowed), "total_matching": len(events)}


# ---------------------------------------------------------------------------
# Pending approvals (read-only; added for Problem 8's dashboard, which needs
# a safe way to discover genuine pending approval requests without querying
# the approvals store directly or inventing data)
# ---------------------------------------------------------------------------


@app.get("/approvals")
async def get_approvals(status: str | None = "pending"):
    """List real approval requests from the existing Problem 5 approvals
    store, optionally filtered by status (default: 'pending', the ones a
    human still needs to act on). Read-only -- cannot grant approval."""
    return {"approvals": approvals.list_approvals(status)}


# ---------------------------------------------------------------------------
# 4. Human payment approval -- the only route that can move money
# ---------------------------------------------------------------------------


class ApprovePaymentRequest(BaseModel):
    approval_id: str = Field(min_length=1)
    approver_name: str = Field(min_length=1)


@app.post("/payments/{approval_id}/approve")
async def approve_payment(approval_id: str, body: ApprovePaymentRequest):
    """Human-facing approval route. This is the ONLY route in this backend
    that can cause a real financial change, and it does so in two steps
    that reuse the exact Problem 5 security mechanism unchanged:

      1. approvals.approve_pending(approval_id, approver_name) -- moves a
         'pending' request to 'approved'. This function is never imported
         by backend/agents.py, backend/orchestrator.py, or any MCP tool
         registration, so no agent can call it, directly or indirectly.
      2. mcp_call.call_tool('record_approved_payment', approval_id=...) --
         a genuine MCP call to the same tool used everywhere else, which
         re-validates cash sufficiency and invoice status, and atomically
         consumes the approval so it can never be replayed.

    TRUST BOUNDARY (documented, not hidden): this endpoint does not
    implement real user authentication -- there is no login, session, or
    cryptographic signature behind `approver_name`. It is a plain HTTP POST
    restricted only by CORS to the local dashboard's own origin and by
    running on localhost. This is explicitly NOT a substitute for human
    authorization in anything beyond this local, single-user homework
    dashboard -- a real deployment would need actual authentication in
    front of this route before it could be trusted. Until that exists, the
    honest security boundary is: the approval and single-use mechanisms
    inherited from Problem 5 (binding to exact invoice/amount/account,
    single-use consumption, cash/invoice re-validation) are real and
    enforced; the claim that a specific named human clicked the button is
    not cryptographically verified, and this limitation is stated here
    rather than concealed.
    """
    if approval_id != body.approval_id:
        raise HTTPException(status_code=400, detail="approval_id in the URL and body must match.")
    if _mutation_lock.locked():
        raise _busy_error()
    async with _mutation_lock:
        try:
            approvals.approve_pending(approval_id, body.approver_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        append_event(
            AuditEvent(
                run_id="http-approval",
                ticket_id=None,
                agent="system",
                event_type="approval_recorded",
                detail={"approval_id": approval_id, "approved_by": body.approver_name},
            )
        )

        try:
            result = await call_tool("record_approved_payment", approval_id=approval_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Payment recording failed: {exc}") from exc

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# 5. Current checking balance
# ---------------------------------------------------------------------------


@app.get("/cash")
async def get_cash(account: str = "checking"):
    """Return the real, current balance of a cash account through MCP."""
    data = await call_tool("get_cash_balance", account=account)
    return data


# ---------------------------------------------------------------------------
# 6. Reset the working database to its original, pristine values
# ---------------------------------------------------------------------------


class ResetRequest(BaseModel):
    confirm: str = Field(description="Must be exactly the literal string 'RESET' to proceed.")


@app.post("/admin/reset-working-database")
async def reset_working_database(body: ResetRequest):
    """Reset ONLY data/campus_customs_new.db from the pristine
    data/campus_customs.db. Never touches the original file.

    Requires an explicit confirm='RESET' in the request body (a plain
    'yes'/true is not accepted, to make an accidental or automated call
    unlikely to match by chance). Refuses while a run/approval/reset is
    already in progress. Does not touch output/audit_trail.json or any
    prior homework's output files -- the reset writes only the working
    database file itself, and the reset action is itself logged as a new
    audit event (never replacing or deleting prior events).

    Pending-approval handling (documented per the assignment's explicit
    requirement): any approval still 'pending' or 'approved' (i.e. not yet
    spent) is invalidated to 'rejected' as part of the reset, so it cannot
    later be replayed against the freshly-reset database's restored
    balances/invoice statuses. Already-'consumed' or already-'rejected'
    approvals are left untouched as historical record.
    """
    if body.confirm != "RESET":
        raise HTTPException(status_code=400, detail="confirm must be exactly 'RESET' to proceed.")
    if not ORIGINAL_DB.exists():
        raise HTTPException(status_code=500, detail="Original database is missing; refusing to reset.")
    if _mutation_lock.locked():
        raise _busy_error()

    async with _mutation_lock:
        shutil.copyfile(ORIGINAL_DB, WORKING_DB)
        invalidated = approvals.invalidate_unconsumed_approvals(reason="working database reset")
        append_event(
            AuditEvent(
                run_id="http-reset",
                ticket_id=None,
                agent="system",
                event_type="reset",
                detail={"invalidated_approval_ids": invalidated, "invalidated_count": len(invalidated)},
            )
        )

    return {
        "status": "reset complete",
        "working_db": str(WORKING_DB),
        "original_db_untouched": True,
        "invalidated_approvals": invalidated,
    }
