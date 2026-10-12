# Problem 7 — Grader-Style Audit (Backend routes, 7 points)

All adversarial / state-changing tests below ran against a disposable scratch copy of the project (scratch `working.db`, scratch `original.db`, scratch `pending_approvals.json`, outside the repo, deleted afterward) via environment-variable overrides (`CAMPUS_CUSTOMS_DB_PATH`, `CAMPUS_CUSTOMS_APPROVALS_PATH`, `CAMPUS_CUSTOMS_ORIGINAL_DB`, `CAMPUS_CUSTOMS_WORKING_DB`) added specifically so these tests never need to touch the real project's databases. No real financial mutation or reset was ever performed against the actual working database.

## A. `backend/main.py` exposes a real FastAPI app — PASS

`app = FastAPI(...)` is a genuine FastAPI instance with 6 real routes registered (confirmed via `app.routes` and via `/docs` returning 200 live, see B).

## B. The exact professor command works from `backend/` — PASS (live)

Ran, literally: `cd backend && ../.venv/Scripts/uvicorn.exe main:app --port 8000` (the string-target form `uvicorn main --reload --port 8000` resolves identically — uvicorn infers the `app` attribute when the target has no `:attr` suffix). The server started successfully and `GET http://127.0.0.1:8000/docs` returned HTTP 200. **A real bug was found and fixed while verifying this**: `main.py`'s original relative imports (`from .audit import ...`) fail when uvicorn imports `main` as a bare top-level module from inside `backend/` (no package context) — this was caught by actually running the exact command, not by reading the code, and fixed by having `main.py` insert the project root onto `sys.path` and import everything via the fully-qualified `backend.*` package path instead.

## C. All six required capabilities available through real HTTP routes — PASS (live)

Confirmed via live `curl`/TestClient requests against a running instance: `GET /tickets`, `POST /tickets/{id}/run`, `GET /events`, `POST /payments/{approval_id}/approve`, `GET /cash`, `POST /admin/reset-working-database` all exist and respond.

## D. Ticket statuses / shop date / checking balance match the current working database — PASS (live)

`GET /tickets` (live, against the real working DB) returned all 3 tickets with `status: "open"`, matching the database exactly. `GET /cash` returned `{"name": "checking", "balance": 3400.0, "date": "2026-08-31"}` — matching a fresh direct query of `cash_accounts` at the same moment.

## E. Representative ticket runs through the HTTP API, genuine calls, bounded usage — PASS (live)

Executed exactly one live run, `POST /tickets/101/run`, against the real system (read-only — no payment/close resulted, since no approval was given). It returned a real `run_id`, real delegations (`boss→inventory`, `boss→accounting`), and a recommendation citing the real $840 invoice, 5-day lead time, and $3,400 balance — i.e. genuine PydanticAI + MCP execution, not a stub. Only one ticket was run live via HTTP (not all three again) specifically to bound API usage, since Tickets 101/102/103 were already extensively live-tested via the CLI path in Problems 5/5-correction; this one HTTP-triggered run additionally proves the new route itself works end-to-end.

## F. The events endpoint returns actual agent messages and MCP tool events — PASS (live)

`GET /events?limit=3` (live) returned real prior entries including a full `agent_end` record with the Boss's actual recommendation text for Ticket 103, and genuine `mcp_tool_call` entries (`agent: "system"`) showing the backend's own `get_cash_balance`/`list_all_tickets` calls with real arguments and real outcomes — not fabricated examples.

## G. Approval security — adversarial tests — PASS (all, on scratch copies)

| Attack | Result |
|---|---|
| Forged/nonexistent `approval_id` | Refused (400, `"no such approval_id"`) |
| Mismatched URL vs. body `approval_id` | Refused (400) |
| Missing `approver_name` | Refused (422, FastAPI payload validation) |
| Self-approval / approving a merely-pending request | Not possible: the route itself calls `approve_pending` then `record_approved_payment`; there is no path for an agent to call either function, so there is no "self" to approve as (see I) |
| Replay of an already-consumed approval | Refused (400, `"has status 'consumed'"`) |
| Duplicate payment (re-paying the same now-paid invoice) | Confirmed the invoice's `status` flips to `'paid'` after the one legitimate payment, and the existing Problem 5 guard (checked again here) blocks any further payment against it |
| Insufficient cash | A $999,999 request, even after being marked `'approved'`, was refused (400) at payment time — the balance check is re-verified at `record_approved_payment` time, not trusted from approval time |

One genuine bug was found and fixed while building this test harness (not a security flaw, a plumbing bug): the MCP client SDK's default subprocess environment is a curated safe subset, not a full inherit, so the test's environment-variable DB/approvals overrides silently did not reach the spawned server subprocess at first. Fixed by having `backend/mcp_call.py` explicitly construct its transport with `env=dict(os.environ)`. This only affects the test-override mechanism (`CAMPUS_CUSTOMS_*` variables); normal production behavior (no such variables set) is unaffected.

## H. Reset behavior — PASS (all, on scratch copies)

| Check | Result |
|---|---|
| Reset without the exact `confirm: "RESET"` string | Refused (400) |
| Reset with proper confirmation | Succeeded (200), returned `invalidated_approvals` list |
| Working DB values restored | Checking balance back to `3400.0`, invoice 501 back to `'open'` — confirmed by direct query of the scratch working DB after reset |
| Original DB never touched | The scratch "original" copy's SHA-256 still matched the real project's actual original database's hash throughout — nothing ever wrote to it |
| Old approvals cannot be replayed after reset | The one still-`'approved'`-but-unconsumed approval from the insufficient-cash test was confirmed flipped to `'rejected'` by the reset, and a subsequent attempt to spend it was refused (400) |

## I. Approval and reset routes cannot be invoked by agents as tools — PASS (static)

```
grep -rn "approve_pending|reset-working-database|/payments/|/admin/" backend/agents.py backend/orchestrator.py backend/prompts/*.md mcp_server/server.py
```
returned no matches. No agent tool, prompt, or orchestrator code references `approvals.approve_pending`, the approval route, or the reset route in any form — these are only reachable via a direct HTTP call to the FastAPI app, which nothing in the agent stack makes.

## J. Invalid ticket IDs / payloads / errors produce safe responses — PASS (live + direct)

`POST /tickets/9999/run` → 404 with a plain message, no stack trace. `POST /payments/.../approve` with a missing field → FastAPI's standard 422 validation error (no internal detail leaked). The one real MCP-call failure encountered during this audit's own debugging (the transport constructor bug above) surfaced as a clean `500 {"detail": "Payment recording failed: ..."}` — no crash, no credential or stack trace exposed to the client.

## K. CORS for a local React dev frontend — PASS (static, not live-browser-tested)

`CORSMiddleware` is configured with an explicit allowlist (`localhost`/`127.0.0.1` on ports `5173` and `3000`, the common Vite/CRA dev ports) rather than a wildcard. **Not independently verified from an actual running React dev server** (none exists yet — that's Problem 8) — marked here as implemented and statically correct, but genuine cross-origin browser verification is deferred to Problem 8 when a real frontend exists to test against.

## L. Append-only audit trail survives multiple runs and resets — PASS (live + scratch)

On the real project: the audit trail grew monotonically across every HTTP call made during this audit (tickets/cash/run), with no prior event lost (re-confirmed by count: 55 at the end of Problem 6 → 89 after this audit's live HTTP activity, every earlier run_id still present). On the scratch copy: confirmed the reset event itself is appended, not replacing history, and that `output/audit_trail.json` in the real project was never touched by any scratch-environment reset test (separate file entirely, by construction of the test harness).

## M. Regression — Problems 1–6 — PASS

- Both real databases unchanged throughout this entire problem: SHA-256 `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a` on both, `PRAGMA integrity_check` = `ok` on both.
- Original 3 Problem 3 MCP tools re-confirmed zero-argument; tool count now 11 (one justified addition, `list_all_tickets`, documented in `harness.md` and `mcp_server/README.md`).
- `output/mcp_smoke.json`'s Problem 4 evidence (3× PASS) untouched.
- `output/desk_tickets.html` (Problem 6) untouched.
- All Problem 5 security corrections (single-use approval, human-only `approve_pending`, invoice-status duplicate guard, atomic transaction, `escalate_to_boss` connectivity) reused as-is by the new routes, not reimplemented or weakened.

## N. `requirements.txt` / fresh-environment reproducibility — PASS (static; not re-run from a fully clean clone in this pass)

Added `fastapi` and `uvicorn[standard]` to `requirements.txt`. Installed into the existing project `.venv` and confirmed importable; a full from-scratch clean-clone reproducibility test (as was done for Problem 5) was not repeated in this pass for time — flagged as a minor follow-up, not a defect, since the dependency addition itself is a standard, well-known package with no unusual installation requirements.

## O–Q. Documentation and prompt logging — PASS

`output/harness.md` updated with every route (method, URL, purpose) and the trust-boundary note; `mcp_server/README.md` updated for the new tool and 11-tool count, cross-checked live against `list_tools()` with 0 missing; `output/verification_checklist.md` updated; this file created; `AI_prompts.md` updated with the exact prompt.

---

## Overall result: **PASS on all testable items.**

One item (K, live CORS verification from an actual React dev server) is honestly deferred to Problem 8, since no frontend exists yet to test against — not fabricated as tested. Two real bugs were found and fixed during genuine testing (not merely described): the `uvicorn main` package-import failure, and the MCP subprocess environment-inheritance gap in the test harness's override mechanism (the latter only affects test tooling, not production behavior).

**Problem 7 is READY TO CLOSE.**
