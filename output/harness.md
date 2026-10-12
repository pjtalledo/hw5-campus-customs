# Campus Customs Database Harness

Reference document for the Campus Customs shop database (`data/campus_customs.db`), built for Homework 5 before any agents, MCP server, backend, or dashboard are implemented.

## Table-by-table reference

### `desk`
Fields: `date_today` (TEXT, NOT NULL), `notes` (TEXT)

No primary key or foreign keys defined. Single-row table.

Why it matters: gives agents the shop's current "as of" date (`2026-08-31`), which is needed to judge whether things like rent or invoices are overdue.

### `tickets`
Fields: `id` (INTEGER, PRIMARY KEY), `type` (TEXT, NOT NULL), `requester` (TEXT, NOT NULL), `subject` (TEXT, NOT NULL), `sku` (TEXT), `size` (TEXT), `qty` (INTEGER), `lease_id` (INTEGER, FOREIGN KEY → `leases.id`), `invoice_id` (INTEGER, FOREIGN KEY → `invoices.id`), `status` (TEXT, NOT NULL), `notes` (TEXT), `created_at` (TEXT, NOT NULL)

Why it matters: this is the shop's inbox/work queue — every task an agent must triage or resolve starts as a row here. It links out to `leases` and `invoices`, and (via `sku`/`size`) implicitly to `inventory` and `pricing`, though those two are not enforced foreign keys in the schema.

### `inventory`
Fields: `sku` (TEXT, NOT NULL, part of PRIMARY KEY), `name` (TEXT, NOT NULL), `size` (TEXT, NOT NULL, part of PRIMARY KEY), `qty` (INTEGER, NOT NULL), `location` (TEXT, NOT NULL)

Primary key is the composite `(sku, size)`. No declared foreign keys — `sku` is not a formal FK to `pricing.sku`, but the two tables share the same SKU values in practice.

Why it matters: tells agents exactly what stock (and which size) is physically available to fulfill a customer order or bulk request.

### `pricing`
Fields: `sku` (TEXT, PRIMARY KEY), `unit_cost` (REAL, NOT NULL), `list_price` (REAL, NOT NULL)

No declared foreign keys. Relates to `inventory` and `tickets` only by matching `sku` values, not an enforced relationship.

Why it matters: gives agents the cost and standard sale price per SKU, which is required to evaluate any discount or price-override request without hurting margin.

### `vendors`
Fields: `id` (INTEGER, PRIMARY KEY), `name` (TEXT, NOT NULL), `specialty` (TEXT, NOT NULL), `lead_days` (INTEGER, NOT NULL)

No declared foreign keys (it is referenced by `invoices.vendor_id`).

Why it matters: tells agents who supplies what, and how long a reorder or reprint will take (`lead_days`) — important for deciding whether a vendor can meet a request in time.

### `leases`
Fields: `id` (INTEGER, PRIMARY KEY), `space_name` (TEXT, NOT NULL), `landlord` (TEXT, NOT NULL), `monthly_rent` (REAL, NOT NULL), `next_due` (TEXT, NOT NULL), `notes` (TEXT)

Referenced by `tickets.lease_id`.

Why it matters: holds the shop's rent obligations — the amount and due date an agent needs to check against `cash_accounts` before approving a rent payment.

### `cash_accounts`
Fields: `name` (TEXT, PRIMARY KEY), `balance` (REAL, NOT NULL), `date` (TEXT, NOT NULL)

No declared foreign keys. Not directly referenced by other tables via a formal FK, but conceptually funds every `payments` row.

Why it matters: this is the shop's bank balance. Any agent approving a payment (rent, invoice, refund) must check this table first to avoid overdrawing the account.

### `payments`
Fields: `id` (INTEGER, PRIMARY KEY), `kind` (TEXT, NOT NULL), `ref_id` (INTEGER), `amount` (REAL, NOT NULL), `account` (TEXT, NOT NULL), `paid_at` (TEXT, NOT NULL), `approved_by` (TEXT, NOT NULL)

No declared foreign keys in the schema, though `ref_id` appears intended to point at a `leases.id` or `invoices.id` depending on `kind`, and `account` at `cash_accounts.name` — none of this is enforced by the schema, only by convention. Table is currently empty (0 rows).

Why it matters: this is the audit trail of money actually paid out, including who approved it (`approved_by`) — central to the shop's human-approval rule for financial actions.

### `invoices`
Fields: `id` (INTEGER, PRIMARY KEY), `vendor_id` (INTEGER, NOT NULL, FOREIGN KEY → `vendors.id`), `amount` (REAL, NOT NULL), `due_date` (TEXT, NOT NULL), `status` (TEXT, NOT NULL), `description` (TEXT)

Referenced by `tickets.invoice_id`.

Why it matters: tracks what the shop owes its vendors and by when — an agent needs this, together with `cash_accounts`, to decide whether an invoice can be paid.

## Schema relationship summary

- `tickets.lease_id` → `leases.id` (enforced FK)
- `tickets.invoice_id` → `invoices.id` (enforced FK)
- `invoices.vendor_id` → `vendors.id` (enforced FK)
- `tickets.sku` / `inventory.sku` / `pricing.sku` share values but are **not** enforced foreign keys — matching must be done by the application/agent logic, not relied on as a database guarantee.
- `payments.ref_id` and `payments.account` are conventionally tied to `leases`/`invoices` and `cash_accounts.name`, but again not enforced by schema.

No relationships beyond what is declared in the `CREATE TABLE` statements (or directly observable by matching values) have been assumed.

## The three open tickets

### Ticket 101 — Customer order (Bulldog tee)
Requester **Tauhid Zaman** wants 1 unit of `CC-TEE-WHITE`, size **S**. Looking at `inventory`, that exact SKU/size combination has **qty = 0** — the shop is out of stock. The ticket is already linked to `invoice_id 501`, which is an open $840 invoice to vendor **Bulldog Print Co** for a "Rush reprint CC-TEE-WHITE S" — i.e., a reprint has already been ordered to cover this shortage. An agent resolving this needs: `inventory` (to confirm the stockout), `invoices` (to see the reprint is in progress and its cost/due date), `vendors` (to check `lead_days` for Bulldog Print Co, i.e. how soon the reprint arrives), and `cash_accounts` (to confirm the shop can cover the $840 invoice when it comes due).

### Ticket 102 — Rent notice
**Elm City Properties** is giving notice that rent is due in 2 days. The ticket links to `lease_id 1`, the Chapel Street shop lease: $2,400/month rent, next due **2026-09-02**. The shop's `desk.date_today` is **2026-08-31**, so the rent is indeed due in 2 days. An agent needs: `leases` (amount and due date), `cash_accounts` (current balance is $3,400 — enough to cover rent, but needs comparison), and eventually `payments` (to log the payment with an `approved_by` value once a human signs off, per the shop's approval rules).

### Ticket 103 — Price override (bulk hoodie discount)
**Yale AI Club** is requesting a bulk discount on 20 units of `CC-HOOD-NAVY`, size **M**. Checking `inventory`, only 8 units of that SKU/size are in stock (total across all sizes of that SKU is 32), so the order as requested exceeds available stock for that size. `pricing` shows unit cost $22.00 and list price $58.00, giving the margin an agent needs to evaluate how large a discount the shop can offer without selling at a loss. An agent needs: `inventory` (stock check), `pricing` (cost/margin check), and likely `vendors` (Bulldog Print Co does apparel reprints, in case more stock needs to be ordered to fulfill the full quantity).

## Problem 3 — MCP Server Tools

Three read-only FastMCP tools were implemented in `mcp_server/server.py`, each querying `data/campus_customs_new.db` directly (never the original `data/campus_customs.db`).

### `get_ticket_101_restock_info`
- **Database tables read:** `tickets`, `inventory`, `invoices`, `vendors`
- **Unlocks ticket:** 101
- **Why it's appropriate:** Ticket 101 needs to know whether the shop can fulfill an out-of-stock tee order, and this tool is the only one that joins the ticket's exact SKU/size against live `inventory` quantity, the linked unpaid reprint `invoices` row, and the supplying `vendors` lead time in one call.

### `get_ticket_102_rent_and_cash_info`
- **Database tables read:** `tickets`, `leases`, `desk`, `cash_accounts`
- **Unlocks ticket:** 102
- **Why it's appropriate:** Ticket 102 is a rent-due notice, so an agent must compare the `leases` due date against the shop's current `desk` date and the available `cash_accounts` balance before any rent payment can be approved, and this tool is the only one that returns all three together.

### `get_ticket_103_pricing_and_inventory_info`
- **Database tables read:** `tickets`, `inventory`, `pricing`
- **Unlocks ticket:** 103
- **Why it's appropriate:** Ticket 103 is a bulk discount request, so an agent needs the real stock available at the requested size and the real unit cost/list price margin to decide what discount is sustainable, and this tool computes that margin directly from the `pricing` table rather than assuming one.

See `mcp_server/README.md` for the server's purpose, database targeting strategy, and dependencies.

## Problem 5 — The Campus Customs Agent Team

### The five agents

| Agent | Responsibilities | Prompt file |
|---|---|---|
| **Boss** | Reads the ticket, decides which specialist(s) to consult, delegates with a bounded budget (max 4 delegation hops, max depth 2), resolves conflicts between specialist findings, and produces the final `TicketResolution` (summary, recommendation, whether human approval is required). | `backend/prompts/boss.md` |
| **Inventory** | Stock availability and shortfall quantification, vendor identification and lead time, and the unpaid-invoice shipment gate (no new shipment from a vendor with any unpaid invoice). | `backend/prompts/inventory.md` |
| **Accounting** | Real cash balances, real invoice/lease amounts, drafting `ApprovalRequest`-shaped payment proposals, and refusing to propose any payment that would take an account negative. Never calls or authorizes `record_approved_payment` itself. | `backend/prompts/accounting.md` |
| **Facilities** | Lease and rent facts, computing days-until-due using the shop's date (`desk.date_today`, never the OS clock), and flagging urgency. Does not judge affordability — that's Accounting's job. | `backend/prompts/facilities.md` |
| **Customer Service** | Customer order/discount feasibility against real stock and pricing, drafting a recommended response for human review. Never sends anything — there is no send action available to it. | `backend/prompts/customer_service.md` |

Architecture (revised after an adversarial audit — see `output/problem5_adversarial_audit.md`): `backend/orchestrator.py` builds all 5 agents with genuine **bidirectional** connectivity. The Boss has four delegation tools (`delegate_to_inventory`, `delegate_to_accounting`, `delegate_to_facilities`, `delegate_to_customer_service`), each of which actually runs that specialist's own `Agent.run()`. Each specialist, in turn, has a real `escalate_to_boss` tool that hands a question back to the Boss mid-task — a working tool, not just a prompt instruction (verified live: an Inventory agent asked an out-of-domain cash question genuinely called `escalate_to_boss`, which ran a full Boss agent loop and returned a real answer). This means any agent can reach any other agent through the Boss hub, while no specialist ever holds another specialist's delegation tool, so a direct specialist-to-specialist call remains structurally impossible. Loop safety is enforced in code (`backend/orchestrator._RunState`), not just by prompt: a hard cap of 4 total delegation hops per ticket, a depth cap (Boss→specialist = depth 1, specialist→Boss escalation = depth 2), and cycle detection (the same directed agent pair may not repeat more than twice) — all three unit-tested directly and confirmed to raise `DelegationBudgetExceeded` when violated. `backend/agents.py`'s standalone `build_*_agent()` functions remain available for testing a single specialist in isolation; the connected team used for real ticket resolution is built by `orchestrator._build_team()`.

### MCP tools (all 10, including the original 3 from Problem 3)

| Tool | Read/Write | Tables accessed | Purpose |
|---|---|---|---|
| `get_ticket_101_restock_info` | read | tickets, inventory, invoices, vendors | (Problem 3, unchanged) Ticket 101 restock lookup |
| `get_ticket_102_rent_and_cash_info` | read | tickets, leases, desk, cash_accounts | (Problem 3, unchanged) Ticket 102 rent/cash lookup |
| `get_ticket_103_pricing_and_inventory_info` | read | tickets, inventory, pricing | (Problem 3, unchanged) Ticket 103 pricing/inventory lookup |
| `list_open_tickets` | read | tickets | Lets the team discover open work generically, not just tickets 101–103 |
| `get_shop_date` | read | desk | The single source of "today" every agent must use instead of the OS clock |
| `check_vendor_payment_status` | read | vendors, invoices | Enforces the "no new shipment while a vendor invoice is unpaid" rule |
| `get_cash_balance` | read | cash_accounts | Generic cash lookup backing any payment-safety check |
| `create_payment_approval_request` | read (+ writes `output/pending_approvals.json`, not the SQLite DB) | cash_accounts, invoices, leases (validation only) | Lets an agent request human approval for a specific, fully-specified payment; creates a `pending` record, authorizes nothing |
| `record_approved_payment` | **write** | payments (insert), cash_accounts (update), invoices (update status if `kind='invoice'`) | The only tool that moves money. Takes only an `approval_id`; pulls kind/ref_id/amount/account from that approval record (not from the caller), refuses unless status is exactly `'approved'`, refuses if the invoice is already paid, refuses if the balance would go negative, and consumes the approval atomically so it cannot be replayed |
| `close_ticket` | **write** | tickets (update `status`, `notes`) | Marks a ticket resolved with the team's resolution notes; fails if the ticket doesn't exist |

All reads and all permitted writes live inside `mcp_server/server.py`. No agent or backend module imports `sqlite3` directly (confirmed by `grep`, re-run after the security correction pass) — every shop fact and every mutation goes through these MCP tools. The one human-only action in the whole system — actually approving a payment — lives in `backend/approve_payment.py`, a CLI script that is never imported by any agent, tool, or orchestrator code, so no agent can reach it.

### Safety section — real-world business guardrails

- **Unpaid-invoice shipment gate:** `check_vendor_payment_status` returns `has_unpaid_invoices`; the Inventory agent is instructed (and was observed, live, in Ticket 101) to refuse to treat a new shipment as viable while any invoice for that vendor is unpaid.
- **No negative cash:** `record_approved_payment` computes the resulting balance before writing anything and refuses the entire operation if it would go negative. Tested directly: a $999,999 payment attempt against a $3,400 balance was refused with no write.
- **Human approval is now technically enforced, not just a prompt convention (corrected after adversarial audit):** an agent can only call `create_payment_approval_request`, which creates a `pending` record and authorizes nothing. Only a human, running `backend/approve_payment.py` — a script no agent, tool, or orchestrator code ever imports or calls — can move a request to `'approved'`. `record_approved_payment` reads the payment's kind/ref_id/amount/account from the approval record itself (not from its caller), refuses unless the status is exactly `'approved'`, and atomically consumes the approval on success so it can never be reused. Adversarially tested: a fabricated non-human `approved_by` string, which previously succeeded, is no longer possible at all (the parameter doesn't exist anymore); attempting to pay a merely-`pending` approval is refused; attempting to replay an already-`consumed` approval is refused.
- **Duplicate payment is blocked (corrected after adversarial audit):** both `create_payment_approval_request` and `record_approved_payment` check `invoices.status` and refuse if an invoice is already `'paid'`. Adversarially tested: a second payment attempt against an already-paid invoice is refused, and a brand-new approval request for that same invoice cannot even be created.
- **Payment writes are atomic:** the payment insert, cash-balance update, and invoice-status update happen inside a single explicit `BEGIN`/`COMMIT` transaction with `ROLLBACK` on any exception.
- **Bounded, bidirectional delegation:** a hard cap of 4 total delegation hops, a depth cap (Boss→specialist=1, specialist→Boss escalation=2), and cycle detection (no directed agent pair may repeat more than twice) — all enforced in code (`_RunState.record`), not just in the prompt, and all three mechanisms unit-tested directly to confirm they correctly reject a violation.
- **No external communication:** no agent, tool, or prompt implements sending an email or placing a vendor call; Customer Service's prompt explicitly states there is no send action available to it.
- **No invented facts:** every agent prompt instructs re-checking the MCP tools rather than recalling a figure from memory; all live ticket runs (101, 102, 103) produced findings that matched the database exactly.
- **Database safety:** `data/campus_customs.db` (the original) is never opened for writing by any Problem 5 code; every live ticket run left `data/campus_customs_new.db` byte-identical to its pre-run state (no ticket was closed and no payment was recorded, because none of the runs received a human approval to do so — exactly per the rules). All adversarial payment/duplicate/replay tests ran exclusively against disposable scratch copies, never the real databases.

### Token usage and cost-control safeguards

- **Bounded tool surface:** each specialist agent only has the shared MCP toolset (9 tools) and no others; the Boss additionally has exactly 4 delegation tools. No unbounded tool proliferation.
- **Zero-argument original tools + minimal-argument new tools:** keeps each tool call's request/response payload small (the largest response, Ticket 103's, is a handful of short JSON objects).
- **Bounded delegation (max 4 hops, depth 1):** caps the number of specialist `Agent.run()` calls — and therefore model calls — per ticket at 5 (1 Boss turn plus up to 4 specialist runs), not an open-ended loop.
- **Concise, role-scoped system prompts:** each prompt is a few paragraphs focused only on that agent's own responsibilities, avoiding the token cost of one giant shared prompt.
- **`reasoning_effort="none"` for tool-calling turns:** set centrally in `backend/config.py` (required by this model/provider combination for function-calling to work at all on the chat-completions endpoint), which avoids extended hidden reasoning tokens on every turn.
- **Centralized model config:** every agent is constructed through `backend/config.get_model()`, which also runs `assert_model_is_compliant()` — a single place to audit (and to change, once) which model/provider every agent call bills against, preventing accidental silent use of a more expensive model.
## Problem 7 — Backend Routes (FastAPI)

`backend/main.py` exposes a FastAPI app over the existing orchestrator and MCP server — no duplicate agent logic, no second direct-SQLite layer. Start it from the `backend/` directory with `uvicorn main --reload --port 8000`; it is accessible at `http://localhost:8000` (interactive docs at `/docs`).

| Method | URL | Purpose |
|---|---|---|
| GET | `/tickets` | Return all three tickets and their current `open`/`resolved` status, read live through MCP's `list_all_tickets` tool (not cached, not hardcoded). |
| POST | `/tickets/{ticket_id}/run` | Validate the ticket id, run the existing `backend.orchestrator.run_ticket_team` agent workflow for real, and return the `run_id` plus the structured `TicketResolution`. |
| GET | `/events` | Return recent entries from the existing append-only `output/audit_trail.json`, chronologically, with optional `ticket_id`/`agent`/`run_id` filters and a `limit` (1–500). |
| POST | `/payments/{approval_id}/approve` | The only route that can move money. Requires a human-supplied `approver_name`; calls the Problem 5 `approvals.approve_pending` (never reachable from any agent tool) and then the real `record_approved_payment` MCP tool. See the trust-boundary note below. |
| GET | `/cash` | Return the real, current balance of a cash account (default `checking`) through MCP's `get_cash_balance` tool. |
| POST | `/admin/reset-working-database` | Reset only `data/campus_customs_new.db` from the pristine `data/campus_customs.db`. Requires `confirm: "RESET"` exactly; refuses while a run/approval/reset is already in progress; invalidates any still-pending or still-approved (unconsumed) approvals so they cannot be replayed against the freshly reset data; never touches the original database or `output/audit_trail.json`. |
| GET | `/approvals` | *(Added in Problem 8.)* Read-only listing of real approval requests from the existing Problem 5 approvals store, filtered by `status` (default `pending`). Added because the dashboard needs a safe way to discover genuine pending approvals without a new business-data layer or direct file/SQLite access from React. |

### Human-approval trust boundary (documented, not hidden)

`/payments/{approval_id}/approve` reuses the exact Problem 5 security mechanism unchanged — single-use approvals bound to an exact kind/ref_id/amount/account, re-validated against live cash and invoice status at payment time, and a human-only `approve_pending` function that no agent tool or prompt ever references. What this route does **not** provide is real user authentication: there is no login/session/signature behind `approver_name`, only CORS restricting the route to the local dashboard's own origin and the fact that the server binds to `localhost`. This is an explicit, acknowledged limitation of a local, single-user homework dashboard, not a claim that clicking a browser button is itself cryptographic proof of human intent.

### MCP tool count

11 tools total: the original 3 (Problem 3, unchanged, zero-argument) + 7 added during Problem 5 and its security-correction pass + 1 added in Problem 7 (`list_all_tickets`, read-only — needed because `list_open_tickets` only returns open tickets, and the dashboard needs resolved ones too). Problem 8 added no new MCP tools, only the read-only `GET /approvals` HTTP route (above), which reads the existing Problem 5 approvals store directly rather than SQLite.

## Problem 11 — Pre-Submission Audit

Full pre-publication audit performed (not yet published). Fixed: `.mcp.json` (was a personal absolute path, now portable relative paths), created the previously-missing `.env.example`, root `.gitignore`, root `README.md`, `output/resolved_tickets.json`, `output/resolved_board.html`, and `output/github_url.txt` (an explicit placeholder — no URL invented). Ran a full clean-clone reproducibility test in an isolated directory (fresh venv, fresh `npm ci`): backend imports, all 11 MCP tools, the exact `uvicorn main --reload --port 8000` command, `npm run build`, `npm run dev`, and the reset workflow all verified working. Security/secrets scan found no leaked credentials or personal paths in any publication-candidate file. Full findings, the Git staging whitelist/blacklist, and the final go/no-go verdict are in `output/problem11_pre_submission_audit.md`. **Publication has not occurred — awaiting explicit user approval.**

## Problem 9 — Genuine Three-Ticket Resolution Run

Ran the real system end-to-end from a freshly reset baseline. Baseline (post-`POST /admin/reset-working-database`): checking balance $3,400.00, all 3 tickets open. Executed `POST /tickets/{id}/run` for 101, 102, 103 in order (API-driven — real dashboard/browser interaction was attempted and is honestly reported as NOT VERIFIED, due to an unrelated environment tooling conflict, not a project defect). Two real, human-approved payments resulted (invoice 501, $840; lease 1 rent, $2,400), bringing the balance to $160.00. Ticket 102 was genuinely closed (`close_ticket`, verified via a fresh `GET /tickets`); Tickets 101 and 103 remain open, correctly, as PENDING HUMAN ACTION rather than being prematurely marked resolved. Full evidence, run IDs, and the requirement-by-requirement audit are in `output/problem9_audit.md`; the actual-vs-expected comparison per ticket is in `output/desk_tickets.html`'s now-populated Actual sections.

## Problem 8 — Agent Dashboard (React + Vite + TypeScript)

`frontend/` is a React + Vite + TypeScript app. Start it from `frontend/` with `npm run dev`; it serves at `http://localhost:5173` and talks to the real backend at `http://localhost:8000` (no mock data). See `output/design.md` for the full layout/visual-design rationale. Key files: `src/types.ts` (typed mirrors of the real backend responses), `src/api.ts` (typed fetch client, no hardcoded results), `src/agentMeta.ts` (per-agent color/label), `src/components/*` (TicketQueue, AgentTimeline, AgentRoster, CashPanel, ApprovalsPanel), `src/App.tsx` (orchestration, including real `GET /events` polling while a run is in flight — not simulated progress).

- **Append-only audit trail doubles as a usage record:** `output/audit_trail.json` records every `agent_start`/`agent_end`/`delegation`/`mcp_tool_call`/`error` event with a `run_id`, so repeated or runaway runs — including every individual MCP tool call, not just each specialist's final answer — are visible and attributable after the fact, not just in a live console. Tool-call arguments and results are sanitized before logging (any key containing "key"/"token"/"secret"/"password"/"credential" is redacted) so no credential material can leak into the trail even if a future tool ever returned one.
