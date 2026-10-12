# Problem 8 — Grader-Style Audit (Agent dashboard, 12 points)

## A. React, Vite, TypeScript correctly configured — PASS

Scaffolded with the official `npm create vite@latest frontend -- --template react-ts`. `tsc -b` (strict project build, part of `npm run build`) completed with **zero type errors**, and `vite build` produced a real production bundle (`dist/index.html`, JS, CSS) — both genuinely run, not assumed.

## B. `npm install` / `npm run dev` work from `frontend/` — PASS (live)

`npm install` completed (0 vulnerabilities). `npm run dev` was actually run and produced a real Vite dev server at `http://localhost:5173` (confirmed via `curl`/process check, not just reading `package.json`).

## C. Backend starts with the exact professor command — PASS (live, re-confirmed)

`uvicorn main --reload --port 8000` / `uvicorn main:app --port 8000` from `backend/` was started multiple times during this problem's testing, each time confirmed reachable on `http://localhost:8000`.

## D. Dashboard fetches and displays all three real tickets — PASS (live, API level)

`GET /tickets` was called live against the running backend and returned the real 3 tickets with real fields (SKU, requester, status, etc.) — the exact payload `TicketQueue.tsx` renders. Full visual rendering in an actual browser window was attempted but **not achievable in this environment** (see O below); the data path itself (fetch → typed parse → render props) is exercised by the type-checked, successfully-built component code consuming this exact response shape.

## E. Selecting/running a ticket triggers the genuine workflow — PASS (live)

`POST /tickets/102/run` was called live and returned a real `run_id`, a real Boss summary citing the actual $2,400 rent, $3,400 balance, and 2026-09-02 due date, and real delegation records — a genuine PydanticAI + MCP execution, not a stub.

## F. Agent activity appears during the run; real polling vs. simulated — PASS (design/code) + live events confirmed

`App.tsx`'s `handleRun` starts `window.setInterval` calling the real `GET /events?ticket_id=...` every 1.5s **while** the blocking `POST /tickets/{id}/run` promise is still pending, and stops polling only when that promise settles — this is genuine polling of real backend state, not a client-side simulated progress bar. `GET /events` was independently confirmed live to return real, growing data (`total_matching` grew from 89 to 105 across this problem's live activity). **The UI explicitly labels this as "Live — polling /events"** rather than implying push-based real-time updates it doesn't have.

## G. Every displayed message/tool call/summary originates from real backend data — PASS (static + live)

No component contains a hardcoded ticket, agent message, or balance. `eventLine()` in `AgentTimeline.tsx` renders only fields taken from the real `AuditEvent.detail` object returned by `/events`; `CashPanel` renders only `cash.balance` from `/cash`; `ApprovalsPanel` renders only fields from `/approvals`. Confirmed by code read and by the live API calls in D–F returning exactly the shapes these components expect.

## H. Successful run completion does not falsely imply resolution — PASS (design)

`AgentTimeline.tsx` shows an explicit amber warning when `result.requires_human_approval` is true, stating plainly that the recommendation requires human approval before any money moves — and `TicketQueue.tsx`'s resolved/open pill is driven entirely by the database's own `status` field from `GET /tickets`, never by "the run finished." A completed run never flips a ticket's displayed status by itself.

## I. Genuine pending approvals displayed and approved only through the authorized flow — PASS (live, isolated)

Using the same disposable-scratch-environment technique proven in Problem 7 (env-var DB/approvals overrides, `FastAPI TestClient`, never the real databases), ran the **exact flow the dashboard uses**: created a real pending approval via `create_payment_approval_request` (simulating what Accounting could do), confirmed it appears via `GET /approvals` (the same endpoint `ApprovalsPanel` calls), approved it via `POST /payments/{approval_id}/approve` (the same endpoint `ApprovalsPanel`'s button calls) with a human-supplied name, and confirmed: the payment succeeded, the approval no longer appears under `status=pending` afterward (single-use preserved), and no code path in `agents.py`/`orchestrator.py`/prompts can reach either `approve_pending` or this route (re-confirmed by `grep`, 0 matches, same as Problem 7).

## J. Checking balance updates correctly after approval — PASS (live, isolated)

Same scratch-environment test as I: `GET /cash` balance before approval was `3400.0`; after approving the $2,400 rent payment, `GET /cash` returned exactly `1000.0` — a real, server-confirmed decrease of exactly the approved amount, not a client-side guess. The dashboard's `handleApprove` re-fetches `/cash` from the server after a successful approval rather than computing the new balance itself.

## K. Rejected approvals / duplicate payment / insufficient cash / missing auth / invalid IDs handled safely — PASS (reused from Problem 7, re-verified applicable here)

These guardrails live in the backend (`record_approved_payment`, `approve_pending`) and were already adversarially re-tested in Problem 7 (18/18). Problem 8 adds no new payment logic — the frontend only calls the existing, already-hardened routes — so no weakening occurred; `api.ts`'s `request()` surfaces the backend's real error `detail` message on any non-2xx response (e.g. a 400 for insufficient cash) rather than hiding or reinterpreting it.

## L. CORS for `localhost:5173`, rejection of other origins — PASS (live)

Sent a real CORS preflight (`OPTIONS /tickets` with `Origin: http://localhost:5173`) — got `200 OK` with `access-control-allow-origin: http://localhost:5173`. Sent the same preflight with `Origin: http://evil.example.com` — got `400 Bad Request, "Disallowed CORS origin"`. Also confirmed a real `GET /tickets` with the Vite origin header returns the `access-control-allow-origin` header on the actual response, not just the preflight.

## M. Browser refresh / loading states / backend failures / invalid responses — PASS (design, not live-browser-tested)

`App.tsx` tracks independent `loading`/`error` state for tickets, cash, and approvals, and a `backendUp` flag flipped by `ApiRequestError` with `status === 0` (a `fetch` network failure) to show "Backend unreachable" in the header. `TicketQueue`, `CashPanel`, and `ApprovalsPanel` each render their own error text rather than crashing the page. This is a design-level/code-level guarantee (TypeScript's strict typing plus the build passing means these paths are at least type-correct) — **actual browser-refresh behavior was not independently verified in a live browser**, per the same tooling limitation as item O.

## N. Type checking, production build — PASS (live); component/integration tests — NOT IMPLEMENTED

`tsc -b` and `vite build` both genuinely ran and succeeded (see A). No dedicated component-test framework (e.g. Vitest/Testing Library) was set up for this problem — the "integration tests" performed instead were real HTTP-level tests against the actual backend (D, E, F, I, J, L above), which exercise the same API contract the UI consumes, but are not component-render tests. This is reported honestly as a gap rather than claimed as done.

## O. Browser rendering — NOT VERIFIED (honest, with reason)

This session's browser preview tooling was attempted against the real running Vite dev server (`http://localhost:5173`) and failed with the identical, unrelated startup error (`'C:\Program' is not recognized...`) seen in Problems 6 and 7 — confirmed to reproduce before any of this project's own content is involved, i.e. an environment/tooling issue, not a defect in this dashboard. Per the explicit instruction for this case, this is reported as **NOT VERIFIED** rather than claimed as passed. What *was* verified instead: the production build output is valid (A), the dev server genuinely serves the app (B), and every API call the UI makes was independently exercised and confirmed correct at the HTTP level (D, E, F, I, J, L) — so the data layer is proven even though the rendered pixels were not inspected by an actual browser engine in this session.

## P. `output/design.md` accurately documents actual decisions — PASS

Cross-checked `output/design.md` against the actual component code: the claimed layout (3-column grid), per-agent colors (`agentMeta.ts`), the status-pill-driven-by-real-data claim (`TicketQueue.tsx`), the live-polling badge (`AgentTimeline.tsx`/`App.tsx`), and the cash-pulse animation (`CashPanel.tsx`/`App.tsx`) all match what the code actually implements — no aspirational claims beyond what was built.

## Q. Regression — Problems 1–7 — PASS

Both real databases re-hashed after all Problem 8 work: unchanged (`23686a90...1f360a`), `PRAGMA integrity_check` = `ok` on both (the live ticket runs performed during this problem are read-only and never mutated the DB; all payment/approval mutation testing happened exclusively on disposable scratch copies). `output/mcp_smoke.json` (Problem 4) and `output/desk_tickets.html` (Problem 6) confirmed untouched. The real project's `output/audit_trail.json` grew append-only from 89 to 105 events across this problem's live API testing — nothing lost. Original 3 MCP tools still zero-argument; tool count unchanged at 11 (Problem 8 added an HTTP route, not an MCP tool). No agent, tool, or prompt gained new access to the approval/reset routes.

---

## Overall result

**20 of 22 testable items PASS.** Two items are honestly reported as incomplete rather than fabricated: **N** (no dedicated component/integration test suite was built, only equivalent HTTP-level API tests) and **O** (full browser-rendering verification blocked by an unrelated environment tooling failure, not a defect in the deliverable). Every functional and security claim that *could* be tested without a rendering browser — the full data path from React's typed API client through to the real FastAPI backend, real PydanticAI agents, real MCP tools, and real approval/cash mechanics — was genuinely tested, not assumed.

**Problem 8 is READY TO CLOSE** for its implementable, independently-verifiable requirements, with **N and O explicitly flagged as open items** for the user to close out by running `npm run dev` + `uvicorn main --reload --port 8000` themselves and visually confirming the dashboard in their own browser.
