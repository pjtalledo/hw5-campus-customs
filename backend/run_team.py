"""CLI entrypoint: run the Campus Customs agent team on one ticket.

Usage (from the Homework 5 project root, using the project's own venv):
    .venv/Scripts/python.exe -m backend.run_team 101
"""

from __future__ import annotations

import asyncio
import sys

from .orchestrator import run_ticket_team


async def _main(ticket_id: int) -> None:
    resolution = await run_ticket_team(ticket_id)
    print(resolution.model_dump_json(indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m backend.run_team <ticket_id>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(_main(int(sys.argv[1])))
