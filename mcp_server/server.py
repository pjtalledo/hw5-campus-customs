"""FastMCP server exposing read-only Campus Customs database tools.

Always reads data/campus_customs_new.db (the working copy), never the
original data/campus_customs.db, regardless of the directory the server
is launched from.
"""

import os
import sqlite3
import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approvals  # noqa: E402

# CAMPUS_CUSTOMS_DB_PATH lets tests point this server at a disposable scratch
# copy instead of the real working database. Unset in normal operation, so
# normal behavior (always data/campus_customs_new.db) is unchanged.
DB_PATH = Path(
    os.environ.get("CAMPUS_CUSTOMS_DB_PATH")
    or (Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db")
)

mcp = FastMCP("campus-customs-db")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _row(cur, query: str, params: tuple = ()) -> dict | None:
    r = cur.execute(query, params).fetchone()
    return dict(r) if r is not None else None


def _rows(cur, query: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in cur.execute(query, params).fetchall()]


@mcp.tool
def get_ticket_101_restock_info() -> dict:
    """Retrieve inventory, vendor, and restocking information for Ticket 101
    (customer order for a Classic Bulldog Tee). Looks up the ticket's exact
    SKU/size, the available quantity at that SKU/size, the linked unpaid
    invoice (if any), and the supplying vendor's lead time.
    """
    con = _connect()
    try:
        cur = con.cursor()

        ticket = _row(cur, "SELECT * FROM tickets WHERE id = 101")
        if ticket is None:
            return {"error": "Ticket 101 not found in database."}

        inventory = _row(
            cur,
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (ticket["sku"], ticket["size"]),
        )

        invoice = None
        vendor = None
        if ticket["invoice_id"] is not None:
            invoice = _row(cur, "SELECT * FROM invoices WHERE id = ?", (ticket["invoice_id"],))
            if invoice is not None:
                vendor = _row(cur, "SELECT * FROM vendors WHERE id = ?", (invoice["vendor_id"],))

        return {
            "ticket": ticket,
            "requested_sku": ticket["sku"],
            "requested_size": ticket["size"],
            "requested_qty": ticket["qty"],
            "inventory_at_sku_size": inventory,
            "linked_invoice": invoice,
            "supplying_vendor": vendor,
        }
    finally:
        con.close()


@mcp.tool
def get_ticket_102_rent_and_cash_info() -> dict:
    """Retrieve lease, rent due date, and cash account information for
    Ticket 102 (rent notice). Returns the linked lease's rent amount and
    due date, the shop's current operating date, and the cash account
    balance so an agent can evaluate whether funds are sufficient.
    """
    con = _connect()
    try:
        cur = con.cursor()

        ticket = _row(cur, "SELECT * FROM tickets WHERE id = 102")
        if ticket is None:
            return {"error": "Ticket 102 not found in database."}

        lease = None
        if ticket["lease_id"] is not None:
            lease = _row(cur, "SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],))

        desk = _row(cur, "SELECT * FROM desk")
        cash_accounts = _rows(cur, "SELECT * FROM cash_accounts")

        return {
            "ticket": ticket,
            "lease": lease,
            "desk_date_today": desk["date_today"] if desk else None,
            "cash_accounts": cash_accounts,
        }
    finally:
        con.close()


@mcp.tool
def get_ticket_103_pricing_and_inventory_info() -> dict:
    """Retrieve inventory and pricing information for Ticket 103 (bulk hoodie
    discount request). Returns available quantity for the requested SKU/size
    (plus other sizes of the same SKU for context), unit cost, list price,
    and the resulting per-unit margin so an agent can evaluate a discount.
    """
    con = _connect()
    try:
        cur = con.cursor()

        ticket = _row(cur, "SELECT * FROM tickets WHERE id = 103")
        if ticket is None:
            return {"error": "Ticket 103 not found in database."}

        inventory_requested_size = _row(
            cur,
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (ticket["sku"], ticket["size"]),
        )
        inventory_all_sizes = _rows(
            cur,
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY size",
            (ticket["sku"],),
        )

        pricing = _row(cur, "SELECT * FROM pricing WHERE sku = ?", (ticket["sku"],))

        margin_per_unit = None
        margin_pct = None
        if pricing is not None:
            margin_per_unit = round(pricing["list_price"] - pricing["unit_cost"], 2)
            if pricing["list_price"]:
                margin_pct = round(margin_per_unit / pricing["list_price"] * 100, 2)

        return {
            "ticket": ticket,
            "requested_sku": ticket["sku"],
            "requested_size": ticket["size"],
            "requested_qty": ticket["qty"],
            "inventory_requested_size": inventory_requested_size,
            "inventory_all_sizes_for_sku": inventory_all_sizes,
            "pricing": pricing,
            "margin_per_unit": margin_per_unit,
            "margin_pct_of_list_price": margin_pct,
        }
    finally:
        con.close()


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List all tickets with status 'open', across all ticket types.

    Read-only. Lets the agent team discover what work exists without
    assuming ticket IDs 101/102/103 are the only ones that will ever exist.
    """
    con = _connect()
    try:
        return _rows(con.cursor(), "SELECT * FROM tickets WHERE status = 'open' ORDER BY id")
    finally:
        con.close()


@mcp.tool
def list_all_tickets() -> list[dict]:
    """List every ticket regardless of status, including whether each is
    'open' or 'resolved'. Read-only. Used by the dashboard's tickets view
    (Problem 7), which needs to show resolved tickets too, not just open
    ones (unlike list_open_tickets).
    """
    con = _connect()
    try:
        return _rows(con.cursor(), "SELECT * FROM tickets ORDER BY id")
    finally:
        con.close()


@mcp.tool
def get_shop_date() -> dict:
    """Return the shop's current operating date from the desk table.

    Read-only. Agents must use this value (not the OS clock) for any
    due-date or lead-time comparison.
    """
    con = _connect()
    try:
        row = _row(con.cursor(), "SELECT * FROM desk")
        return row or {"error": "desk row not found"}
    finally:
        con.close()


@mcp.tool
def check_vendor_payment_status(vendor_id: int) -> dict:
    """Check whether a vendor has any unpaid (status != 'paid') invoices.

    Read-only. A new shipment from this vendor must not be approved while
    any of their invoices remain unpaid. Returns the vendor record, its
    lead_days, and the list of open/unpaid invoices (empty if none).
    """
    con = _connect()
    try:
        cur = con.cursor()
        vendor = _row(cur, "SELECT * FROM vendors WHERE id = ?", (vendor_id,))
        if vendor is None:
            return {"error": f"Vendor {vendor_id} not found."}
        unpaid = _rows(
            cur,
            "SELECT * FROM invoices WHERE vendor_id = ? AND status != 'paid' ORDER BY id",
            (vendor_id,),
        )
        return {
            "vendor": vendor,
            "has_unpaid_invoices": len(unpaid) > 0,
            "unpaid_invoices": unpaid,
        }
    finally:
        con.close()


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Return the balance of a named cash account (default: 'checking').

    Read-only. Use before proposing or approving any payment to confirm
    sufficient funds exist.
    """
    con = _connect()
    try:
        row = _row(con.cursor(), "SELECT * FROM cash_accounts WHERE name = ?", (account,))
        return row or {"error": f"Cash account '{account}' not found."}
    finally:
        con.close()


@mcp.tool
def create_payment_approval_request(
    kind: str,
    ref_id: int,
    amount: float,
    account: str,
    reason: str,
    requested_by: str,
) -> dict:
    """Request human approval for a specific payment. Does NOT pay anything
    and does NOT grant any authorization by itself -- it only creates a
    'pending' record that a human must separately approve outside this
    agent system (via backend/approve_payment.py). Returns the pending
    request, including its approval_id, which record_approved_payment will
    later require.

    Validates the request is well-formed before creating it: positive
    amount, an existing cash account, and (for kind='invoice') an existing,
    not-already-paid invoice; (for kind='rent') an existing lease.
    """
    if amount <= 0:
        return {"error": "Refused: amount must be positive."}
    con = _connect()
    try:
        cur = con.cursor()
        acct = _row(cur, "SELECT * FROM cash_accounts WHERE name = ?", (account,))
        if acct is None:
            return {"error": f"Refused: cash account '{account}' not found."}
        if kind == "invoice":
            invoice = _row(cur, "SELECT * FROM invoices WHERE id = ?", (ref_id,))
            if invoice is None:
                return {"error": f"Refused: invoice {ref_id} not found."}
            if invoice["status"] == "paid":
                return {"error": f"Refused: invoice {ref_id} is already paid."}
        elif kind == "rent":
            lease = _row(cur, "SELECT * FROM leases WHERE id = ?", (ref_id,))
            if lease is None:
                return {"error": f"Refused: lease {ref_id} not found."}
        else:
            return {"error": f"Refused: unknown payment kind '{kind}' (expected 'invoice' or 'rent')."}
    finally:
        con.close()

    approval = approvals.create_pending_approval(
        kind=kind, ref_id=ref_id, amount=amount, account=account, reason=reason, requested_by=requested_by
    )
    return {
        "approval": approval,
        "note": (
            "This is PENDING, not approved. A human must run "
            "`python -m backend.approve_payment <approval_id> <name>` before "
            "record_approved_payment(approval_id) can succeed."
        ),
    }


@mcp.tool
def record_approved_payment(approval_id: str) -> dict:
    """Record a payment, but ONLY if a human has already approved it.

    This is the ONLY way money moves in this system, and it takes a single
    argument -- an approval_id previously created by
    create_payment_approval_request and then approved by a human via
    backend/approve_payment.py (never by any agent or tool). The kind,
    ref_id, amount, and account are read from that approval record itself,
    not from this call's caller, so a caller cannot substitute a different
    amount/account than what was actually approved.

    Refuses, with no database write, if: the approval does not exist; its
    status is not exactly 'approved' (covers a still-pending request, an
    already-consumed one -- blocking replay -- or a rejected one); the
    referenced invoice is already paid (blocking duplicate payment); or the
    payment would take the account balance negative. On success, the
    approval is atomically marked 'consumed' so it can never be spent again.
    """
    approval = approvals.get_approval(approval_id)
    if approval is None:
        return {"error": f"Refused: no such approval_id '{approval_id}'."}
    if approval["status"] != "approved":
        return {
            "error": (
                f"Refused: approval '{approval_id}' has status '{approval['status']}', not 'approved'. "
                "A pending request is not an authorization, and an approval can only be spent once."
            )
        }

    kind = approval["kind"]
    ref_id = approval["ref_id"]
    amount = approval["amount"]
    account = approval["account"]

    con = _connect()
    try:
        cur = con.cursor()
        acct = _row(cur, "SELECT * FROM cash_accounts WHERE name = ?", (account,))
        if acct is None:
            return {"error": f"Refused: cash account '{account}' not found."}
        new_balance = round(acct["balance"] - amount, 2)
        if new_balance < 0:
            return {
                "error": (
                    f"Refused: this payment of {amount} would take '{account}' "
                    f"from {acct['balance']} to a negative balance ({new_balance})."
                )
            }
        if kind == "invoice":
            invoice = _row(cur, "SELECT * FROM invoices WHERE id = ?", (ref_id,))
            if invoice is None:
                return {"error": f"Refused: invoice {ref_id} not found."}
            if invoice["status"] == "paid":
                return {"error": f"Refused: invoice {ref_id} is already paid (duplicate payment blocked)."}

        # Single-use: consume the approval before writing. If this raises
        # (e.g. a concurrent caller already consumed it), nothing is paid.
        approvals.consume_approval(approval_id)

        shop_date = _row(cur, "SELECT date_today FROM desk")
        paid_at = shop_date["date_today"] if shop_date else None

        try:
            cur.execute("BEGIN")
            cur.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (kind, ref_id, amount, account, paid_at, approval["approved_by"]),
            )
            cur.execute(
                "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                (new_balance, paid_at, account),
            )
            if kind == "invoice":
                cur.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
            con.commit()
        except Exception:
            con.rollback()
            raise

        payment_id = cur.lastrowid
        return {
            "payment": _row(cur, "SELECT * FROM payments WHERE id = ?", (payment_id,)),
            "new_account_balance": new_balance,
            "approval_id": approval_id,
        }
    finally:
        con.close()


@mcp.tool
def close_ticket(ticket_id: int, resolution_notes: str) -> dict:
    """Mark a ticket as resolved, with the agent team's resolution notes.

    State-changing (updates `status` and `notes` on an existing ticket
    row only); does not touch any other table. Fails if the ticket does
    not exist.
    """
    con = _connect()
    try:
        cur = con.cursor()
        ticket = _row(cur, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        if ticket is None:
            return {"error": f"Ticket {ticket_id} not found."}
        cur.execute(
            "UPDATE tickets SET status = 'resolved', notes = ? WHERE id = ?",
            (resolution_notes, ticket_id),
        )
        con.commit()
        return {"ticket": _row(cur, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))}
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()
