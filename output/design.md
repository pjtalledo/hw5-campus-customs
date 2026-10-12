# Campus Customs — AI Operations Desk: Design Notes (Problem 8)

## Overall layout

A three-column "operations center" grid, not a chat window:

- **Left — Ticket Queue.** All three real tickets, each a card showing its id, open/resolved status pill, subject, the concrete request (e.g. "1 × CC-TEE-WHITE (S)"), and the requester. A "Run agent team" button per card triggers the real workflow. Clicking a card (not the button) selects it for viewing without re-running it.
- **Center — Agent Activity.** The selected ticket's live timeline: a chronological feed of real audit events (agent starts/ends, delegations, MCP tool calls), followed by the Boss's actual final summary and recommendation once the run completes.
- **Right — Operations rail.** Three stacked panels: the Agent Roster (who's on the team and what they do), the Checking Balance (live from the database), and Pending Approvals (real, actionable payment requests).

This mirrors how an actual operations desk is organized — a work queue, a live activity feed, and a status/control rail — rather than a single conversational thread, which would bury the delegation structure the professor specifically wants visible.

## How agents are visually differentiated

Each of the five roles has a fixed color and a two-letter badge, defined once in `src/agentMeta.ts` and reused everywhere (roster, timeline dots, delegation text):

| Agent | Color | Badge |
|---|---|---|
| Boss | Yale Blue `#00356B` | B |
| Inventory | Green `#2E7D32` | I |
| Accounting | Gold `#C7B14E` | A |
| Facilities | Purple `#6A4C93` | F |
| Customer Service | Terracotta `#B3541E` | CS |
| System (backend-initiated events) | Slate `#5A6472` | S |

Using the brand gold for Accounting specifically ties the "money" agent to the one non-blue brand color, reinforcing its role without needing a legend.

## How resolved tickets appear

A ticket's status pill reflects **the database's actual `status` field** (via `GET /tickets`), not whether a run happened. A finished agent run shows its summary and, if `requires_human_approval` is true, an explicit amber warning banner stating that the run finishing is not the same as the business problem being resolved — because in this system, no agent run resolves a ticket by itself; only an explicit `close_ticket` action (not currently wired into any agent prompt) would, and payments require separate human approval regardless. This was a deliberate design response to requirement 9: the UI never claims a ticket is "done" just because the HTTP call succeeded.

## Checking cash and financial changes

The Checking Balance panel always shows the real, current value from `GET /cash` — never a value computed client-side. After a human approves a payment, the panel re-fetches from the backend (not a local optimistic update) and briefly shifts the number to green with a soft pulse animation, so a real balance change is visually legible without becoming a distracting effect. Pending Approvals cards show the exact kind, amount, linked invoice/lease id, and the requesting agent's stated reason, with an explicit input for the approver's own name before the "Approve payment" button enables — reinforcing that a click alone isn't authorization.

## Post-launch correction: run-grouped Agent Activity view

A manual browser QA pass (opening the real dashboard in Edge) surfaced a genuine presentation gap my earlier automated testing had missed: a ticket that had been run many times during development (Ticket 101: 84 events across 8 runs; Ticket 103: 51 events across 5 runs) displayed all of its historical events as one long, run-agnostic list, with no way to tell where one run ended and the next began. The fix, in `frontend/src/runGrouping.ts` and an updated `AgentTimeline.tsx`, groups a ticket's full event history by its real `run_id` (every event already carries one — no backend change was needed), defaults to showing the most recent run, and adds a plain `<select>` run picker so a grader can inspect any earlier run without digging through raw JSON. A run's final Boss summary is extracted directly from that run's own real `agent_end` event rather than only being available for whichever run happens to be in memory from the current session. System-initiated actions (a human-approved payment, a ticket closed via `close_ticket`) are never folded into the run selector as if they were agent activity — they're shown in a separate "Ticket-level system actions" list, since they have no genuine run association. The same QA pass also showed that the UI let a ticket be re-run with a single click regardless of its status; `TicketQueue` now visually distinguishes a resolved ticket's rerun button and `App.tsx` requires an explicit confirmation before re-running one, since a rerun makes real, billable Portkey calls.

## Creative choices and why they improve the experience

- **Live/polling badge on the Agent Activity panel.** A pulsing green "Live — polling /events" indicator appears only while a run is actually in flight, so the user can tell real-time activity from a finished, static summary — directly serving the "don't simulate progress" requirement by being honest about what's live and what isn't.
- **Per-agent color-coded timeline dots.** Scanning the timeline by color lets a user follow which agent is acting without reading every line of text — useful once a ticket has produced several delegation hops.
- **Trust-boundary copy embedded in the UI itself**, not just in a document: the Approvals panel states outright that a click is not authentication, matching the backend's own documented limitation from Problem 7 rather than presenting a false sense of security.
- **Restrained, not decorative.** No chat bubbles, no avatars, no unnecessary motion — a single pulsing dot and a one-time balance-color pulse are the only animations, deliberately avoiding "excessive decoration" per the assignment's own guidance, while still feeling alive rather than static.
