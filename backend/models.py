"""Shared Pydantic models for the Campus Customs agent team.

These are the typed structures agents use to delegate work, request
approvals, and report results. Nothing here talks to the database directly
-- all shop facts come from the MCP server tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

AgentRole = Literal["boss", "inventory", "accounting", "facilities", "customer_service", "system"]
"""'system' denotes an audit event triggered by the FastAPI backend itself
(e.g. a human approving a payment via HTTP, or a database reset) -- never
an agent, and never something an agent can trigger."""


@dataclass
class AgentDeps:
    """Per-run context threaded through every agent via RunContext.deps.

    Lets the shared MCP toolset's process_tool_call hook (see
    mcp_client.py) attribute each real tool call to the right run_id,
    ticket, and agent in the audit trail.
    """

    run_id: str
    ticket_id: int
    agent_name: AgentRole


class DelegationRecord(BaseModel):
    """One delegation hop: who asked whom to do what, and why."""

    from_agent: AgentRole
    to_agent: AgentRole
    reason: str
    depth: int = Field(ge=0, description="Delegation depth at which this hop occurred.")


class ApprovalRequest(BaseModel):
    """A proposed financial or consequential action awaiting human sign-off.

    Agents may only PROPOSE actions of this shape. Only a human, acting
    outside the agent loop, can supply `approved_by` to actually authorize
    the matching MCP write tool (record_approved_payment).
    """

    action: Literal["payment"]
    kind: str = Field(description="e.g. 'rent' or 'invoice'")
    ref_id: int = Field(description="Related lease.id or invoice.id")
    amount: float = Field(gt=0)
    account: str
    reason: str
    requested_by: AgentRole


class InventoryFinding(BaseModel):
    sku: str
    size: str
    available_qty: int
    requested_qty: int
    sufficient: bool
    vendor_name: str | None = None
    vendor_lead_days: int | None = None
    notes: str


class AccountingFinding(BaseModel):
    cash_account: str
    cash_balance: float
    proposed_action: ApprovalRequest | None = None
    safe_to_pay: bool
    notes: str


class FacilitiesFinding(BaseModel):
    lease_id: int
    rent_amount: float
    due_date: str
    days_until_due: int | None = None
    notes: str


class CustomerServiceFinding(BaseModel):
    ticket_id: int
    requester: str
    feasible: bool
    recommendation: str
    notes: str


class TicketResolution(BaseModel):
    """The Boss agent's final, synthesized recommendation for one ticket."""

    ticket_id: int
    summary: str
    recommendation: str
    requires_human_approval: bool
    delegations: list[DelegationRecord] = Field(default_factory=list)
    run_id: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditEvent(BaseModel):
    """One append-only audit log entry for an agent-loop step."""

    timestamp: str = Field(default_factory=utc_now_iso)
    run_id: str
    ticket_id: int | None = None
    agent: AgentRole
    event_type: Literal[
        "agent_start",
        "agent_end",
        "delegation",
        "mcp_tool_call",
        "approval_request",
        "approval_recorded",
        "reset",
        "error",
    ]
    detail: dict = Field(default_factory=dict)
