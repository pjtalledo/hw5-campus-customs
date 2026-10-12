"""Boss-led, bidirectionally-connected delegation loop for one ticket.

Connectivity model (Correction 1): the Boss can delegate to any of the four
specialists, AND each specialist can escalate back to the Boss mid-task via
its own `escalate_to_boss` tool -- a real, working tool, not just a prompt
instruction. This means any agent can reach any other agent *through* the
Boss hub (Boss -> specialist, specialist -> Boss -> a different specialist),
which is genuine two-way connectivity, while still structurally forbidding
a specialist from calling another specialist directly (no specialist is
ever given another specialist's delegation tool). Loop safety is enforced
in code, not just by prompt:
  * a hard cap of MAX_DELEGATIONS total hops per ticket,
  * a depth cap (Boss->specialist = depth 1, specialist->Boss escalation =
    depth 2; nothing deeper is possible given the tools each role has),
  * simple cycle detection: the same (from_agent, to_agent) directed pair
    may not repeat more than MAX_REPEATS_PER_PAIR times, which prevents an
    unproductive Boss<->specialist ping-pong even before the global hop cap
    is reached.

Every delegation hop, every agent start/end, and every individual MCP tool
call (via mcp_client's process_tool_call hook) is appended to
output/audit_trail.json.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import Agent, RunContext

from .audit import append_event
from .config import assert_model_is_compliant, get_model
from .mcp_client import new_campus_customs_toolset
from .models import (
    AccountingFinding,
    AgentDeps,
    AgentRole,
    AuditEvent,
    CustomerServiceFinding,
    DelegationRecord,
    FacilitiesFinding,
    InventoryFinding,
    TicketResolution,
)

MAX_DELEGATIONS = 4
MAX_DELEGATION_DEPTH = 2
MAX_REPEATS_PER_PAIR = 2

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class DelegationBudgetExceeded(Exception):
    pass


@dataclass
class _RunState:
    run_id: str
    ticket_id: int
    delegations: list[DelegationRecord] = field(default_factory=list)
    _pair_counts: Counter = field(default_factory=Counter)

    def record(self, from_agent: AgentRole, to_agent: AgentRole, reason: str, depth: int) -> DelegationRecord:
        if len(self.delegations) >= MAX_DELEGATIONS:
            raise DelegationBudgetExceeded(
                f"Delegation budget of {MAX_DELEGATIONS} hops exceeded for ticket {self.ticket_id}."
            )
        if depth > MAX_DELEGATION_DEPTH:
            raise DelegationBudgetExceeded(
                f"Delegation depth {depth} exceeds max {MAX_DELEGATION_DEPTH} for ticket {self.ticket_id}."
            )
        pair = (from_agent, to_agent)
        if self._pair_counts[pair] >= MAX_REPEATS_PER_PAIR:
            raise DelegationBudgetExceeded(
                f"Cycle detected: {from_agent} -> {to_agent} repeated more than "
                f"{MAX_REPEATS_PER_PAIR} times for ticket {self.ticket_id}."
            )
        self._pair_counts[pair] += 1

        rec = DelegationRecord(from_agent=from_agent, to_agent=to_agent, reason=reason, depth=depth)
        self.delegations.append(rec)
        append_event(
            AuditEvent(
                run_id=self.run_id,
                ticket_id=self.ticket_id,
                agent=from_agent,
                event_type="delegation",
                detail=rec.model_dump(),
            )
        )
        return rec


def _new_agent(output_type, prompt_name: str, name: str) -> Agent:
    model = get_model()
    assert_model_is_compliant(model)
    return Agent(
        model,
        output_type=output_type,
        deps_type=AgentDeps,
        system_prompt=(_PROMPTS_DIR / f"{prompt_name}.md").read_text(encoding="utf-8"),
        toolsets=[new_campus_customs_toolset()],
        name=name,
    )


def _build_team(state: _RunState) -> dict[str, Agent]:
    """Build all 5 agents, wiring real bidirectional delegation tools between
    the Boss and each specialist."""

    boss = _new_agent(TicketResolution, "boss", "boss")
    inventory = _new_agent(InventoryFinding, "inventory", "inventory")
    accounting = _new_agent(AccountingFinding, "accounting", "accounting")
    facilities = _new_agent(FacilitiesFinding, "facilities", "facilities")
    customer_service = _new_agent(CustomerServiceFinding, "customer_service", "customer_service")

    specialists: dict[AgentRole, Agent] = {
        "inventory": inventory,
        "accounting": accounting,
        "facilities": facilities,
        "customer_service": customer_service,
    }

    def _deps_for(role: AgentRole) -> AgentDeps:
        return AgentDeps(run_id=state.run_id, ticket_id=state.ticket_id, agent_name=role)

    # Boss -> each specialist (depth 1)
    for role, specialist in specialists.items():

        def _make_delegate_tool(role: AgentRole = role, specialist: Agent = specialist):
            async def delegate(ctx: RunContext[AgentDeps], reason: str, question: str) -> str:
                f"""Delegate a question to the {role} specialist."""
                state.record("boss", role, reason, depth=1)
                append_event(AuditEvent(run_id=state.run_id, ticket_id=state.ticket_id, agent=role, event_type="agent_start", detail={"question": question}))
                result = await specialist.run(question, deps=_deps_for(role))
                append_event(AuditEvent(run_id=state.run_id, ticket_id=state.ticket_id, agent=role, event_type="agent_end", detail={"output": result.output.model_dump()}))
                return result.output.model_dump_json()

            return delegate

        boss.tool(name=f"delegate_to_{role}")(_make_delegate_tool())

    # Each specialist -> Boss (depth 2): a REAL, working escalation tool, not
    # just a prompt instruction. Bounded by the same hop cap, depth cap, and
    # cycle-detection as any other delegation.
    for role, specialist in specialists.items():

        def _make_escalate_tool(role: AgentRole = role):
            async def escalate_to_boss(ctx: RunContext[AgentDeps], reason: str, question: str) -> str:
                """Escalate a question that is outside this specialist's domain back to the Boss."""
                state.record(role, "boss", reason, depth=2)
                append_event(AuditEvent(run_id=state.run_id, ticket_id=state.ticket_id, agent="boss", event_type="agent_start", detail={"question": question, "escalated_by": role}))
                result = await boss.run(question, deps=_deps_for("boss"))
                append_event(AuditEvent(run_id=state.run_id, ticket_id=state.ticket_id, agent="boss", event_type="agent_end", detail={"output": result.output.model_dump(), "escalated_by": role}))
                return result.output.recommendation

            return escalate_to_boss

        specialist.tool(name="escalate_to_boss")(_make_escalate_tool())

    return {"boss": boss, **specialists}


async def run_ticket_team(ticket_id: int) -> TicketResolution:
    """Run the full, bidirectionally-connected agent team on one ticket.

    Returns the Boss's final TicketResolution, with the full delegation
    history (both directions) attached.
    """
    run_id = str(uuid.uuid4())
    state = _RunState(run_id=run_id, ticket_id=ticket_id)
    team = _build_team(state)
    boss = team["boss"]

    append_event(AuditEvent(run_id=run_id, ticket_id=ticket_id, agent="boss", event_type="agent_start", detail={}))
    try:
        result = await boss.run(
            f"Resolve ticket {ticket_id}. First call list_open_tickets or the relevant "
            f"ticket-specific MCP tool yourself to see the ticket's real details, then "
            f"delegate to the specialists you need (within your delegation budget), then "
            f"produce your final TicketResolution.",
            deps=AgentDeps(run_id=run_id, ticket_id=ticket_id, agent_name="boss"),
        )
    except DelegationBudgetExceeded as exc:
        append_event(AuditEvent(run_id=run_id, ticket_id=ticket_id, agent="boss", event_type="error", detail={"error": str(exc)}))
        raise

    append_event(
        AuditEvent(
            run_id=run_id,
            ticket_id=ticket_id,
            agent="boss",
            event_type="agent_end",
            detail={"output": result.output.model_dump(), "delegations": [d.model_dump() for d in state.delegations]},
        )
    )
    final = result.output.model_copy(update={"delegations": state.delegations, "run_id": run_id})
    return final
