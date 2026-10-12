"""The five Campus Customs agents, each wired to the real MCP server.

Every agent shares the same model (via config.get_model()) and connects to
the same FastMCP server (via mcp_client.new_campus_customs_toolset()) --
never a direct SQLite import, never a simulated tool response.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent

from .config import assert_model_is_compliant, get_model
from .mcp_client import new_campus_customs_toolset
from .models import (
    AccountingFinding,
    AgentDeps,
    CustomerServiceFinding,
    FacilitiesFinding,
    InventoryFinding,
    TicketResolution,
)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def build_inventory_agent() -> Agent[None, InventoryFinding]:
    model = get_model()
    assert_model_is_compliant(model)
    return Agent(
        model,
        output_type=InventoryFinding,
        deps_type=AgentDeps,
        system_prompt=_load_prompt("inventory"),
        toolsets=[new_campus_customs_toolset()],
        name="inventory",
    )


def build_accounting_agent() -> Agent[None, AccountingFinding]:
    model = get_model()
    assert_model_is_compliant(model)
    return Agent(
        model,
        output_type=AccountingFinding,
        deps_type=AgentDeps,
        system_prompt=_load_prompt("accounting"),
        toolsets=[new_campus_customs_toolset()],
        name="accounting",
    )


def build_facilities_agent() -> Agent[None, FacilitiesFinding]:
    model = get_model()
    assert_model_is_compliant(model)
    return Agent(
        model,
        output_type=FacilitiesFinding,
        deps_type=AgentDeps,
        system_prompt=_load_prompt("facilities"),
        toolsets=[new_campus_customs_toolset()],
        name="facilities",
    )


def build_customer_service_agent() -> Agent[None, CustomerServiceFinding]:
    model = get_model()
    assert_model_is_compliant(model)
    return Agent(
        model,
        output_type=CustomerServiceFinding,
        deps_type=AgentDeps,
        system_prompt=_load_prompt("customer_service"),
        toolsets=[new_campus_customs_toolset()],
        name="customer_service",
    )


def build_boss_agent() -> Agent[None, TicketResolution]:
    model = get_model()
    assert_model_is_compliant(model)
    return Agent(
        model,
        output_type=TicketResolution,
        deps_type=AgentDeps,
        system_prompt=_load_prompt("boss"),
        toolsets=[new_campus_customs_toolset()],
        name="boss",
    )
