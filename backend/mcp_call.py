"""Raw, audited MCP tool calls for the FastAPI backend itself.

The dashboard backend needs a few direct shop-data facts (ticket list, cash
balance) and one direct shop-data write (recording an approved payment)
that are not part of any agent's reasoning loop. Rather than import
mcp_server/server.py's functions directly (which would bypass the MCP
protocol) or open sqlite3 directly (which would bypass MCP entirely), this
module makes genuine MCP client calls via fastmcp.Client, exactly as a
real MCP client would -- just without an LLM agent in the loop, since no
model reasoning is needed for these simple pass-through calls.

Every call here is logged to output/audit_trail.json as an 'mcp_tool_call'
(or 'error') event, agent='system', so these backend-initiated tool calls
are just as traceable as agent-initiated ones.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

from .audit import append_event
from .mcp_client import _sanitize
from .models import AuditEvent

SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"


def _new_transport() -> PythonStdioTransport:
    # Explicitly inherit this process's full environment (rather than the MCP
    # client SDK's default curated subset) so that CAMPUS_CUSTOMS_DB_PATH /
    # CAMPUS_CUSTOMS_APPROVALS_PATH test overrides actually reach the
    # subprocess when set. This is our own trusted server code, not a
    # third-party tool, so full env inheritance is appropriate here.
    return PythonStdioTransport(script_path=SERVER_PATH, env=dict(os.environ), python_cmd=sys.executable)


async def call_tool(tool_name: str, run_id: str = "http", **kwargs: Any) -> Any:
    """Make one genuine MCP tool call against our FastMCP server and audit it."""
    try:
        async with Client(_new_transport()) as client:
            result = await client.call_tool(tool_name, kwargs)
        data = result.data
        append_event(
            AuditEvent(
                run_id=run_id,
                ticket_id=kwargs.get("ticket_id"),
                agent="system",
                event_type="mcp_tool_call",
                detail={"tool": tool_name, "args": _sanitize(kwargs), "outcome": _sanitize(data)},
            )
        )
        return data
    except Exception as exc:
        append_event(
            AuditEvent(
                run_id=run_id,
                ticket_id=kwargs.get("ticket_id"),
                agent="system",
                event_type="error",
                detail={"tool": tool_name, "args": _sanitize(kwargs), "error": str(exc)},
            )
        )
        raise
