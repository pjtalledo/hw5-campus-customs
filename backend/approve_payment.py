"""Human-only CLI to approve a pending payment request.

This script is the ONLY way a pending approval can become 'approved'. It is
never imported by backend/agents.py, backend/orchestrator.py, or
mcp_server/server.py's tool set -- no agent can call it, directly or
indirectly. A human runs this themselves, outside the agent loop, after
reviewing the pending request's exact kind/ref_id/amount/account.

Usage (from the Homework 5 project root):
    .venv/Scripts/python.exe -m backend.approve_payment <approval_id> "<your name>"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))
import approvals  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m backend.approve_payment <approval_id> <your_name>", file=sys.stderr)
        sys.exit(1)
    approval_id, approver_name = sys.argv[1], sys.argv[2]

    pending = approvals.get_approval(approval_id)
    if pending is None:
        print(f"No such approval: {approval_id}", file=sys.stderr)
        sys.exit(1)

    print("You are about to approve this exact payment:")
    print(f"  kind:    {pending['kind']}")
    print(f"  ref_id:  {pending['ref_id']}")
    print(f"  amount:  {pending['amount']}")
    print(f"  account: {pending['account']}")
    print(f"  reason:  {pending['reason']}")
    print(f"  requested_by (agent): {pending['requested_by']}")

    result = approvals.approve_pending(approval_id, approver_name)
    print(f"\nApproved by {approver_name}. approval_id={result['approval_id']} is now 'approved' "
          f"and may be spent exactly once by record_approved_payment.")


if __name__ == "__main__":
    main()
