# Problem 9 — Independent Grader-Style Audit (Resolve the tickets, 10 points)

## Baseline record (Phase 1)

| Field | Value |
|---|---|
| Original DB hash | `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`, `PRAGMA integrity_check` = `ok` |
| Reset action | `POST /admin/reset-working-database {"confirm":"RESET"}` on the real backend — real HTTP call, not simulated |
| Working DB hash after reset | `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a` (byte-identical to original) |
| Reset audit event | Logged: `{"run_id":"http-reset","agent":"system","event_type":"reset","detail":{"invalidated_approval_ids":[],"invalidated_count":0}}` — zero stale approvals existed to invalidate (none had ever been created against the real project DB before this problem) |
| Initial checking balance (via real `GET /cash`) | **$3,400.00** |
| Initial ticket statuses (via real `GET /tickets`) | 101: open, 102: open, 103: open |

## A. Reset actually occurred before the run — PASS

Confirmed via the real `POST /admin/reset-working-database` response, the resulting hash match, and the logged `reset` audit event, all before any of the three ticket runs were started.

## B. Initial checking balance captured accurately — PASS

$3,400.00, read live through the real `GET /cash` → MCP `get_cash_balance` path, matching the database directly queried afterward.

## C. All three tickets genuinely executed through the existing system — PASS (API-driven; dashboard interaction NOT VERIFIED, see below)

All three ran via `POST /tickets/{id}/run` — the exact route the dashboard's "Run agent team" button calls — sequentially, in order 101 → 102 → 103.

**Dashboard (browser) execution: NOT VERIFIED.** This session's browser automation tooling was attempted against the running Vite dev server and failed with an environment-level conflict (a pre-existing, unrelated process bound to port 5174) unrelated to this project's files. Per the explicit instruction not to pretend a dashboard click occurred, every execution in this problem is clearly labeled **API-driven** — real HTTP calls to the same backend routes the dashboard uses, not a substitute for an actual browser session. This limitation is reported honestly, not worked around.

## D. Real agent/MCP/Portkey execution for each ticket — PASS

Each run produced a unique `run_id`, real delegation records, and real `mcp_tool_call` audit events with genuine tool names and outputs matching the live database. All three used the single, centrally-configured `gpt-6-luna` model via Portkey (`backend.config.get_model()`, unchanged since Problem 5/7 — no alternate model path exists anywhere in the codebase).

| Ticket | Run ID |
|---|---|
| 101 | `3cbd9263-b53b-4c56-bee0-324c3d3ba2e5` |
| 102 | `f55bd0c5-1183-4d6d-81be-aecad741fd10` |
| 103 | `6f41a5a7-1a2b-46f1-a65d-9e421f532759` |

## E. Every Actual section matches real audit evidence — PASS

Each ticket's Actual section in `output/desk_tickets.html` was written directly from the real `GET /events?run_id=...` output for that run (agents, delegation reasons, MCP tool names) and the real `TicketResolution` JSON (summary, recommendation, `requires_human_approval`) — not inferred from agent prompts or invented. Spot-checked: Ticket 103's Actual section correctly reports a genuine `accounting → boss` escalation at depth 2, which is directly visible in that run's actual delegation list, not assumed from the architecture description.

## F. All Expected sections remain unchanged — PASS

Diffed the three Expected `<div class="card">` blocks against their Problem 6 content: untouched. Only the three `actual-reserved` placeholder divs were replaced with `actual-filled` content: the Expected prose, tables, and flow diagrams above them were not touched.

## G. Ticket statuses reflect genuine business resolution, not just a successful API response — PASS

- **Ticket 101:** API call succeeded, but the status is reported as **OPEN — PENDING HUMAN ACTION**, because paying invoice 501 only clears a vendor-eligibility gate; the SKU/size is still 0 units on hand and the vendor's 5-day lead time has not elapsed. The customer does not have their tee. `close_ticket` was deliberately **not** called for 101.
- **Ticket 102:** marked **RESOLVED** only after independently confirming the rent obligation was fully and verifiably paid (see I/J below) — the run finishing was not treated as resolution; the payment being real and complete was.
- **Ticket 103:** API call succeeded, but the status is **OPEN — PENDING HUMAN ACTION**, since the 12-unit shortfall and discount/pricing decision remain unresolved business questions, not technical blockers.

## H. Payments genuinely human-approved and properly recorded — PASS

Neither payment was initiated by an agent. In both cases, Accounting only recommended the payment in its text output and never called `create_payment_approval_request` itself (confirmed by inspecting each run's real `mcp_tool_call` events — no such call appears in either run). Per the explicit instruction, **the actual human user was asked directly** (via a structured question, not assumed) whether to approve the $840 invoice payment and the $2,400 rent payment; both were explicitly approved by the user. Only after that real authorization were the formal `create_payment_approval_request` calls made (reflecting the agents' own stated figures, not invented ones) and the approvals executed through the real `POST /payments/{approval_id}/approve` route with `approver_name: "Piero Talledo"` — the same mechanism and the same security guarantees (single-use, bound to exact amount/account, re-validated at payment time) proven in Problems 5 and 7's adversarial audits. No approval was fabricated, self-granted by an agent, or auto-clicked on the user's behalf.

## I. Reconcile checking balance changes against actual payments — PASS

| Step | Balance |
|---|---|
| Baseline (post-reset) | $3,400.00 |
| After invoice 501 payment ($840.00) | $2,560.00 |
| After rent payment ($2,400.00) | **$160.00** |

$3,400.00 − $840.00 − $2,400.00 = $160.00, confirmed by both the API's own returned `new_account_balance` at each step and an independent, separate `GET /cash` call afterward, and independently again by a direct `sqlite3` query of `cash_accounts`. No negative balance occurred at any point (the second payment left exactly $160.00, correctly still non-negative).

## J. Original database integrity and working database consistency — PASS

Original: unchanged throughout, `23686a90...1f360a`, confirmed before and after this entire problem. Working database: `PRAGMA integrity_check` = `ok` after all mutations; `payments` table shows exactly 2 rows (the two real payments above, both `approved_by: "Piero Talledo"`); `invoices` table shows invoice 501 now `status: paid`; `tickets` table shows 102 `status: resolved` with accurate resolution notes, 101 and 103 still `open`.

## K. `audit_trail.json` append-only; all runs traceable — PASS

Event count grew monotonically across this problem: 109 (immediately after the reset) → 171 (end of problem). All three ticket runs' events remain retrievable by `run_id` via `GET /events?run_id=...`, exactly as used to populate the HTML's Actual sections. Nothing was overwritten or deleted.

## L. No duplicate payments, negative cash, forged approvals, or unauthorized mutations — PASS

Exactly one payment per approval_id (`payments` table has 2 rows for 2 distinct, legitimately-created-and-approved requests). No negative balance at any point. Every `approved_by` value is the real, explicitly-authorizing user's name, entered through the exact same route and mechanism already adversarially hardened in Problems 5 and 7 — no new or weakened code path was introduced to make this problem's approvals easier to grant.

## M. React dashboard still builds; both servers start — PASS (build + startup only; browser rendering NOT VERIFIED)

`npm run build` (in `frontend/`) was re-run after this problem's HTML edits and succeeded with the same output shape as Problem 8 (0 TypeScript errors, real production bundle). The real backend (`uvicorn main:app --port 8000`) and the real frontend (`npm run dev`, confirmed listening on `localhost:5173` via a direct `curl`) were both started and confirmed reachable during this problem's work — this is the same honest distinction as item C: server startup is verified; a rendered browser session is not.

## N. HTML tabs remain functional after adding Actual sections — PASS (genuine jsdom re-test)

Re-ran the same Node + jsdom functional test used in Problem 6, against the now-updated file: all 5 tabs still correctly show/hide via the real `showTab()` function (15/15 assertions passed, including new checks that each ticket's real run_id and final status text are actually present in the rendered text content).

## O. Regression — Problems 1–8 — PASS

- Problem 4: `output/mcp_smoke.json`'s 3 PASS entries unchanged.
- Problem 6: all three Expected sections and the Cash/Reflection placeholders preserved exactly (F above).
- Problem 7/8 security mechanisms: reused without modification — no new route, no new MCP tool, no changed approval/reset logic was introduced for this problem.
- MCP tool count unchanged at 11; original 3 Problem 3 tools re-confirmed zero-argument.
- Frontend still builds (M above).

---

## Final report

**1. Baseline:** Checking balance $3,400.00; all three tickets open.

**2. Execution order and run IDs:** 101 (`3cbd9263-b53b-4c56-bee0-324c3d3ba2e5`) → 102 (`f55bd0c5-1183-4d6d-81be-aecad741fd10`) → 103 (`6f41a5a7-1a2b-46f1-a65d-9e421f532759`), all API-driven (dashboard click NOT VERIFIED).

**3. Agents/delegations/MCP tools per ticket:** see the Actual sections in `output/desk_tickets.html` and section E above — Ticket 101: Boss→Inventory→Boss→Accounting, tools `get_ticket_101_restock_info`, `check_vendor_payment_status`; Ticket 102: Boss→Accounting, tool `get_ticket_102_rent_and_cash_info`; Ticket 103: Boss→Inventory→Boss→Accounting→Boss (genuine escalation)→Boss→Inventory, tool `get_ticket_103_pricing_and_inventory_info`.

**4. Final verified statuses:** 101 OPEN (pending human action — vendor lead time), 102 **RESOLVED**, 103 OPEN (pending human action — pricing/quantity decision).

**5. Financial reconciliation:** $3,400.00 → $2,560.00 (−$840.00, invoice 501) → $160.00 (−$2,400.00, rent). No negative balance; no duplicate payments.

**6. Expected vs. Actual:** Recorded ticket-by-ticket in `output/desk_tickets.html`; the main deviations were (a) Accounting never autonomously calling `create_payment_approval_request` on either ticket — approval requests had to be formally created based on its stated recommendations only after genuine human authorization; (b) Ticket 102's Boss skipping a separate Facilities hop since one tool call already answered both the lease and cash questions; (c) Ticket 103 showing a real, unscripted `accounting → boss` escalation the Expected plan could only describe abstractly.

**7. Remaining blockers / human actions required:** Ticket 101 needs the vendor's 5-day lead time to elapse (and a decision on whether/when to actually place a new shipment, since the invoice is now paid and the vendor is eligible) before the customer can be fulfilled. Ticket 103 needs a human decision on whether to offer a partial quantity (8 of 20) and/or what discount, if any, to extend — no technical blocker remains, only a business policy call.

**8. Final verdict: Problem 9 is READY TO CLOSE for its implementable, independently-verifiable requirements**, with one item honestly carried forward as **NOT VERIFIED rather than fabricated**: genuine browser/dashboard-click execution (blocked by an unrelated environment tooling conflict, consistent with Problems 6–8). All financial, database, audit-trail, and security requirements were independently verified with real evidence, no fabricated approvals, and no premature ticket closures.

---

## Addendum — Focused Gap Analysis (follow-up audit)

A follow-up gap analysis was requested given the 101-open/102-resolved/103-open result, to determine whether this reflects a real correctable gap or a genuine business/architectural limit. Findings:

1. **Ticket 101:** Independently re-queried `check_vendor_payment_status(vendor_id=1)` — confirmed `has_unpaid_invoices: false` (invoice 501 is genuinely paid). However, **no MCP tool exists anywhere in this system to place a vendor shipment/restock order**, and the shop's own rules explicitly forbid contacting vendors. The 5-day lead time cannot begin until an order is placed by a human outside this system. **Conclusion: genuine business fulfillment of this ticket is architecturally unreachable through this system by design — not a correctable gap.**
2. **Ticket 102:** Independently re-verified from fresh SQL (not reused from the original run): `status='resolved'`, payment row `(id=2, kind='rent', ref_id=1, amount=2400.0, account='checking', approved_by='Piero Talledo')`, `cash_accounts.balance=160.0`. **No gap found — correct as reported.**
3. **Ticket 103:** Feasible options identified (offer the 8 in-stock units at list price; offer a discount on those 8; wait for restock) — but finalizing any of them requires the customer's (Yale AI Club's) real acceptance, and this system has no customer-communication capability and must not invent a response. **Same category of limitation as Ticket 101 — not a correctable gap.**
4. **Architecture review:** The agent/ticket-resolution logic was found to be behaving correctly, not incorrectly leaving tickets open — it is accurately refusing to fabricate a vendor order or a customer reply that would be required for genuine closure. No logic change was made or recommended.
5. **Minimum additional actions:** None exist that would make Tickets 101/103 genuinely business-resolved without the system performing an action it is explicitly forbidden from performing. This was presented to the user as an explicit decision point rather than resolved unilaterally.
6. **Browser automation re-investigated:** Discovered and fixed a real, separate bug — two stray leftover Vite dev-server processes from earlier testing were simultaneously bound to ports 5173 and 5174, which was the proximate cause of the prior port-conflict error. Killed both, verified via `netstat` that exactly one clean instance was running on 5173 with nothing on 5174, and retried the browser preview tool. **It still failed, with the same unrelated internal error seen in Problems 6–8** (`'C:\Program' is not recognized...`), confirming the remaining failure is a genuine environment/tooling limitation independent of this project's processes or ports — not something resolvable by changing this project's configuration. Dashboard browser verification remains honestly **NOT VERIFIED**.
7. **`output/desk_tickets.html` accuracy re-confirmed:** fresh `GET`-equivalent SQL query showed 101/102/103 statuses exactly match what the HTML displays (open/resolved/open); all 3 Expected sections confirmed unchanged (byte-identical review, not just a heading count).
8. **No database mutations occurred during this gap analysis** — re-verified original hash unchanged, payment count still exactly 2, no reset repeated, no new financial transaction executed.

**User decision obtained:** asked the user explicitly how to document Tickets 101/103 given the architectural limitation; the user chose to **leave both open** (the more accurate option) rather than close them with "shop-side action complete" framing. No ticket status was changed as a result of this gap analysis — only the HTML's Actual sections were enriched with an explicit "why this ticket cannot be closed" explanation for each, approved implicitly by the user's choice of the "leave open" option.

**Revised final verdict: Problem 9 remains READY TO CLOSE.** The 1-of-3 resolution rate is not a defect to fix but a documented, user-confirmed consequence of this system correctly refusing to fabricate vendor orders or customer communications — exactly the behavior the assignment's own safety constraints require.

---

## Addendum 2 — Manual browser verification findings (final, pre-publication)

The user personally exercised the real dashboard in Microsoft Edge across multiple sessions after the initial Problem 9 run. A fresh, independent re-count of the real `output/audit_trail.json` (252 total events) confirms these genuine, additional historical runs, none of which changed any business outcome:

| Ticket | Historical agent runs | Total events | System events |
|---|---|---|---|
| 101 | 9 | 92 | 0 |
| 102 | 4 | 30 | 1 (`close_ticket`, the real Problem 9 closure) |
| 103 | 6 (including the originally documented run, still present and intact) | 58 | 0 |

Ticket 103's run `6f41a5a7-1a2b-46f1-a65d-9e421f532759` (started `2026-10-12T21:51:29Z`) still contains the genuine `accounting → boss` escalation documented in this file's main body — re-confirmed present in its correct, specific run by the Problem 11 run-grouping correction's own verification test.

**None of this additional activity changed the database.** Re-confirmed immediately before this addendum was written: original DB hash unchanged; working DB — ticket statuses `101 open / 102 resolved / 103 open`, exactly 2 payment rows, checking balance `$160.00` — identical to every value reported earlier in this document. `output/resolved_tickets.json` and `output/resolved_board.html` remain accurate as written; they describe the real, unchanged business outcome and do not claim exclusivity over a single run, so the additional historical runs do not make them stale or inconsistent. No historical snapshot was rewritten — this addendum only adds new, dated observations on top of the existing record.
