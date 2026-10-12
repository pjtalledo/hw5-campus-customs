# Campus Customs — AI Operations Desk

Homework 5, Yale SOM MGT 409 (AI Foundations for Managers). A five-agent PydanticAI team, backed by a FastMCP server and a FastAPI backend, resolves real operational tickets for a fictional campus shop, with human-gated payment approval and a React dashboard.

## Project overview

Campus Customs is a small shop with three open tickets: a customer order the shop can't currently fulfill, a rent notice, and a bulk-discount request. A team of five AI agents (Boss, Inventory, Accounting, Facilities, Customer Service) investigates each ticket using real database facts exposed through an MCP server, and can propose — but never execute — a payment. Only an explicit, out-of-band human action can actually move money. See `output/desk_tickets.html` for the full Expected-vs-Actual record of a genuine run, and `output/problem9_audit.md` / its gap-analysis addendum for why only one of the three tickets could be marked resolved.

## Architecture

```
React dashboard (frontend/, Vite + TypeScript)
        │  HTTP (localhost:8000)
        ▼
FastAPI backend (backend/main.py)
        │  real MCP client calls (not a direct DB import)
        ▼
FastMCP server (mcp_server/server.py) ── SQLite ── data/campus_customs_new.db
        ▲
        │  pydantic_ai.mcp.MCPToolset (genuine MCP, per agent)
PydanticAI agent team (backend/orchestrator.py, backend/agents.py)
```

All shop data access and the two permitted writes (`record_approved_payment`, `close_ticket`) happen inside the MCP server. No agent, backend route, or frontend component ever opens the SQLite file directly.

## The five agent roles

| Agent | Responsibility | Prompt |
|---|---|---|
| Boss | Reads tickets, delegates, resolves conflicts, produces the final recommendation. Bounded to 4 delegation hops, depth 2, max 2 repeats of any agent pair. | `backend/prompts/boss.md` |
| Inventory | Stock, restocking, vendor lead time, the unpaid-invoice shipment gate. | `backend/prompts/inventory.md` |
| Accounting | Cash, invoices, payment proposals. Can never authorize or execute a payment itself. | `backend/prompts/accounting.md` |
| Facilities | Lease, rent, due dates, using the shop's own date (never the OS clock). | `backend/prompts/facilities.md` |
| Customer Service | Customer requests, pricing, drafted (never sent) responses. | `backend/prompts/customer_service.md` |

Every specialist also has a real `escalate_to_boss` tool, so any agent can reach any other through the Boss hub — this is not just a diagram; see Ticket 103's genuine `accounting → boss` escalation in `output/desk_tickets.html`.

## MCP tool inventory (11 tools, `mcp_server/server.py`)

| Tool | Read/Write | Purpose |
|---|---|---|
| `get_ticket_101_restock_info` | read | Ticket 101 stock/invoice/vendor lookup |
| `get_ticket_102_rent_and_cash_info` | read | Ticket 102 lease/cash lookup |
| `get_ticket_103_pricing_and_inventory_info` | read | Ticket 103 stock/margin lookup |
| `list_open_tickets` | read | All open tickets |
| `list_all_tickets` | read | All tickets, any status |
| `get_shop_date` | read | The shop's own "today" (`desk.date_today`) |
| `check_vendor_payment_status` | read | Unpaid-invoice shipment gate |
| `get_cash_balance` | read | Real-time cash balance |
| `create_payment_approval_request` | writes a pending-approval record (not the shop DB) | Formally request a payment |
| `record_approved_payment` | **write** | The only tool that moves money — requires an already-`approved` `approval_id` |
| `close_ticket` | **write** | Marks a ticket resolved with notes |

Full per-tool documentation: `mcp_server/README.md`. Every route and its exact URL: `output/harness.md`.

## Required software

- Python 3.12+
- Node.js 20+ and npm
- A Portkey API key with access to `gpt-6-luna`

## Environment setup

1. Create a `.env` file containing `PORTKEY_API_KEY=<your key>`. `backend/config.py` looks for this file **one directory above this project root** (i.e. alongside this `hw5/` folder, matching how this project was developed inside a shared course directory). If you've cloned this repository standalone, either place `.env` one level above the repo, or edit `backend/config.py`'s `_ENV_PATH` to point at wherever you keep it. See `.env.example` for the variable name.
2. Create the virtual environment and install dependencies, from the repository root:
   ```bash
   python -m venv .venv
   .venv/Scripts/pip install -r requirements.txt      # Windows
   # .venv/bin/pip install -r requirements.txt        # macOS/Linux
   ```
3. Copy the original database to the working database for a clean run (see "Database reset" below) before the first run.

## Portkey configuration (no secrets here)

Every agent is constructed through the single `backend.config.get_model()` factory, which reads `PORTKEY_API_KEY` from the environment and always calls `gpt-6-luna` through `https://api.portkey.ai/v1`. No other model or provider path exists in the codebase — `assert_model_is_compliant()` raises if anything else is ever passed in.

## MCP configuration for Claude Code and Codex

A project-level `.mcp.json` is included, using **relative paths** (`.venv/Scripts/python.exe`, `mcp_server/server.py`) so it works from any clone location on Windows, as long as you run `claude` from the repository root. On macOS/Linux, change the command to `.venv/bin/python`.

For Codex, add this to `~/.codex/config.toml` (not included in this repo, since it's a user-level file):
```toml
[mcp_servers.campus-customs-db]
command = "<PATH_TO_THIS_REPO>/.venv/Scripts/python.exe"
args = ["<PATH_TO_THIS_REPO>/mcp_server/server.py"]
```
See `mcp_server/README.md`'s "Codex MCP Setup" section for full detail, including the single-use-approval safety note.

## Starting the MCP server (standalone, for inspection)

```bash
.venv/Scripts/python.exe mcp_server/server.py
```
Not required for normal dashboard use — the backend spawns it as needed.

## Starting the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```
Accessible at `http://localhost:8000` (interactive docs at `/docs`). CORS is restricted to `http://localhost:5173` and `http://localhost:3000` (and their `127.0.0.1` equivalents) — not a wildcard.

## Starting the React dashboard

```bash
cd frontend
npm install
npm run dev
```
Accessible at `http://localhost:5173`.

## Using the dashboard

1. Open `http://localhost:5173` with the backend already running.
2. The left column lists the three real tickets and their live status.
3. Click "Run agent team" on a ticket to execute the real PydanticAI/MCP workflow; the center column polls `GET /events` live while the run is in progress (labeled "Live — polling /events") and shows the Boss's final summary once it completes.
4. The right column shows the agent roster, the real checking balance (`GET /cash`), and any genuine pending approvals (`GET /approvals`).
5. To approve a payment: type your name and click "Approve payment." This calls `POST /payments/{approval_id}/approve` — the only route that can move money, and it is never reachable by any agent.

## Database reset (for a clean three-ticket run)

```bash
curl -X POST http://localhost:8000/admin/reset-working-database \
  -H "Content-Type: application/json" \
  -d '{"confirm":"RESET"}'
```
This copies `data/campus_customs.db` over `data/campus_customs_new.db` **only** — the original is never written to. It also invalidates (marks `rejected`) any still-pending or still-approved-but-unconsumed approvals, so a stale approval can never be replayed against freshly reset data. It refuses while a run/approval/reset is already in progress, and requires the exact string `"RESET"` (not `true` or `"yes"`) to reduce the chance of an accidental automated call matching.

### Alternative: plain filesystem copy (no server required)

If you want a clean working database **without** starting the backend at all — for example, to inspect the pristine starting state directly with a SQLite browser, or to reset before the backend has even been started for the first time — copy the file directly from the repository root:

```powershell
# Windows PowerShell
Copy-Item -Path data\campus_customs.db -Destination data\campus_customs_new.db -Force
```

```cmd
:: Windows Command Prompt
copy /Y data\campus_customs.db data\campus_customs_new.db
```

```bash
# macOS/Linux, or Git Bash on Windows
cp data/campus_customs.db data/campus_customs_new.db
```

**When to use which:**
- Use the **API route above** (`POST /admin/reset-working-database`) whenever the backend is already running — it is the only method that also safely invalidates stale pending/approved payment requests, so it should be preferred for a genuine "clean three-ticket run."
- Use the **plain filesystem copy** only when the backend is not running at all. It performs the identical file copy the API route performs internally, but it does **not** touch `output/pending_approvals.json` — if any approval requests exist from a prior session, they are left as-is and could reference a payment/invoice state that no longer matches the freshly-copied database. If you use the filesystem copy, also manually clear or review `output/pending_approvals.json` before approving anything new.
- **Either command irreversibly overwrites whatever is currently in `data/campus_customs_new.db`.** Do not run it if you have working-database state (e.g. a test payment) you still need — there is no undo beyond re-copying from the original again. **This command is documented here for your use and was not executed as part of preparing this repository.**

## Human approval workflow

1. An agent (typically Accounting) may call `create_payment_approval_request`, which only creates a `pending` record — it authorizes nothing.
2. A human reviews the request's exact kind, amount, account, and reason (visible via `GET /approvals` / the dashboard's Approvals panel), and either:
   - runs `python -m backend.approve_payment <approval_id> "<your name>"` from the command line, or
   - clicks "Approve payment" in the dashboard, which calls the same underlying mechanism through `POST /payments/{approval_id}/approve`.
3. Only then can `record_approved_payment(approval_id)` succeed — it re-validates cash sufficiency and invoice status, and consumes the approval so it can never be replayed.

**No agent, prompt, or tool anywhere in this codebase can call `approve_pending` or the approval/reset HTTP routes.** This was verified by `grep` across `backend/agents.py`, `backend/orchestrator.py`, `backend/prompts/*.md`, and `mcp_server/server.py` with zero matches (see `output/problem5_adversarial_audit.md` and `output/problem7_audit.md`).

## Safety guardrails

- Payments require a single-use, human-approved `approval_id` bound to an exact kind/amount/account — never a caller-supplied boolean or free-text name.
- No payment can make a cash account negative (checked at payment time, not just approval time).
- No invoice can be paid twice (checked via `invoices.status` at both request-creation and payment time).
- A new vendor shipment is never treated as viable while that vendor has any unpaid invoice.
- No MCP tool, agent, or route can place a vendor order, send a customer email, or otherwise act on the outside world — these capabilities simply do not exist in this system, by design.
- Delegation is bounded (max 4 hops, max depth 2, max 2 repeats of any agent pair) to prevent runaway loops.

## Actual three-ticket results (Problem 9, genuine run)

| Ticket | Outcome |
|---|---|
| 101 — Bulldog tee | **OPEN.** $840 invoice paid (human-approved); vendor now shipment-eligible, but no restock order exists as a system capability, so the customer still doesn't have the item. |
| 102 — Rent | **RESOLVED.** $2,400 rent paid (human-approved); independently verified fully satisfied before closing. |
| 103 — Bulk hoodie discount | **OPEN.** Only 8 of 20 requested units in stock; Accounting declined to authorize a discount and escalated to the Boss; no customer decision exists for this system to act on. |

Checking balance: $3,400.00 → $2,560.00 (−$840 invoice) → $160.00 (−$2,400 rent). Full evidence: `output/desk_tickets.html`, `output/resolved_tickets.json`, `output/resolved_board.html`, `output/problem9_audit.md`.

### Why Tickets 101 and 103 are OPEN / PENDING HUMAN ACTION, not RESOLVED

The Problem 9 assignment instructed running all three tickets "until each is resolved," but the same instruction's own Phase 3 explicitly anticipates and authorizes exactly this outcome:

> "if the current implementation cannot satisfy 'until each is resolved' without violating these safeguards, identify the minimum legitimate correction and explain the blocker before changing business logic" and "if a ticket cannot be resolved without a legitimate human action, report it as PENDING HUMAN ACTION rather than fabricating success." *(Problem 9 prompt, Phase 3, preserved verbatim in `AI_prompts.md`)*

**Agent-run completion is not the same as business resolution.** Both open tickets reached a point where every internally-actionable step was genuinely completed and verified — what remains is an action this system has no tool for and is explicitly forbidden from fabricating:

- **Ticket 101:** The $840 Bulldog Print Co invoice is paid (real, human-approved payment), and the vendor is confirmed shipment-eligible (`check_vendor_payment_status` returns zero unpaid invoices). **What's missing:** an actual restock order. No MCP tool exists to place a vendor order (`list_tools()` returns 11 tools, none of them create a purchase order or contact a vendor), and vendor contact is explicitly forbidden throughout this assignment. The 5-day vendor lead time cannot even begin until a human places that order outside this system. **The customer does not have the item** — closing this ticket would misrepresent that fact.
- **Ticket 103:** Real stock (8 of 20 requested units) and real margin figures ($22 cost / $58 list) were confirmed; Accounting correctly declined to authorize a discount and escalated the pricing decision to the Boss rather than guessing. **What's missing:** the customer's actual decision. This system has no customer-communication tool, and inventing Yale AI Club's acceptance of any specific offer was explicitly ruled out during development ("do not invent customer acceptance" — Problem 9 follow-up prompt). **No order has been confirmed** — closing this ticket would misrepresent that fact.

Neither ticket was left open due to a defect; both were investigated in depth (see `output/problem9_audit.md`'s gap-analysis addendum and `output/final_rubric_audit.md`) and the decision to leave them open, rather than close them with "shop-side action complete" framing, was made explicitly by the project's author rather than by the AI system unilaterally. No vendor order, customer acceptance, shipment, or fulfillment is claimed anywhere in this repository's deliverables for these two tickets.

## Known limitations

- Accounting reliably *recommends* a payment in its summary but does not always call `create_payment_approval_request` itself — a human currently has to notice the recommendation and formalize it.
- No vendor-ordering or customer-communication capability exists at all (by design, per the assignment's constraints) — this is the reason two of three tickets cannot reach genuine resolution through this system.
- `backend/config.py`'s `.env` lookup path assumes the original course directory layout (one level above the repo); a standalone clone needs either that same layout or a one-line edit.
- No dedicated frontend component/integration test suite exists — equivalent coverage comes from direct HTTP-level tests against the real backend (documented in `output/problem7_audit.md` and `output/problem8_audit.md`).
- Full browser-rendering verification of the dashboard could not be completed in the development environment used to build this project (an unrelated local tooling issue, not a defect in the app); see the manual browser-testing checklist in `output/problem11_pre_submission_audit.md`.

## Troubleshooting

- **"PORTKEY_API_KEY is not set"**: check your `.env` location against the note in "Environment setup" above.
- **`uvicorn main:app --reload --port 8000` fails with an import error**: make sure you're running it from inside the `backend/` directory, not the repo root.
- **MCP tool calls hang or fail**: confirm `.venv/Scripts/python.exe` (or `.venv/bin/python`) exists and `fastmcp` is installed; try running `mcp_server/server.py` directly to see the startup banner.
- **CORS errors in the browser console**: the frontend must run on `localhost:5173` or `localhost:3000` — the backend's CORS allowlist is intentionally narrow, not a wildcard.
- **Port already in use**: check for a leftover `uvicorn`/`vite` process from a previous run before starting a new one.

## Reproducibility

This project was verified end-to-end from a fully isolated clean clone (fresh virtual environment, `pip install -r requirements.txt`, `npm ci`) before submission: all backend modules imported cleanly, the MCP server listed all 11 tools, the exact `uvicorn main:app --reload --port 8000` command worked, `npm run build` and `npm run dev` both succeeded, and the database reset workflow was exercised safely on the isolated copy only. See `output/problem11_pre_submission_audit.md` for the full reproducibility report.
