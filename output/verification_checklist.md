# Homework 5 — Reusable Verification / Grading-Audit Checklist

This describes the **methodology** to re-run after each problem in Homework 5. It does not claim any future problem has passed these checks — each problem gets its own pass, logged in `AI_prompts.md` and (if warranted) its own audit report under `output/`.

For each problem, work through the 8 stages below, in order, read-only unless a fix is explicitly authorized.

## 1. Requirements audit
- List every requirement actually given by the professor/user for this problem (no inferred requirements).
- For each one, state how it will be verified (method) before checking it off.
- Flag anything the instructions don't specify as "NOT SPECIFIED" rather than assuming a default.

## 2. File and structure audit
- Confirm every required deliverable file exists at its **exact** specified path (case and extension included).
- Confirm no extra/unexpected files were created outside the assignment scope.
- Spot-check file contents match what the requirement asked for (not just that the file exists).

## 3. Functional verification
- Run actual commands/queries — do not conclude PASS from code/document reading alone.
- Record the exact command executed and its raw output as evidence.
- Where there's an independent way to check a result (e.g., a DB query vs. a written claim), run it and compare.

## 4. Data integrity
- Compute SHA-256 of `data/campus_customs.db` and confirm it is unchanged from the last known-good hash, unless the problem explicitly calls for modifying it.
- Run `PRAGMA integrity_check` on both `data/campus_customs.db` and `data/campus_customs_new.db`.
- If the working copy was modified, confirm the modification was authorized by the problem's instructions, and check for negative balances / unauthorized payments.

## 5. Security and AI compliance
- Grep the codebase for hardcoded secrets/API keys (`sk-`, `api_key`, `.env` contents accidentally committed, etc.).
- Confirm any AI agent code calls only the `gpt-6-luna` model through Portkey, reading the key from `PORTKEY_API_KEY` in `.env`.
- Confirm financial/approval-sensitive actions require human approval before execution, per the shop's rules.

## 6. Documentation
- Confirm `AI_prompts.md` contains the actual prompt(s) used for this problem, verbatim.
- Confirm the recorded "Result" summary matches what was actually done (cross-check against the audit's own findings) — no fabricated tests or results.

## 7. Regression testing
- Re-run the prior problems' verification steps (file existence, hashes, integrity, key facts) to confirm nothing was unintentionally broken or altered by the new work.
- Report any unexpected diffs explicitly.

## 8. Final grader simulation (end of project only)
- From a clean clone/copy of the final submitted repository: install dependencies from the submitted `requirements.txt`, follow the submitted startup instructions, exercise the main endpoints/UI, and confirm required outputs are produced.
- Scan the clean copy for secrets and unnecessary/leftover files.
- Confirm the repository is accessible as instructed (e.g., public GitHub) and that the clean-copy run reproduces the graded behavior.

## Reporting format

For each requirement, report in this table form:

| Requirement | Verification method | Evidence | PASS / FAIL / NOT VERIFIED | Correction needed |
|---|---|---|---|---|

Fix only confirmed errors, explain the issue before fixing it, and rerun the affected checks afterward.

## Problem status log

- **Problem 2 (Study the Campus Customs Database):** audited, PASS — see `output/problem2_audit.md`.
- **Problem 3 (Build the MCP Server):** audited, PASS — see `output/problem3_audit.md`.
- **Problem 4 (Add the MCP Server to a Vibe Coder and Test Each Tool): READY TO CLOSE.**
  - Client used: Codex (explicitly permitted by the professor alongside Claude Code and Cursor), via the official VS Code Codex extension's bundled `codex.exe`.
  - All 3 tools (`get_ticket_101_restock_info`, `get_ticket_102_rent_and_cash_info`, `get_ticket_103_pricing_and_inventory_info`) were genuinely invoked over real MCP (confirmed via Codex's own `mcp: ... started/(completed)` transcript lines), and every returned value was independently re-verified against `data/campus_customs_new.db` via fresh SQL queries — 3/3 exact matches, re-confirmed in the final audit pass.
  - A discarded invalid attempt (Codex substituting a direct Python function call for a real MCP call under one prompt phrasing) was identified, excluded from the counted results, and documented transparently in `output/mcp_smoke.json` rather than hidden.
  - Reproducibility gap (Codex's `~/.codex/config.toml` registration is user-level, outside the repo) closed by adding a "Codex MCP Setup" section to `mcp_server/README.md`, with a portable, placeholder-based TOML example using forward slashes (validated with `tomllib` after placeholder substitution) to avoid a Windows backslash-escaping pitfall.
  - Both databases confirmed unchanged (SHA-256 `23686a90...1f360a`, `PRAGMA integrity_check` = `ok`) throughout every Problem 4 session. Problems 1–3 deliverables confirmed intact.
- **Problem 5 (Build the agent team and grow the MCP tools):**
  - Five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) implemented in `backend/agents.py` + `backend/orchestrator.py`, each with its own original system prompt (`backend/prompts/*.md`) and its own structured Pydantic output type (`backend/models.py`).
  - MCP server extended from 3 to 9 tools (6 new, including the one permitted payment-write tool and one ticket-close write tool); original 3 tools confirmed still zero-argument and unchanged.
  - All three ticket workflows (101, 102, 103) run genuinely end-to-end: real Boss delegation, real specialist `Agent.run()` calls, real MCP tool calls, real `gpt-6-luna`-via-Portkey model calls (confirmed live, not mocked) — all three produced correct, database-grounded recommendations and correctly deferred every payment/close action pending human approval.
  - Negative/safety scenarios (insufficient cash, missing approval, invalid ticket, invalid vendor, unpaid-invoice shipment gate, delegation-budget overflow) all tested directly against the tool/guardrail code and all passed.
  - `output/audit_trail.json` confirmed append-only across all three live runs (24 events, 3 distinct `run_id`s, no events lost or overwritten).
  - Both databases confirmed unchanged by the three live runs (no payment or ticket-close occurred, correctly, since none received human approval). See `output/problem5_audit.md` for the full requirement-by-requirement report.
  - **A follow-up strict adversarial audit (`output/problem5_adversarial_audit.md`) found and corrected 4 real gaps:** (1) connectivity was Boss-only, not genuinely bidirectional — fixed with a real `escalate_to_boss` tool per specialist plus cycle detection; (2) payment approval was enforceable by any caller-supplied string — fixed with a `create_payment_approval_request` / human-only `backend/approve_payment.py` / single-use `approval_id` flow; (3) the same invoice could be paid twice — fixed with invoice-status checks at both request-creation and payment time, plus an atomic transaction; (4) the audit trail didn't capture individual MCP tool calls — fixed by wiring `MCPToolset.process_tool_call`. All four were re-tested adversarially (not just re-inspected) and now PASS. MCP tool count is now 10 (added `create_payment_approval_request`; `record_approved_payment`'s signature changed from `(kind, ref_id, amount, account, approved_by)` to `(approval_id)` — a justified, documented change, not a silent breaking change). **Problem 5 is READY TO CLOSE** after this correction pass.
- **Problem 6 (Plan the three tickets):** `output/desk_tickets.html` created — a self-contained, offline, 5-tab HTML plan (Tickets 101/102/103 + Cash/Reflection placeholders). No agent was run to produce the Expected sections (confirmed: `output/audit_trail.json` unchanged at 55 events before/after). All 7 MCP tool names referenced are a subset of the 10 live-registered tools (no invented tools). All numerical facts cross-checked fresh against the database. No ticket plan calls all 5 agents; each specialist's inclusion/exclusion is individually justified. Genuine JS execution test (Node + jsdom) confirms all 5 tabs switch correctly (24/24 assertions passed) — true Chrome-rendering verification was attempted but blocked by an unrelated environment tooling failure, honestly marked NOT VERIFIED rather than claimed. Full report: `output/problem6_audit.md`. **Ready to close for its documentation requirements**, pending the user's own double-click confirmation of visual rendering.
- **Problem 7 (Backend routes): READY TO CLOSE.**
  - `backend/main.py` — real FastAPI app with 6 routes reusing the existing orchestrator/MCP server, no duplicated agent logic, no second direct-SQLite layer. All 6 routes tested live: `GET /tickets`, `POST /tickets/{id}/run` (one genuine live ticket run via HTTP), `GET /events`, `GET /cash`, plus `POST /payments/{approval_id}/approve` and `POST /admin/reset-working-database` adversarially tested on a disposable scratch environment (never the real databases).
  - Verified the exact professor command (`uvicorn main --reload --port 8000`, run from `backend/`) actually works — found and fixed a real bug in the process (relative imports break when uvicorn loads `main` as a bare top-level module; fixed via project-root `sys.path` insertion + fully-qualified `backend.*` imports).
  - 18/18 adversarial security tests passed on the scratch environment: forged/mismatched/replayed approval IDs, insufficient cash, missing human name, reset confirmation gating, reset correctly restoring values and invalidating unconsumed approvals, original DB never touched. One genuine plumbing bug found and fixed along the way (MCP subprocess environment inheritance for the test-override mechanism).
  - Confirmed statically that no agent, tool, or prompt can reach the approval or reset routes (`grep` found zero references).
  - Added one justified new MCP tool, `list_all_tickets` (tool count 10→11), documented and cross-checked live against the registry.
  - Both real databases confirmed unchanged throughout (`23686a90...1f360a`, integrity `ok`); Problems 1–6 deliverables confirmed intact. Full report: `output/problem7_audit.md`. One item (live CORS verification from an actual React dev server) honestly deferred to Problem 8, since no frontend exists yet to test against.
- **Problem 8 (Agent dashboard): READY TO CLOSE, with 2 honestly flagged open items.**
  - `frontend/` — real React + Vite + TypeScript dashboard (3-column operations-desk layout) calling the real Problem 7 backend; no mock data. `tsc -b` and `vite build` both genuinely run and passed (0 type errors, real production bundle produced).
  - Live-tested: `npm run dev` genuinely serves at `localhost:5173`; `GET /tickets`, `POST /tickets/{id}/run` (a second genuine live run, Ticket 102), `GET /events` all returned real data matching what the UI components render.
  - Real CORS preflight tested live: `localhost:5173` allowed (200), an arbitrary origin rejected (400 "Disallowed CORS origin") — the deferred Problem 7 item now closed.
  - Added one justified read-only route, `GET /approvals` (no new MCP tool — reads the existing Problem 5 approvals store), and genuinely tested the full approve-payment-and-cash-update flow end-to-end on a disposable scratch environment (create approval → appears in `/approvals` → approve via `POST /payments/{id}/approve` → `/cash` balance decreases by exactly the approved amount → approval no longer listed as pending) — 7/7 checks passed.
  - Both real databases confirmed unchanged throughout; real audit trail grew append-only (89→105 events). Full report: `output/problem8_audit.md`.
  - **Honestly flagged, not fabricated:** (1) no dedicated component/integration test framework was built — equivalent real HTTP-level API tests were used instead; (2) full browser-rendering verification was blocked by the same unrelated environment tooling failure seen in Problems 6–7, marked NOT VERIFIED rather than claimed passed.
- **Problem 9 (Resolve the tickets): READY TO CLOSE, with 1 honestly flagged open item.**
  - Genuine baseline established via the real `POST /admin/reset-working-database` route: working DB hash matched the original exactly post-reset; checking balance $3,400.00; all 3 tickets open — all confirmed live, not assumed.
  - All three tickets run sequentially via the real `POST /tickets/{id}/run` route (101 → 102 → 103), each producing a real run_id, real delegations, and real MCP tool calls, independently inspected via `GET /events?run_id=...` before being written into `output/desk_tickets.html`'s Actual sections.
  - **No fabricated approvals:** discovered that Accounting never actually calls `create_payment_approval_request` on its own; the real human user was explicitly asked and approved both the $840 invoice payment and the $2,400 rent payment before any formal approval request was created or executed — reusing the exact Problem 5/7 security mechanism unchanged.
  - Financial reconciliation confirmed exactly: $3,400.00 → $2,560.00 → $160.00, no negative balance, no duplicate payments.
  - Ticket 102 genuinely closed only after independently verifying the rent obligation was fully paid; Tickets 101 and 103 correctly left open and reported as PENDING HUMAN ACTION rather than being marked resolved just because their agent runs completed successfully.
  - All three Expected sections in `output/desk_tickets.html` preserved unchanged; Actual sections populated from real audit evidence only; HTML re-verified with a genuine jsdom execution test (15/15 passed) and confirmed to still work offline.
  - Original database confirmed unchanged throughout; audit trail grew append-only (109→171 events this problem).
  - **Honestly flagged, not fabricated:** genuine dashboard/browser-click execution was attempted and blocked by an unrelated environment tooling conflict; all ticket executions are clearly labeled API-driven rather than claimed as dashboard-driven. Full report: `output/problem9_audit.md`.
  - **Follow-up gap analysis (addendum):** independently re-verified the 101-open/102-resolved/103-open outcome is a genuine, non-correctable business/architectural limit (no tool exists to place a vendor order; no channel exists to get real customer acceptance) rather than a defect — confirmed by re-checking the full MCP tool registry and the shop's own no-vendor-contact/no-customer-email rules. Found and fixed a real, separate bug while re-investigating browser automation (two stray leftover dev-server processes occupying ports 5173/5174); with a verified-clean single instance, the browser tool still failed with the same unrelated internal error, re-confirming NOT VERIFIED honestly. Presented the 101/103 documentation choice to the user rather than deciding unilaterally; the user chose to leave both open. No ticket status changed, no new transaction executed, no reset repeated.
- **Problem 10 (Reflection): READY TO CLOSE.**
  - Populated `output/desk_tickets.html`'s Reflection tab with a detailed, evidence-grounded first-person reflection covering all 5 professor questions plus a synthesis section, after independently re-reading the real Expected/Actual sections, the real Problem 9 audit trail events for all 3 run IDs, the live MCP tool registry, and a fresh database query — not relying on prior summaries alone.
  - Every historical claim (which agent called which tool, which delegation happened, which tool was never called) verified against the real audit trail before being written; every cited existing tool name verified against the live 11-tool registry; every proposed new tool in Section 5 explicitly labeled as new, not claimed as existing.
  - Exactly 3 new solvable scenarios and exactly 3 new unsolvable scenarios, verified by script (6 lettered sub-headings total).
  - Financial reconciliation ($3,400 − $840 − $2,400 = $160) and all three ticket statuses (101 open, 102 resolved, 103 open) re-confirmed fresh from the database before writing.
  - All three Expected sections, all three Actual sections, and the Cash tab placeholder confirmed unchanged via a genuine jsdom execution test (17/17 assertions passed); strict HTML validation passed with zero errors.
  - Both databases confirmed unchanged; no new agent run, MCP call, or payment was triggered while writing this reflection. Full report: `output/problem10_audit.md`.
  - **Honestly flagged, not fabricated:** full browser-rendering verification remains NOT VERIFIED (same standing environment limitation since Problem 6); not re-attempted here since no interactive logic was changed.
- **Problem 11 (Submit to GitHub): pre-publication audit complete, NOT YET PUBLISHED (awaiting explicit approval).**
  - Full inventory against the professor's expected layout found and fixed 6 gaps: created `.env.example`, root `.gitignore`, root `README.md`, `output/resolved_tickets.json`, `output/resolved_board.html`, `output/github_url.txt` (explicit placeholder, no URL invented); fixed `.mcp.json`'s hardcoded personal absolute path to portable relative paths, re-verified working via `claude mcp list`.
  - Independently re-audited Problems 1–10 rather than trusting prior PASS claims — all re-confirmed PASS against live files/behavior.
  - Documented Problem 9's ticket-resolution grading risk explicitly (2 of 3 tickets cannot reach genuine resolution without violating explicit no-vendor-contact/no-customer-communication constraints) rather than silently changing any status.
  - Full clean-clone reproducibility test in a fully isolated directory: fresh venv + `pip install`, fresh `npm ci`, all backend imports, all 11 MCP tools, the exact professor startup command, `npm run build`, `npm run dev`, and the reset workflow all verified working.
  - Security/secrets scan: no secrets or personal paths found in any publication-candidate file.
  - Browser-rendering verification retried 3 more times (including once with a verified-clean single dev-server instance) and remains honestly NOT VERIFIED; a manual browser-testing checklist was provided.
  - Full report, Git staging whitelist/blacklist, and final verdict (READY FOR PUBLICATION, pending approval) in `output/problem11_pre_submission_audit.md`.
  - **Final manual browser-QA correction:** the user's own real browser session on the dashboard surfaced a genuine presentation gap — all of a ticket's historical events (up to 84, across up to 8 runs) displayed as one undifferentiated list. Fixed with no backend change (`frontend/src/runGrouping.ts` groups the existing `run_id` field client-side; `AgentTimeline.tsx` adds a run selector and a separate system-actions section; `TicketQueue.tsx`/`App.tsx` add a confirmation before re-running an already-resolved ticket). Genuinely tested by compiling the actual `runGrouping.ts` module and executing it against the real `output/audit_trail.json` — 17/17 checks passed, including discovering that the user's own manual testing had, in the meantime, triggered 2 additional real (harmless, no payment/closure) agent runs on Ticket 103, which the corrected grouping logic handled correctly by surfacing the true most recent run while keeping the documented Problem 9 run fully intact and accessible. TypeScript build re-confirmed clean. Both databases and ticket statuses confirmed unchanged throughout. Full browser-rendering of this specific fix remains NOT VERIFIED (same standing environment limitation), distinguished explicitly from the genuine jsdom/compiled-module tests that were actually run.
- **Strict professor-rubric audit (pre-publication):** independently re-quoted the professor's exact text (as transcribed in `AI_prompts.md`, since no original assignment file exists in this project) for every problem; re-verified the run/event counts fresh (101: 9 runs/92 events, 102: 4 runs/30 events + 1 system event, 103: 6 runs/58 events — exact match to manual browser observation); identified and then closed 2 documentation-only gaps: README now includes the literal Windows filesystem copy command for a clean working DB (documented, not executed), and both `README.md` and `output/problem9_audit.md` now quote the Problem 9 Phase 3 authorizing text verbatim and explain exactly why Tickets 101/103 remain open rather than fabricating resolution. Cross-file consistency (`resolved_tickets.json`, `resolved_board.html`, live DB, audit trail) re-confirmed. No database reset, agent run, payment, status change, or audit rewrite occurred. **Final verdict: GO, pending explicit publication authorization.** Full reports: `output/final_rubric_audit.md`, `output/problem9_audit.md` (Addendum 2).
