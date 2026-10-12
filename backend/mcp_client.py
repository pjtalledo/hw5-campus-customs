"""Single factory for the real MCP toolset every agent shares.

All shop facts come through this one stdio connection to
mcp_server/server.py. Agents never query SQLite directly and never import
a database-access helper that bypasses MCP.

Every real tool call made through this toolset is logged to
output/audit_trail.json via `process_tool_call`, so the audit trail
captures genuine MCP execution (tool name, sanitized args, outcome or
error) -- not merely each agent's final response.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.mcp import CallToolFunc, FastMCPClient, MCPToolset

from .audit import append_event
from .models import AgentDeps, AuditEvent

SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"

_SENSITIVE_KEY_MARKERS = ("key", "token", "secret", "password", "authorization", "credential")


def _sanitize(value: Any) -> Any:
    """Redact anything that looks like a credential before it is ever logged."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if any(marker in str(k).lower() for marker in _SENSITIVE_KEY_MARKERS):
                out[k] = "[REDACTED]"
            else:
                out[k] = _sanitize(v)
        return out
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


async def _audit_process_tool_call(
    ctx: RunContext[AgentDeps], call_tool: CallToolFunc, tool_name: str, args: dict[str, Any]
):
    deps = ctx.deps
    try:
        result = await call_tool(tool_name, args)
        if deps is not None:
            append_event(
                AuditEvent(
                    run_id=deps.run_id,
                    ticket_id=deps.ticket_id,
                    agent=deps.agent_name,
                    event_type="mcp_tool_call",
                    detail={"tool": tool_name, "args": _sanitize(args), "outcome": _sanitize(result)},
                )
            )
        return result
    except Exception as exc:
        if deps is not None:
            append_event(
                AuditEvent(
                    run_id=deps.run_id,
                    ticket_id=deps.ticket_id,
                    agent=deps.agent_name,
                    event_type="error",
                    detail={"tool": tool_name, "args": _sanitize(args), "error": str(exc)},
                )
            )
        raise


def new_campus_customs_toolset() -> MCPToolset:
    """Create a fresh MCPToolset connected to our FastMCP server via real stdio MCP,
    with every real tool call audited through process_tool_call."""
    client = FastMCPClient(str(SERVER_PATH))
    return MCPToolset(client, process_tool_call=_audit_process_tool_call)
