# Campus Customs MCP Server

## Purpose
A FastMCP server that exposes database access over the Campus Customs shop's SQLite database to the Campus Customs agent team (Boss, Inventory, Accounting, Facilities, Customer Service agents — implemented in `backend/`, see `output/harness.md`'s Problem 5 section). Agents retrieve real, current facts instead of guessing or hardcoding business values, and the two permitted write operations (recording an approved payment, closing a ticket) are gated by validation inside this server rather than left to agent judgment.

## Database file
Always `data/campus_customs_new.db` (the working copy), resolved relative to this file's own location (`mcp_server/server.py`'s parent directory's parent, then `data/`), so the server finds the database correctly regardless of the directory it is launched from. The original `data/campus_customs.db` is never read or written by this server.

## Tools

Eleven tools total: the original three (read-only, zero-argument, unchanged since Problem 3), seven added or revised in Problem 5 to support the agent team securely, and one more (`list_all_tickets`) added in Problem 7 for the dashboard backend.

### `get_ticket_101_restock_info` *(Problem 3, unchanged)*
Reads: `tickets`, `inventory`, `invoices`, `vendors`.
Returns Ticket 101's exact SKU/size and requested quantity, the current `inventory` quantity at that SKU/size, the linked unpaid `invoices` record (if any), and the supplying `vendors` record (including lead time). Helps resolve Ticket 101, the out-of-stock Bulldog tee customer order, by showing whether a reprint is already in progress and how long it will take.

### `get_ticket_102_rent_and_cash_info` *(Problem 3, unchanged)*
Reads: `tickets`, `leases`, `desk`, `cash_accounts`.
Returns Ticket 102's linked `leases` record (monthly rent and next due date), the shop's current operating date from `desk`, and the full `cash_accounts` balances. Helps resolve Ticket 102, the rent notice, by giving an agent everything needed to check whether the rent due date has passed and whether cash on hand covers it.

### `get_ticket_103_pricing_and_inventory_info` *(Problem 3, unchanged)*
Reads: `tickets`, `inventory`, `pricing`.
Returns Ticket 103's requested SKU/size and quantity, the `inventory` quantity at that exact size plus all other sizes of the same SKU for context, the `pricing` record (unit cost and list price), and a computed per-unit margin and margin percentage. Helps resolve Ticket 103, the bulk hoodie discount request, by giving an agent the real stock constraint and the real margin available to discount from.

### `list_open_tickets` *(Problem 5)*
Reads: `tickets`. Read-only, no arguments.
Returns every ticket with `status = 'open'`, so the agent team can discover work generically rather than assuming only tickets 101–103 will ever exist.

### `list_all_tickets` *(Problem 7)*
Reads: `tickets`. Read-only, no arguments.
Returns every ticket regardless of status (open or resolved) — needed because `list_open_tickets` only returns open ones, and the Problem 7 dashboard backend's `/tickets` route must show resolved tickets too.

### `get_shop_date` *(Problem 5)*
Reads: `desk`. Read-only, no arguments.
Returns `desk.date_today`, the single source of "today" every agent must use for due-date and lead-time comparisons — never the operating system's clock.

### `check_vendor_payment_status(vendor_id)` *(Problem 5)*
Reads: `vendors`, `invoices`. Read-only.
Returns the vendor record plus every invoice for that vendor with `status != 'paid'`. Enforces the business rule that a new vendor shipment must never be approved while any invoice from that vendor remains unpaid.

### `get_cash_balance(account="checking")` *(Problem 5)*
Reads: `cash_accounts`. Read-only.
Returns the named cash account's balance and as-of date. Used before proposing or approving any payment.

### `create_payment_approval_request(kind, ref_id, amount, account, reason, requested_by)` *(Problem 5, added in the security correction pass)*
Reads: `cash_accounts`, `invoices`, `leases`. Writes: a pending-approval record in `output/pending_approvals.json` (not a database table).
Lets an agent **request** human approval for a specific payment. Validates the request is well-formed (positive amount, existing account, existing and not-already-paid invoice, or existing lease) before creating a `pending` record. Does **not** authorize or pay anything by itself — it is the only way a payment proposal can start down the approval path.

### `record_approved_payment(approval_id)` *(Problem 5 — the only tool that moves money; revised in the security correction pass)*
Writes: `payments` (insert), `cash_accounts` (balance update), `invoices` (sets `status='paid'` when `kind='invoice'`).
Takes a single `approval_id` — not a free-text approver name. The kind, ref_id, amount, and account are read from the approval record itself, so a caller cannot substitute different payment details than what was actually approved. Refuses, with no database write, unless the approval's status is exactly `'approved'` (blocking a still-pending request, a replay of an already-consumed approval, or a rejected one), the referenced invoice is not already paid (blocking duplicate payment), and the payment would not take the account negative. On success, the approval is atomically marked `'consumed'` so it can never be spent again, and the payment insert/cash update/invoice update happen inside a single transaction with rollback on error.

**How a payment actually gets approved:** an agent calls `create_payment_approval_request` to get an `approval_id`. A human then runs `python -m backend.approve_payment <approval_id> "<their name>"` — a separate CLI script that is never imported by any agent, orchestrator, or MCP tool — to move that request from `pending` to `approved`. Only then can `record_approved_payment(approval_id)` succeed. No agent, tool, or prompt can grant its own approval.

### `close_ticket(ticket_id, resolution_notes)` *(Problem 5)*
Writes: `tickets` (`status` and `notes` only).
Marks a ticket resolved with the agent team's resolution notes. Fails (no write) if the ticket does not exist.

## Tool behavior
- All reads use parameterized SQL (`?` placeholders) — no string-built SQL anywhere, including the write tools.
- No business values (prices, quantities, dates, amounts) are hardcoded; every value returned comes from a live database query.
- Of the 10 tools, 8 are strictly read-only (`create_payment_approval_request` only writes a JSON approval request, not the shop database). `record_approved_payment` and `close_ticket` are the only two tools that write to the SQLite database, and both validate before writing and refuse cleanly (returning an `error` field, no exception, no partial write) rather than ever leaving the database in an inconsistent state. `record_approved_payment`'s three writes happen inside a single transaction with rollback on error.
- No AI model calls are made by this server — all model calls happen in `backend/`, which connects to this server as an MCP client.
- See `backend/approve_payment.py` for the human-only approval mechanism; it is deliberately not part of this server's tool set.

## Dependencies
- `fastmcp` (installed in this project's `.venv`, pinned in `requirements.txt`)
- Python standard library `sqlite3` and `pathlib`

## Running
Not required for Problem 3 (per the assignment, the server does not need to be connected yet). If run manually:

```bash
.venv/Scripts/python.exe mcp_server/server.py
```

## Codex MCP Setup

For Problem 4, the professor explicitly permits **Claude Code, Codex, or Cursor** as the vibe coder used to connect to and test this MCP server. This section documents registration for **Codex**.

Codex does not use a project-level file like `.mcp.json`; it stores MCP server registrations in a user-level config file at `~/.codex/config.toml` (i.e. `C:\Users\<your-username>\.codex\config.toml` on Windows). This is outside the project repository by Codex's own design, so each grader must add this entry on their own machine before testing.

### 1. Register the server

Add the following block to `~/.codex/config.toml` (append it; do not remove any existing content in that file):

```toml
[mcp_servers.campus-customs-db]
command = "<PATH_TO_HOMEWORK_5>/.venv/Scripts/python.exe"
args = ["<PATH_TO_HOMEWORK_5>/mcp_server/server.py"]
```

Replace `<PATH_TO_HOMEWORK_5>` in **both** lines with the absolute path to this `Homework 5` project directory on your own machine (e.g. `C:/Users/yourname/.../Homework 5` on Windows, or `/home/yourname/.../Homework 5` on macOS/Linux). Forward slashes are used deliberately, even on Windows: Windows accepts forward slashes in paths, and this avoids a common pitfall where a plain single-backslash Windows path (e.g. copied directly from File Explorer) breaks TOML's string-escaping rules and fails to parse. Both `command` and `args` must point inside that same directory: `command` to the project's own `.venv/Scripts/python.exe` (or `.venv/bin/python` on macOS/Linux), and `args` to this project's `mcp_server/server.py`. No other line in `config.toml` needs to change.

### 2. Verify registration

From a terminal, confirm Codex sees the server:

```bash
codex mcp list
codex mcp get campus-customs-db
```

`codex mcp list` should show `campus-customs-db` with `Status: enabled`. `codex mcp get campus-customs-db` should show `transport: stdio` and the `command`/`args` you just set.

### 3. Genuine invocation requirement

A grader testing this server **must** run it through an actual MCP-capable Codex client (e.g. `codex exec` or the Codex VS Code extension) and have Codex invoke the three registered tools — `get_ticket_101_restock_info`, `get_ticket_102_rent_and_cash_info`, `get_ticket_103_pricing_and_inventory_info` — by name, over the real MCP protocol. Directly executing the Python functions in `server.py` (e.g. via a bare `python -c "...import server; server.get_ticket_101_restock_info()"` call) is **not** a substitute for a genuine MCP invocation and does not count as verifying this server.

### 4. Verified evidence

See [`output/mcp_smoke.json`](../output/mcp_smoke.json) for the actual recorded evidence: the exact natural-language prompt given to Codex for each ticket, the exact MCP tool name invoked, the real tool output returned over MCP, and the independent database verification for all three tools.
