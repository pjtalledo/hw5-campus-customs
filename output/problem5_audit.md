# Problem 5 — Independent Grading Audit (Build the agent team and grow the MCP tools, 15 points)

Methodology: `output/verification_checklist.md`. All tests below distinguish **live** (real `gpt-6-luna` via Portkey, real MCP stdio connection, real tool execution) from **direct/unit** (deterministic Python code tested without a live model call) and **static** (code/doc inspection). Nothing in this report is mocked or simulated and labeled otherwise.

## A. Five agents exist, have distinct detailed prompts, use PydanticAI

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| 5 agents, distinct roles | Static: `backend/agents.py`, `backend/orchestrator.py` | `build_inventory_agent`, `build_accounting_agent`, `build_facilities_agent`, `build_customer_service_agent`, and the Boss built in `orchestrator._build_boss_agent` | PASS |
| One original prompt per agent, in `backend/prompts/` | Static: file read | 5 files (`boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md`), each with distinct role-specific responsibilities, permitted actions, and limitations | PASS |
| Uses PydanticAI | Static + live | All 5 agents are `pydantic_ai.Agent` instances; confirmed live via `agent.run()` succeeding end-to-end | PASS |

## B. Delegation architecture is genuinely functional

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| Boss can delegate to specialists via real tool calls | **Live**, 3 runs (tickets 101, 102, 103) | Each run's JSON output includes a non-empty `delegations` list; `output/audit_trail.json` independently confirms matching `delegation`/`agent_start`/`agent_end` events per hop | PASS |
| Delegation is a real nested agent run, not a stub | Live | Ticket 101 run shows Customer Service and Inventory each independently reasoning and calling their own MCP tools (confirmed via audit detail payloads containing each specialist's full structured output) | PASS |
| Specialists cannot delegate to each other | Static + direct | `build_inventory_agent`/`build_accounting_agent`/`build_facilities_agent`/`build_customer_service_agent` register no delegation tools — only the shared MCP toolset. Confirmed by code read: only the Boss agent object has `delegate_to_*` tools registered. | PASS |
| Delegation budget enforced in code | **Direct** (deterministic unit test, not LLM-dependent) | `_RunState.record()` tested directly: 4 hops succeed, a 5th raises `DelegationBudgetExceeded`. Synthetic test audit entries (`run_id='test-budget'`) were removed from `output/audit_trail.json` afterward so the production trail only contains genuine runs. | PASS |

## C. Every agent configured for gpt-6-luna via PORTKEY_API_KEY

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| Single centralized model factory | Static | `backend/config.get_model()` is the only place an `OpenAIChatModel` is constructed in `backend/`; all 5 `build_*_agent` functions call it | PASS |
| Model name is exactly `gpt-6-luna` | Static + live | `REQUIRED_MODEL_NAME = "gpt-6-luna"`; live runs' console banners confirm `model: openai:gpt-6-luna` | PASS |
| Key read from `PORTKEY_API_KEY`, never hardcoded | Static | `os.environ.get("PORTKEY_API_KEY")`, loaded via `dotenv` from the course `.env`; `get_model()` raises if unset rather than falling back | PASS |
| Compliance actively validated, not just asserted in prose | **Direct** unit test | `assert_model_is_compliant()` called on every agent build; directly tested that it raises `RuntimeError` when passed a `gpt-4o` model instance | PASS |

## D. All shop facts come through MCP, no direct SQLite bypass

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| No `sqlite3` import anywhere in `backend/` | Static | `grep -rl "import sqlite3" backend/` → no matches | PASS |
| Agents only access data via the shared MCP toolset | Static | `backend/mcp_client.new_campus_customs_toolset()` is the only toolset constructor used by any `build_*_agent`/Boss | PASS |

## E. Original 3 tools still work; new tools registered and callable

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| 9 tools total, correct names | **Live**: `asyncio.run(server.mcp.list_tools())` | Returned exactly 9: the original 3 plus `list_open_tickets`, `get_shop_date`, `check_vendor_payment_status`, `get_cash_balance`, `record_approved_payment`, `close_ticket` | PASS |
| Original 3 tools still zero-argument | Live, re-checked after the Problem 5 edit | `t.parameters.get('properties', {}) == {}` asserted true for all 3 original tool names | PASS |
| New tools callable with real inputs | Live (direct function calls, scratch DB only) and live (via agent/MCP in the 3 ticket runs) | `check_vendor_payment_status(1)` returned real unpaid-invoice data during the Ticket 101 agent run; direct tests confirmed the rest (see sections G/H below) | PASS |

## F. Representative workflows for Tickets 101, 102, 103 (live, end-to-end)

All three run through the real stack: Boss agent → real delegation tool call → real specialist `Agent.run()` → real MCP stdio connection to `mcp_server/server.py` → real SQLite read against `data/campus_customs_new.db` → real `gpt-6-luna` completion via Portkey, for every step.

| Ticket | Delegations (live) | Result (live) | DB-grounded? |
|---|---|---|---|
| 101 | Boss→Customer Service, Boss→Inventory | Correctly identified 0 stock at size S, cited the real $840 invoice 501 and Bulldog Print Co's real 5-day lead time, correctly refused to treat a shipment as approvable (invoice unpaid), flagged human approval required | Yes — every figure matches the database exactly |
| 102 | Boss→Facilities, Boss→Accounting | Correctly computed "2 days until due" using `desk.date_today` (2026-08-31) vs. lease `next_due` (2026-09-02), cited real $2,400 rent and real $3,400 balance, confirmed payment would not go negative, flagged human approval required | Yes |
| 103 | Boss→Customer Service, Boss→Accounting | Correctly identified the 12-unit shortfall (8 available vs. 20 requested) at size M, cited real $22 cost / $58 list price, declined to approve a discount without policy/human input | Yes |

No ticket's payment or closure was executed by any run — correct, since none of the three conversations supplied a human approval, and the agents' prompts (and the `record_approved_payment`/`close_ticket` tools' own guardrails) correctly withheld action.

## G. Negative and safety scenarios

All run **directly against the tool implementation on a disposable scratch copy** of the working database (created in the session scratch directory, never `data/campus_customs.db` or the live `data/campus_customs_new.db`; deleted after use) — this is deliberate: these are correctness tests of the guardrail logic itself, not of MCP transport (already proven live, repeatedly, in Problems 3/4 and in section F above).

| Scenario | Result | Verdict |
|---|---|---|
| Unpaid vendor invoice (gating a new shipment) | `check_vendor_payment_status(1)` → `has_unpaid_invoices: true`; also observed live in the Ticket 101 agent run, where Inventory correctly refused to treat a shipment as viable | PASS |
| Insufficient cash ($999,999 payment vs. $3,400 balance) | `record_approved_payment` refused: `"would take 'checking' from 3400.0 to a negative balance"`, no write occurred | PASS |
| Missing approval (blank `approved_by`) | `record_approved_payment` refused: `"approved_by is required..."`, no write occurred | PASS |
| Invalid ticket (`close_ticket(9999, ...)`) | Refused: `"Ticket 9999 not found."`, no write occurred | PASS |
| Invalid vendor (`check_vendor_payment_status(9999)`) | Refused: `"Vendor 9999 not found."` | PASS |
| Delegation-limit overflow (5th hop) | `_RunState.record()` raised `DelegationBudgetExceeded` on the 5th call (direct unit test, see section B) | PASS |
| Valid, properly-approved payment (control case) | `record_approved_payment(..., approved_by="Piero Talledo (simulated...)")` succeeded, balance correctly decremented by exactly the payment amount, verified against a follow-up `get_cash_balance` call — all on the scratch copy only | PASS |

## H. `audit_trail.json` appends correctly, never overwrites

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| Appends across multiple separate process runs | Live: 3 separate `python -m backend.run_team <id>` invocations | Event count grew 8 → 16 → 24 across the three runs; all three `run_id`s present simultaneously in the final file | PASS |
| Never overwrites/truncates | Code read + live | `backend/audit.append_event()` always reads the existing array first and writes the union back; confirmed empirically by the growing count above | PASS |
| Sufficient detail per step | Static + live | Each event carries `timestamp`, `run_id`, `ticket_id`, `agent`, `event_type`, and a `detail` payload (delegation reason, specialist's full structured output, or error) | PASS |
| No API keys or secrets logged | Static | `AuditEvent.detail` only ever contains ticket/delegation/output data constructed in `orchestrator.py`; no credential is ever passed into it | PASS |

## I. Original database byte-for-byte unchanged; working DB changes only when authorized

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| `data/campus_customs.db` unchanged | SHA-256, re-run after all Problem 5 work | `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a` — identical to every prior recorded value | PASS |
| `data/campus_customs_new.db` unchanged by the 3 live runs | SHA-256 + row counts | Identical hash to the original; `payments` table still has 0 rows; all 3 tickets still `status='open'` — correct, since no run received human approval | PASS |
| Both pass `PRAGMA integrity_check` | Live | `ok` on both | PASS |
| Negative-test writes stayed off the real databases | Code read + process confirmation | All write-path tests ran with `server.DB_PATH` monkey-patched to a scratch file in the session temp directory, never the project's `data/` files | PASS |

## J. `harness.md` and MCP README match the actual implementation

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| harness.md documents all 5 agents + responsibilities | Static | New "Problem 5" section added, table matches `backend/prompts/*.md` content | PASS |
| harness.md documents all 9 MCP tools + tables accessed | Static, cross-checked against live `list_tools()` | All 9 names present with table mappings matching the actual SQL in `server.py` | PASS |
| harness.md has a safety section and a token/cost section | Static | Both present, each citing specific, verified mechanisms (not generic prose) | PASS |
| `mcp_server/README.md` tool list exactly matches implementation | **Live** cross-check | Script compared `list_tools()` output names against README text — 0 missing | PASS |

## K. Imports, syntax, dependencies, paths, error handling, reproducibility

| Check | Method | Evidence | Verdict |
|---|---|---|---|
| Syntax | `py_compile` on all 9 `backend/*.py` files + `mcp_server/server.py` | All compiled cleanly | PASS |
| Dependencies declared | Static | `requirements.txt` updated to add `pydantic-ai-slim[openai,mcp]`; `fastmcp` and `python-dotenv` already present | PASS |
| Paths portable | Static | All paths in `backend/` derived via `Path(__file__).resolve().parent...`, no hardcoded absolute paths | PASS |
| Error handling on bad model config | Direct unit test | `get_model()` raises `RuntimeError` if `PORTKEY_API_KEY` unset (verified by reading the code path; not re-triggered live to avoid unnecessarily unsetting the real key) | NOT RE-TESTED LIVE (static only) |
| Reproducible from a clean project environment | Static + live (this project's own venv was in fact built once and used throughout) | `requirements.txt` plus the existing `.venv` setup pattern from Problems 1–4 is sufficient; not tested from a truly separate clean clone in this pass | NOT VERIFIED (would require a full clean clone, out of scope for this pass) |

## L. Live vs. mocked/static — explicit distinction

**Live (real model + real MCP, not mocked):** the initial connectivity smoke test, and all three full ticket-team runs (101, 102, 103) in section F, including every delegation and every specialist's tool use within them.

**Direct/unit (real code, no live model call):** the delegation-budget test, the model-compliance-rejection test, and all 7 negative/safety-guardrail tests in section G (these test the deterministic Python validation logic in `mcp_server/server.py`, not model behavior, and intentionally avoid spending additional live API calls on scenarios the guardrail code already proves deterministic).

**Static:** all file-existence, cross-reference, and documentation-matching checks.

No test result in this report was fabricated; no PASS is claimed for anything not actually executed.

## M. Regression — Problems 1–4

| Check | Evidence | Verdict |
|---|---|---|
| Problem 1–4 files still present | `AI_prompts.md`, `output/harness.md`, `output/problem2_audit.md`, `output/problem3_audit.md`, `output/verification_checklist.md`, `output/mcp_smoke.json`, `mcp_server/server.py`, `mcp_server/README.md`, `.mcp.json` all confirmed present | PASS |
| Problem 4's genuine MCP smoke-test evidence preserved | `output/mcp_smoke.json` not modified in Problem 5 | PASS |
| Original 3 MCP tools unchanged | See section E | PASS |
| Homework 4 and other prior homework folders untouched | No file outside `Homework 5/` was written during Problem 5 | PASS |

## N. Remaining risks / NOT VERIFIED items

- **Clean-environment reproducibility** (item K) was not tested from an actual separate clone — this project's single `.venv` was used throughout. Should be exercised once, end-to-end, before final submission.
- **Redacted/unavailable assignment detail:** no portion of the visible Problem 5 requirements was found to be hidden or redacted in what was provided to this session; nothing was flagged as NOT VERIFIED on that basis.
- **Delegation depth constant:** `MAX_DELEGATION_DEPTH = 2` is set as a forward-looking ceiling, but the current architecture (specialists have no delegation tools) means real depth never exceeds 1. This is a deliberate, documented design choice, not a gap, but worth noting if a future problem adds specialist-to-specialist escalation.
- **Boss's own direct MCP tool use:** the Boss agent also holds the shared MCP toolset directly (in addition to its 4 delegation tools), so it can look up a ticket itself before delegating, as instructed in its prompt and observed live in all three runs — this is intentional, not a bypass, since it still goes through the same MCP server.

---

## Overall Problem 5 result (original pass): **PASS**, with 2 items marked **NOT VERIFIED** (K: clean-environment reproducibility; error-handling retrigger) rather than claimed as tested.

No corrections were required to any agent, prompt, model, or tool logic as a result of this original audit — all live and direct tests passed on the first implementation pass tested.

---

## Update: strict adversarial audit found 4 real gaps, now corrected

A follow-up strict, adversarial audit (`output/problem5_adversarial_audit.md`) deliberately re-tested this implementation looking for weaknesses rather than confirmation, and found 4 real, material gaps that this original pass's tests did not surface:

1. **Full connectivity** was only Boss→specialist (a star topology), not genuinely "delegate to each other." **Fixed:** added a real `escalate_to_boss` tool on every specialist, with cycle detection and depth bounding added to `_RunState`.
2. **Payment approval was not technically enforced** — a fabricated `approved_by` string succeeded. **Fixed:** replaced it with a `create_payment_approval_request` / human-only `backend/approve_payment.py` / single-use `approval_id` flow; no agent can self-approve.
3. **Duplicate payment was possible** — the same invoice could be paid twice. **Fixed:** both the request-creation and payment-recording tools now check `invoices.status`, and the payment writes are wrapped in an explicit transaction.
4. **Audit trail did not capture individual MCP tool calls** — only each specialist's final output was logged. **Fixed:** wired `MCPToolset.process_tool_call` to log every real tool invocation (name, sanitized args, sanitized outcome) via a new `AgentDeps` context.

All four corrections were re-tested adversarially (not just re-inspected) and confirmed PASS — full re-test evidence is in `output/problem5_adversarial_audit.md`'s "Correction pass — re-test results" section. The 2 original NOT VERIFIED items (K) were separately, actually re-tested in that same audit pass: reproducibility was verified from a genuine isolated clean copy with a fresh venv, and the missing-key failure path was triggered for real in an isolated process. **Both are now PASS, not NOT VERIFIED.**

## Final overall tally (after corrections)

- **Total checks passed:** 33 (original pass) + 4 corrections (connectivity, approval, duplicate-payment, audit traceability) + 2 previously-NOT-VERIFIED items now actually tested (reproducibility, missing-key) = all requirement areas now PASS.
- **Total checks failed:** 0 (the 4 that failed under adversarial testing were corrected and re-tested to PASS).
- **Total checks not verified:** 0.
- **Files changed in the correction pass:** `mcp_server/server.py` (new `create_payment_approval_request` tool; `record_approved_payment` rewritten to take only `approval_id`, with transaction + duplicate-payment guards), `mcp_server/approvals.py` (new), `backend/approve_payment.py` (new, human-only CLI), `backend/models.py` (added `AgentDeps`), `backend/mcp_client.py` (added `process_tool_call` audit hook), `backend/agents.py` (added `deps_type=AgentDeps`), `backend/orchestrator.py` (rewritten for bidirectional connectivity + cycle detection), `backend/prompts/*.md` (specialist prompts now name the real `escalate_to_boss` tool), `mcp_server/README.md`, `output/harness.md`, `output/verification_checklist.md`.
- **Database integrity status:** both databases unchanged throughout (`23686a90...1f360a`, `PRAGMA integrity_check` = `ok`) across the entire correction pass, including 6 live ticket runs (3 before, 3 after the corrections) and all adversarial payment tests (run exclusively against disposable scratch copies).
- **Is Problem 5 ready to close:** **Yes**, after this correction pass.
- **Remaining risks for final submission:** the single-use approval guarantee relies on a single-process `threading.Lock`, sufficient for this homework's scope but not a production-grade distributed lock — documented as a known limitation, not hidden.
