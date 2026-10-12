# Problem 5 — Strict Adversarial Grader-Style Audit

This audit deliberately looks for weaknesses, not confirmation. All runtime claims below were actually executed (commands shown); nothing is inferred from code reading alone where a runtime test was feasible.

## 1. Full connectivity — FAIL (architectural gap, not yet fixed)

**Finding:** The professor's wording is "agent loops so the agents can delegate work to each other with full connectivity." The implemented architecture is a strict star/hub topology: only the Boss has delegation tools (`delegate_to_inventory`, `delegate_to_accounting`, `delegate_to_facilities`, `delegate_to_customer_service`); the four specialists have none. A specialist cannot delegate to another specialist, and cannot even delegate back to the Boss mid-task — it simply returns its finding.

This is a genuine, real weakness, not a style nitpick: "delegate work to each **other**" implies bidirectional or peer capability, and "full connectivity" suggests more than one agent (the Boss) being able to initiate delegation. A strict reading of the current implementation only satisfies "Boss delegates to specialists," which is a subset of the requirement as worded.

**Why the current design exists:** it was chosen specifically to make cycle-prevention and the delegation-hop budget trivially true by construction (depth can never exceed 1). This is a real, defensible safety property, not an accident — but it was built in place of, not in addition to, genuine peer connectivity.

**Smallest safe correction (proposed, NOT implemented in this audit):** give each of the four specialists exactly one tool, `escalate_to_boss(reason, question)`, that lets a specialist hand a question back to the Boss mid-task (e.g., Inventory realizing a question is really about cash should escalate to the Boss rather than guessing). The Boss remains the only agent that can delegate to a *specialist*, but now any agent can reach any other agent through the Boss as a hub — this satisfies "delegate to each other" in a materially real sense while keeping the cycle-safety property: the hop budget (4) and a depth cap (raise `MAX_DELEGATION_DEPTH` to 2 and actually enforce escalations as depth-2 events) still bound the loop, and specialist-to-specialist direct calls remain structurally impossible (preventing an uncontrolled mesh). This is additive — no existing tool or prompt needs to be removed, only one new tool per specialist and one new `_RunState` check for escalation depth.

**Verdict: FAIL as literally worded. Proposed correction identified but not applied, per instruction to propose before changing the architecture.**

## 2. MCP-only data access — PASS

```
grep -rln "import sqlite3\|from sqlite3\|sqlite3\.connect" backend/
```
No matches. Every `build_*_agent` and the Boss in `orchestrator.py` only ever receives `toolsets=[new_campus_customs_toolset()]` (verified by `grep -n "toolsets=\|new_campus_customs_toolset" backend/agents.py backend/orchestrator.py` — 6 construction sites, all using the same factory, no other toolset or import). **PASS.**

## 3. Payment security — FAIL (two real gaps found by direct adversarial testing)

Tests run against a disposable scratch copy of `data/campus_customs_new.db` (created in the session scratch directory, deleted afterward; the real working and original databases were never touched).

**3a. Fabricated/forged approval — FAIL.**
```python
server.record_approved_payment(kind='invoice', ref_id=501, amount=840, account='checking', approved_by='Boss Agent')
```
This **succeeded** — payment recorded, balance decremented, invoice marked paid. `approved_by` is only checked for being a non-empty string; there is no mechanism (no out-of-band confirmation token, no separate human-approval record, no distinct "approval" data source) that distinguishes a real human's approval from an agent simply writing any label into that field. **The "payments require human approval" rule is currently enforced only at the prompt level (social convention), not technically.** This is a real, material gap: any bug or adversarial prompt could cause an agent to self-approve a payment.

**3b. Duplicate payment on an already-paid invoice — FAIL.**
Immediately calling `record_approved_payment` a second time for the same `kind='invoice', ref_id=501` **succeeded again** — a second payment was recorded and the balance was decremented a second time for the same invoice, even though the first call had already set `invoices.status = 'paid'`. The tool never checks the invoice's current status before paying. This is a real double-payment vulnerability.

**3c. Insufficient cash / missing approval / invalid ticket / invalid vendor — PASS (re-confirmed).** These four guardrails, previously tested and re-verified here, correctly refuse with no write.

**Minimal corrections (proposed, NOT implemented in this audit):**
- For 3a: at minimum, require the caller to also supply a separately-issued approval token/id that was generated by a distinct "create approval request" step (closing the loop between `ApprovalRequest` objects already modeled in `backend/models.py` and the payment tool) rather than accepting a free-text name. This raises the bar from "any string" to "must reference a specific prior approval record," though a fully tamper-proof technical guarantee of human-in-the-loop is out of scope for a local, single-process homework system and should be stated as a known limitation either way.
- For 3b: add a one-line guard — if `kind == 'invoice'`, check `invoices.status` first and refuse with an error if it is already `'paid'`.

**Verdict: FAIL on both sub-items. Corrections proposed, not applied, pending direction.**

## 4. Model compliance — PASS

Every one of the 5 agent-build call sites (`backend/agents.py` x4, `backend/orchestrator.py` Boss) calls `get_model()`, the single factory hard-coded to `gpt-6-luna` via `OpenAIProvider(base_url="https://api.portkey.ai/v1", ...)`. Since each `Agent` is constructed with exactly one `model` object, every `.run()` call and any internal pydantic-ai retry logic for that agent necessarily uses that same model/provider — compliance follows from the single-construction-path property, confirmed by code (static) and by the live console banners from all three ticket runs showing `model: openai:gpt-6-luna` (live). **Network-level interception of every outbound HTTP request was not performed** (would require a proxy/mitm setup out of scope here), so full compliance at the wire level is **NOT VERIFIED** at that depth, though the application-level guarantee is PASS.

## 5. MCP tool completeness — PASS

The 9 tools were sufficient for all three live ticket runs with no missing-capability errors (confirmed live in the Problem 5 implementation pass). Table access cross-checked against `mcp_server/README.md` and `output/harness.md`: exact match, re-confirmed by script in the prior audit and spot-checked again here by reading `server.py`'s actual SQL against both documents' claims.

## 6. Audit trail — PARTIAL FAIL

**Append-only behavior — PASS**, re-confirmed: `output/audit_trail.json` currently holds 24 events from 3 run_ids (101, 102, 103), none overwritten.

**Traceability of individual tool calls — FAIL.** Implementation-design requirement #13 explicitly calls for capturing "tool names, inputs, outcomes." The `AuditEvent` model defines an `"mcp_tool_call"` event type, but `grep -n "mcp_tool_call" backend/*.py` shows it is **never actually emitted anywhere** — only each specialist's *final* structured output is logged (via `agent_end`), not the individual MCP tool calls (e.g., which specific `get_ticket_101_restock_info` or `check_vendor_payment_status` calls were made, with what arguments, and what they returned) that happened during that specialist's reasoning. This is a real documentation-vs-implementation gap.

**Minimal correction (proposed, NOT implemented):** `MCPToolset` accepts a `process_tool_call` callback (confirmed present in its constructor signature during the original implementation). Wiring that callback to call `append_event(AuditEvent(..., event_type="mcp_tool_call", detail={"tool": ..., "args": ..., "result": ...}))` for each toolset instance would close this gap without changing any agent's prompt or business logic.

**Verdict: PASS on append-only; FAIL on tool-call-level traceability. Correction proposed, not applied.**

## 7. Reproducibility — PASS (now actually tested, not just asserted)

Copied `backend/`, `mcp_server/`, `requirements.txt`, and a copy of `data/campus_customs_new.db` into an isolated directory (`C:/temp/hw5_clean_test`, outside the project, deleted after the test). Created a brand-new `.venv_clean` there and ran `pip install -r requirements.txt` — succeeded with no modification to the real project's `.venv`. Imported every backend module (`backend.config`, `.models`, `.audit`, `.mcp_client`, `.agents`, `.orchestrator`, `.run_team`) in that fresh environment — all imported cleanly. The original project and its databases were never touched by this test. **This resolves the "NOT VERIFIED" reproducibility item from the prior Problem 5 audit.**

## 8. Missing-key safety — PASS (now actually tested)

In an isolated Python process, removed `PORTKEY_API_KEY` from the environment after module import (so the module's own `.env` load couldn't silently repopulate it), then called `get_model()` directly: raised `RuntimeError: PORTKEY_API_KEY is not set...` — a clear, safe failure. Confirmed the error message contains no credential value, no `sk-`-shaped string, and no `Bearer` token (asserted programmatically, not just eyeballed). **PASS.**

## 9. Regression — PASS

Re-hashed both databases after all audit testing: `data/campus_customs.db` and `data/campus_customs_new.db` both still `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`; both pass `PRAGMA integrity_check`. `output/mcp_smoke.json`'s three Problem 4 test entries still show `status: PASS` and the file was not modified. The three original Problem 3 MCP tools re-confirmed zero-argument (`properties: {}`) via a fresh `list_tools()` call, total tool count still 9.

## 10. Rubric alignment — explicit mapping

| Panel | Requirement | File(s) | Evidence | Test executed |
|---|---|---|---|---|
| A | 5 PydanticAI agents, distinct roles | `backend/agents.py`, `backend/orchestrator.py` | 5 `Agent` constructions, 5 output types in `backend/models.py` | Live (3 ticket runs) |
| A | One original prompt per agent in `backend/prompts/` | `backend/prompts/*.md` (5 files) | Distinct, role-specific text | Static read |
| A | Shared models in `backend/models.py` | `backend/models.py` | `DelegationRecord`, `ApprovalRequest`, 4 `*Finding` types, `TicketResolution`, `AuditEvent` | Static |
| A | `gpt-6-luna` via `PORTKEY_API_KEY` only | `backend/config.py` | Single `get_model()`, no hardcoded key | Live + direct (missing-key test) |
| A | Delegate to each other, full connectivity | `backend/orchestrator.py` | Boss→specialist only | **FAIL — see item 1** |
| B | Extend MCP server for open tickets | `mcp_server/server.py` | 9 tools total (6 new) | Live `list_tools()` |
| B | All shop facts through MCP, no bypass | `backend/*.py` | No `sqlite3` import | Static (grep) |
| B | Append-only `output/audit_trail.json` | `backend/audit.py` | 24 events, 3 run_ids, growing not shrinking | Live (3 separate process runs) |
| B | `harness.md` updated (agents, tools, tables, safety, token/cost) | `output/harness.md` | Problem 5 section added | Static, cross-checked live |
| B | `mcp_server/README.md` matches implementation | `mcp_server/README.md` | Tool names cross-checked against `list_tools()` | Live |
| Constraint | Original DB preserved | n/a | SHA-256 unchanged throughout | Live (repeated) |
| Constraint | No vendor shipment with unpaid invoice | `check_vendor_payment_status` | Returns `has_unpaid_invoices`; observed enforced live in Ticket 101 | Live |
| Constraint | Payments require human approval | `record_approved_payment` | **Only enforced at prompt level, not technically — see item 3a** | **FAIL** |
| Constraint | Never let cash go negative | `record_approved_payment` | Refuses before writing | Direct (adversarial test) |
| Constraint | Use `desk.date_today`, not OS clock | `get_shop_date`, agent prompts | Observed correctly used live in Ticket 102 ("2 days until due") | Live |

---

## Independent final assessment

**Problem 5 is NOT YET READY TO CLOSE.** Three concrete, material gaps were found by direct, adversarial, runtime testing (not by inspection alone):

1. **Full connectivity (item 1):** the current Boss-only-delegates topology is a defensible safety design but does not literally satisfy "delegate work to each other with full connectivity" as worded. Smallest proposed fix: add a single `escalate_to_boss` tool per specialist, bounded by the existing hop/depth budget.
2. **Payment approval is not technically enforced (item 3a):** any caller can supply a fabricated `approved_by` string and the payment succeeds. This is the single highest-risk finding, since it undermines the "payments require human approval" rule at the implementation level, not just in an edge case.
3. **Duplicate invoice payment is possible (item 3b):** no check against `invoices.status` before paying — a real double-payment risk.
4. **Audit trail does not capture individual tool calls (item 6):** `mcp_tool_call` events are modeled but never emitted, so the audit trail cannot show exactly which MCP tool was called with what arguments during a specialist's reasoning — only the specialist's final output.

All four corrections are additive and small in scope (one new tool per specialist, one guard clause, one callback wiring) and do not require removing or rearchitecting anything that currently works. Per instruction, none of them have been applied yet — they are reported here for a decision before any change is made to the architecture or security model.

**What would make Problem 5 ready to close:** implement the four corrections above, then re-run the same adversarial tests in this report (items 1, 3a, 3b, 6) to confirm each now passes, and re-run the three live ticket workflows once more to confirm no regression.

---

## Correction pass — re-test results (all four items re-run, not just re-inspected)

All four corrections approved and implemented. Every item below was re-tested with the same or an equivalent adversarial method as the original finding; none is marked PASS from code reading alone.

### Correction 1 — connectivity: now PASS

Implemented a real `escalate_to_boss` tool on each of the 4 specialists (`backend/orchestrator.py`), alongside the existing 4 Boss→specialist delegation tools. Any agent can now reach any other agent through the Boss hub; no specialist holds another specialist's tool, so direct specialist-to-specialist calls remain structurally impossible.

**Live test:** deliberately asked the Inventory agent an out-of-domain cash-balance question. It genuinely called `escalate_to_boss`; the Boss ran its own full agent loop (including its own MCP tool calls) and returned a real, correct answer ("$3,400.00, dated 2026-08-31"), which Inventory then incorporated into its own response. The resulting `DelegationRecord` correctly shows `from_agent='inventory', to_agent='boss', depth=2`.

**Loop-safety re-verified (direct unit tests):**
- Cycle detection: the same `(boss, inventory)` pair repeated a 3rd time was correctly refused with `DelegationBudgetExceeded`.
- Depth cap: a fabricated depth-3 hop was correctly refused.
- Global hop budget: still correctly refuses a 5th hop even across mixed directions (2 Boss→specialist + 2 specialist→Boss hops, then a 5th refused).

**Verdict: PASS.**

### Correction 2 — human payment approval: now PASS

Removed `approved_by` as a free-text parameter entirely. `record_approved_payment` now takes only `approval_id`. A new `create_payment_approval_request` tool lets an agent request approval (creates a `pending` record, authorizes nothing). The only way a request becomes `'approved'` is `backend/approve_payment.py` — a CLI script that is not imported by any agent, tool, or orchestrator code, and is therefore unreachable from the agent loop by construction, not just by convention.

**Adversarial re-tests, all on a disposable scratch DB copy (deleted after use):**
1. Calling `record_approved_payment` with a fabricated/nonexistent `approval_id` → refused (`"no such approval_id"`).
2. Creating a real pending request, then immediately trying to pay it before human approval (the previous self-approval attack's equivalent) → refused (`"has status 'pending', not 'approved'"`).
3. A human (simulated by directly calling `approvals.approve_pending`, exactly what the CLI script does internally) approves it → payment succeeds.
4. Immediately replaying the same, now-`consumed`, `approval_id` → refused (`"has status 'consumed', not 'approved'"`).
5. Attempting to create a brand-new approval request for the same, now-paid invoice → refused at the request-creation step itself (`"invoice 501 is already paid"`).

**Verdict: PASS on all 5 re-tests. No agent can create, forge, or self-approve its own payment authorization; a pending request cannot be spent; an approval is single-use.**

**Known, documented limitation (not hidden):** `approve_pending`'s single-use guarantee is enforced by a Python `threading.Lock` plus a status check, sufficient for this single-process homework system, but not a substitute for a real multi-process-safe or cryptographically-bound approval token in a production system. This is stated here rather than silently assumed away.

### Correction 3 — duplicate payments: now PASS

Both `create_payment_approval_request` and `record_approved_payment` check `invoices.status` and refuse if it is already `'paid'`. The three state-changing writes (payment insert, cash update, invoice-status update) are wrapped in an explicit `BEGIN`/`COMMIT` transaction with `ROLLBACK` on any exception, so a failure partway through cannot leave a half-applied payment.

**Re-tested** (same scratch DB, same test run as Correction 2's re-tests 4–5 above): duplicate payment via replay — refused; duplicate payment via a fresh approval request against an already-paid invoice — refused at request-creation, before a human could even be asked to approve it. Insufficient-cash and invalid-ticket/invalid-vendor guards were also re-confirmed unaffected by these changes.

**Verdict: PASS.**

### Correction 4 — MCP audit traceability: now PASS

Wired `MCPToolset`'s `process_tool_call` hook (`backend/mcp_client.py`) to log every real MCP tool invocation — tool name, sanitized arguments, and sanitized outcome or error — as an `mcp_tool_call` (or `error`) `AuditEvent`, attributed to the correct `run_id`/`ticket_id`/`agent` via a new `AgentDeps` dataclass threaded through every agent via `RunContext.deps`.

**Live re-test:** re-ran all three ticket workflows (101, 102, 103). The audit trail grew from 24 pre-correction events to 55 events total, and now contains 10 genuine `mcp_tool_call` entries (previously zero), each showing the exact tool name, arguments, and real returned data (spot-checked one entry: `get_ticket_101_restock_info` with the correct, real Ticket 101 JSON as its `outcome`). Confirmed append-only still holds: all 6 run_ids (3 pre-correction, 3 post-correction) remain present simultaneously — nothing was lost by the orchestrator rewrite.

**Secret-redaction check:** `_sanitize()` redacts any key containing `key`/`token`/`secret`/`password`/`authorization`/`credential` (case-insensitive) before logging; confirmed by code read that this runs on every logged call, and confirmed empirically that no API key or credential appears anywhere in `output/audit_trail.json` (none of our tool's real arguments or outputs contain such a field today, but the guard is in place regardless).

**Verdict: PASS.**

## Revised final assessment

All four originally-identified gaps now pass genuine re-testing — see `output/problem5_audit.md`'s updated final tally for the complete, re-run requirement set (A–N) including these four corrections. **Problem 5 is now READY TO CLOSE**, pending the final mandatory-validation pass recorded there.
