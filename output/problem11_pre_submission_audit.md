# Problem 11 — Pre-Submission Audit (Submit to GitHub, 5 points)

**No public repository has been created or pushed. This is the pre-publication audit only, as explicitly instructed.**

## Phase 1 — Full project inventory

| Expected item | Status | Note |
|---|---|---|
| `AI_prompts.md` | PASS | Present, complete, chronological |
| `requirements.txt` | PASS | Present |
| `.env.example` | **FIXED** | Was missing; created with variable name + safe placeholder only |
| `.gitignore` | **FIXED** | Was missing at root; created |
| `.mcp.json` | **FIXED** | Existed, but hardcoded a personal absolute Windows path — rewritten to portable relative paths, re-verified working via `claude mcp list` |
| `README.md` | **FIXED** | Was missing; created (see Phase 8) |
| `data/campus_customs.db` | PASS | Present, pristine |
| `data/campus_customs_new.db` | PASS | Present, reflects genuine Problem 9 state ($160 balance, ticket 102 resolved) |
| `data/data/` (stray provenance folder) | NOTED | Original professor download, not part of expected structure; excluded via `.gitignore`, left on disk (not deleted) |
| `mcp_server/server.py`, `mcp_server/README.md` | PASS | Present, 11 tools registered, cross-checked live |
| `frontend/` | PASS | Present, builds cleanly |
| `backend/main.py`, `backend/models.py`, `backend/prompts/{boss,inventory,accounting,facilities,customer_service}.md` | PASS | All present |
| `output/harness.md` | PASS | Present, updated through Problem 10 |
| `output/mcp_smoke.json` | PASS | Present, 3× PASS (Problem 4 evidence) unmodified |
| `output/desk_tickets.html` | PASS | Present, 5 tabs, Expected+Actual+Reflection all populated |
| `output/design.md` | PASS | Present |
| `output/resolved_tickets.json` | **CREATED** | Did not exist; created from genuine current database + audit-trail evidence (see Phase 4) |
| `output/resolved_board.html` | **CREATED** | Did not exist; created, self-contained, offline |
| `output/audit_trail.json` | PASS | Present, append-only, 173 events at time of this audit |
| `output/github_url.txt` | **CREATED** | Did not exist; created as an explicit, clearly-labeled placeholder, no invented URL |
| Top-level empty `prompts/` folder | NOTED | Leftover from Problem 1 scaffolding, empty, harmless, git will not track an empty directory |
| `AVAILABILITY.txt` | NOTED | Course-provided file, harmless, not part of the expected hw5 structure but not forbidden either |

**Original database pristine check:** `data/campus_customs.db` SHA-256 `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a` — re-confirmed unchanged from every prior recorded value across all 10 problems. **No previous homework folder was modified during this audit.**

## Phase 2 — Independent per-problem audit (re-checked, not trusted from prior claims)

| Problem | Verdict | Independent check performed in this audit |
|---|---|---|
| 1 — AI prompt documentation | PASS | `AI_prompts.md` re-opened, confirmed chronological, every problem's prompts present verbatim |
| 2 — Database inspection/harness | PASS | Re-queried all 9 original tables live; matches `output/harness.md`'s table descriptions exactly |
| 3 — FastMCP server, 3 original tools | PASS | Live `list_tools()` re-run: all 3 original tools present, zero-argument (`properties: {}`) |
| 4 — Codex MCP evidence | PASS | `output/mcp_smoke.json` re-opened: 3 tests, all `status: PASS`, real tool outputs present; `mcp_server/README.md`'s Codex setup section still present |
| 5 — 5 agents, gpt-6-luna, delegation, security | PASS | `backend/agents.py`/`orchestrator.py` re-read: 5 agents, single `get_model()` factory, `escalate_to_boss` present on all 4 specialists, `create_payment_approval_request`/`record_approved_payment` split confirmed in `mcp_server/server.py` |
| 6 — 5-tab HTML, Expected plans | PASS | All 3 Expected sections present and, per Problem 9/10 audits, confirmed byte-unchanged since creation |
| 7 — FastAPI routes, exact startup command | PASS (re-verified in Phase 7 below) | |
| 8 — React dashboard, CORS, design.md | PASS | `frontend/src/` re-read: typed API client, no hardcoded data; `output/design.md` present |
| 9 — genuine execution evidence | PASS, with documented grading risk | See Phase 3 below |
| 10 — reflection | PASS | All 5 questions + synthesis present; exactly 3+3 scenarios (re-counted) |

No problem's prior PASS claim was accepted without re-checking the underlying file or live behavior in this audit.

## Phase 3 — Problem 9 compliance risk (explicit documentation, not a fix)

**Verified outcome, unchanged, not silently altered:** Ticket 101 OPEN, Ticket 102 RESOLVED, Ticket 103 OPEN. $3,400 → $2,560 (−$840) → $160 (−$2,400).

The professor's instruction to run tickets "until each is resolved" is in direct tension with the assignment's own, repeatedly-stated constraints: no vendor contact, no customer communication, no fabricated approvals. Two of three tickets (101, 103) cannot reach genuine business resolution without this system performing an action it has no tool for and is explicitly forbidden from performing. This was investigated in depth during Problem 9's gap-analysis addendum, including the user being asked directly whether to leave the tickets open (accurate) or close them with "shop-side action complete" framing — **the user chose to leave them open.**

**Grading risk, stated plainly:** a strict reading of "resolve all three tickets" would mark this submission short of full compliance on that literal instruction. The project's position — supported by every other explicit safety constraint in the assignment across Problems 5, 7, 8, and 9 — is that fabricating a vendor order or customer acceptance to force a 3-of-3 resolved count would be a more serious violation than leaving two tickets honestly open. No ticket status was changed, no transaction was repeated, and no business history was rewritten to improve this count.

## Phase 4 — Resolved-ticket deliverables

`output/resolved_tickets.json` and `output/resolved_board.html` did not exist before this audit. Both were created from a genuine, read-only query of `data/campus_customs_new.db` and the real Problem 9 run IDs — not regenerated by rerunning any agent or payment. The JSON correctly marks only Ticket 102 as `"resolution_state": "resolved"`; Tickets 101 and 103 are `"pending_human_action"`, each with explicit `shop_side_steps_completed` vs. `outstanding_real_world_obligation` lists. The HTML visually distinguishes all five required states (Resolved / Open / Pending human action / Completed shop-side step / Outstanding real-world obligation) via a legend and per-ticket sections. No professor-specific schema was visible, so a minimal, self-documented structure was used rather than inventing grading-specific fields (the JSON's own `_note` field states this explicitly).

## Phase 5 — Real visual and browser audit

**Genuine browser automation was attempted three times across this session** (and multiple additional times across Problems 6–9), including one attempt in this audit after thoroughly cleaning up every stray leftover dev-server process (confirmed via `netstat` that exactly one process was listening on port 5173 with nothing on 5174 immediately before the final attempt). **It failed identically every time** with an internal tooling error (`'C:\Program' is not recognized...`) that reproduces before any of this project's own content is involved, confirming it is an environment limitation, not a defect in this dashboard or this HTML file.

**Honest result: browser-rendered verification of `output/desk_tickets.html`, the React dashboard, `output/resolved_board.html`, and responsive layouts is NOT VERIFIED.**

What *was* genuinely verified as a substitute, clearly distinguished from actual browser rendering:
- `output/desk_tickets.html`: real Node+jsdom execution of its actual `showTab()` function (not a mock), confirming all 5 tabs switch correctly and the real content (run IDs, statuses, Expected text) is present — 17/17 assertions passed (Problem 10's test, re-confirmed structurally intact here).
- The React dashboard: a real, running `npm run dev` instance was confirmed reachable via `curl` (HTTP 200, real HTML returned), and every API call the UI makes was independently exercised against the real backend in Problems 7–8 (not re-run here, to avoid unnecessary API cost).
- `output/resolved_board.html`: validated with Python's strict `html.parser` (zero errors) — not yet jsdom-tested, since it has no interactive JavaScript to execute (static content only).

**Manual browser-testing checklist for the user to execute** (since this session's automation remains unavailable):
1. With the backend running (`cd backend && uvicorn main --reload --port 8000`) and frontend running (`cd frontend && npm run dev`), open `http://localhost:5173`.
2. Confirm the three tickets display with correct subjects and statuses (101 open, 102 resolved, 103 open).
3. Click a ticket card; confirm the center panel shows its details.
4. Click "Run agent team" on a ticket; confirm the "Live — polling /events" badge appears and real event lines stream in before the final summary appears. *(Note: this will make real Portkey API calls — bounded, intentional use only.)*
5. Check the right column: confirm the agent roster, a real dollar-formatted checking balance, and (if any exist) pending approval cards with a name field and "Approve payment" button.
6. Resize the browser to a mobile width (~375px); confirm the 3-column grid collapses to a single column without horizontal scrolling or broken layout.
7. Open `output/desk_tickets.html` directly by double-clicking it (no server needed); click through all 5 tabs; confirm Expected, Actual, Cash (placeholder), and Reflection content all display correctly.
8. Open `output/resolved_board.html` directly; confirm the three ticket cards and the color-coded legend display correctly.

## Phase 6 — Security and privacy audit

| Check | Result |
|---|---|
| `.gitignore` excludes `.env`, `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, OS cruft, `.claude/` | PASS (created in this audit) |
| Scan of all publication-candidate files for secret-shaped strings (`sk-...`, `api_key=...`) | PASS — none found |
| Personal absolute paths (`C:\Users\piero\...`) in any deliverable file (JSON/HTML/Markdown/Python/`.mcp.json`) | PASS — none found; `.mcp.json` fixed to relative paths as a precaution even though it had no secret, just a portability problem |
| `AI_prompts.md`, audit `.md` files for leaked personal paths | PASS — none found (0 matches via `grep -c`) |
| `.env.example` contains only a variable name and placeholder | PASS |
| `.mcp.json` portability | **FIXED** — now relative paths, re-verified via `claude mcp list` |
| Database contents reviewed for anything beyond course-provided fictional data | PASS — `requester` values are the course's own fictional names (Tauhid Zaman, Elm City Properties, Yale AI Club); `payments.approved_by` contains the student's own real name as the human approver, which is the assignment's intended use, not a privacy leak |
| Real `.env` staged or committed | N/A / PASS by construction — the real `.env` lives one directory above this repository root (outside the project folder entirely), so it cannot be accidentally staged from within this repo |

No secret value was printed or reproduced anywhere in this audit report.

## Phase 7 — Clean-clone reproducibility (performed in a fully isolated copy, `C:/temp/hw5_clone_test`, deleted after testing — not relying on this machine's existing `.venv`/`node_modules`)

| Step | Result |
|---|---|
| Fresh Python venv + `pip install -r requirements.txt` | **PASS** — installed cleanly |
| All backend imports (`config, models, audit, mcp_client, mcp_call, agents, orchestrator, main`) | **PASS** |
| MCP server starts, lists all tools | **PASS** — 11/11 tools, matching the live project exactly |
| Exact command `cd backend && uvicorn main --reload --port 8000`-equivalent | **PASS** — started, `GET /tickets` and `GET /cash` returned real data |
| `npm ci` (lockfile-based install) | **PASS** — 0 vulnerabilities |
| `npm run build` (`tsc -b && vite build`) | **PASS** — 0 TypeScript errors, real bundle produced |
| `npm run dev` | **PASS** — confirmed reachable via `curl` |
| Reset workflow, isolated copy only | **PASS** — `POST /admin/reset-working-database` correctly restored the clone's working DB to $3,400.00, matching its own original's hash; the clone's original database hash also independently matched the real project's actual original database hash |
| Original SQLite database (real project) unchanged throughout this entire clone test | **PASS** — re-confirmed `23686a90...1f360a` after the clone test completed |
| Genuine MCP calls / agent runs | **PARTIAL** — genuine MCP tool calls were exercised (via the live `GET /tickets`/`GET /cash` routes, which are real MCP calls, not mocks); a full agent run was **not** repeated in the clone to avoid an unnecessary additional paid Portkey call, per the explicit "bounded tests" instruction — agent-run reproducibility was already proven live in Problems 5, 7, 8, and 9 |
| README instructions reproduce these results without undocumented manual fixes | **PASS, with one documented exception**: the `.env` location (one directory above the repo) is a layout inherited from this course's shared directory structure; the README explicitly documents this and gives the one-line fix needed for a standalone clone |
| Windows path/shell/package/env-var/port issues | One real issue found and fixed: `.mcp.json`'s hardcoded personal path (Phase 1/6); one environment quirk documented (`.env` location) |

## Phase 8 — Final documentation

- Root `README.md` created (did not exist) — project overview, architecture, 5 agent roles, MCP tool inventory, required software, environment setup, Portkey configuration (no secrets), MCP configuration for Claude Code and Codex, FastAPI/React startup, dashboard usage, database reset, human approval workflow, safety guardrails, actual three-ticket results, known limitations, troubleshooting, and reproducibility steps.
- `output/harness.md` — reviewed, already current through Problem 10; no changes needed beyond this audit's own additions being referenced.
- `output/verification_checklist.md` — updated with a Problem 11 status entry (see below).
- `AI_prompts.md` — updated with this exact Problem 11 prompt.
- `output/github_url.txt` — remains an explicit placeholder; **no URL was invented.**

## Phase 9 — Final Go/No-Go report

### 1. Required-file inventory
All items from the professor's expected layout now exist. 4 items were missing and have been created/fixed in this audit: `.env.example`, `.gitignore`, `README.md`, `output/resolved_tickets.json`, `output/resolved_board.html`, `output/github_url.txt` (6 items, one bullet above undercounts — corrected count: **6 created, 1 fixed-in-place** (`.mcp.json`)).

### 2. Problems 1–11 rubric compliance matrix
Problems 1–10: all independently re-verified PASS in Phase 2 above (not trusted from prior claims alone). Problem 11: in progress, this document is its own deliverable.

### 3. Missing items and corrections completed
`.env.example`, root `.gitignore`, root `README.md`, `output/resolved_tickets.json`, `output/resolved_board.html`, `output/github_url.txt` — all created. `.mcp.json` — personal absolute path replaced with portable relative paths, re-verified working.

### 4. Remaining FAIL or NOT VERIFIED items
- **NOT VERIFIED:** real browser-rendered visual testing of `output/desk_tickets.html`, the React dashboard, and `output/resolved_board.html` (environment tooling limitation, not a project defect; manual checklist provided above).
- **Documented grading risk, not a FAIL:** Problem 9's 1-of-3 ticket resolution rate, explained in Phase 3, is a constraint-driven outcome, not an oversight.

### 5. Browser verification results
NOT VERIFIED, as stated in Phase 5, with a substitute jsdom-based structural verification and a manual checklist provided.

### 6. Security and secrets audit results
PASS — no secrets or personal paths found in any publication-candidate file; `.gitignore` and `.env.example` now in place; `.mcp.json` made portable.

### 7. Clean-clone reproducibility results
PASS on every tested step (Phase 7), with one documented, non-blocking `.env`-location caveat.

### 8. Exact final database statuses and checking balance
Tickets: 101 open, 102 resolved, 103 open. Checking balance: **$160.00**. Original database: pristine, `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`.

### 9. Git staging whitelist / forbidden-file blacklist

**Whitelist (stage these):**
```
AI_prompts.md
requirements.txt
.env.example
.gitignore
.mcp.json
README.md
data/campus_customs.db
data/campus_customs_new.db
mcp_server/
frontend/            (excluding node_modules/, dist/ -- covered by frontend/.gitignore)
backend/
output/              (excluding output/pending_approvals.json is NOT excluded -- it is real evidence and should be included)
prompts/             (empty; git will not track it)
AVAILABILITY.txt     (harmless, optional)
```

**Blacklist (never stage):**
```
.env                              <- the real file, lives outside this repo anyway
.venv/
frontend/node_modules/
frontend/dist/
__pycache__/ and *.pyc
data/data/                        <- stray provenance copy, excluded via .gitignore
.claude/                          <- local tool config, may contain machine-specific settings
```

### 10. Exact steps needed to publish safely
1. Review `git status` after staging to confirm nothing on the blacklist above is included.
2. Create the GitHub repository as **public**.
3. Push.
4. Update `output/github_url.txt` with the real URL (replacing the placeholder) and commit that one change.
5. Submit the URL to Canvas.

**None of these five steps have been performed. They require your explicit approval first.**

### 11. READY FOR PUBLICATION verdict

**READY FOR PUBLICATION**, pending your review and explicit go-ahead. All identified gaps were corrected and re-tested in this audit; the one remaining NOT VERIFIED item (browser rendering) is an environment limitation with a documented manual fallback, and the one documented grading risk (Problem 9's ticket resolution rate) is a constraint-driven, user-confirmed decision, not an unaddressed defect.

---

## Addendum — Final Manual Browser QA Correction

The user personally opened the real dashboard in Microsoft Edge after this audit and found a genuine presentation gap the automated audits had not caught: a ticket run many times during development (Ticket 101: 84 events/8 runs; Ticket 102: 30 events/4 runs + 1 system event; Ticket 103: 51 events/5 runs) displayed its entire history as one undifferentiated list, with no run boundaries.

### Root cause (confirmed by inspection before any change)
`frontend/src/App.tsx`'s `handleSelect`/`handleRun` fetched a ticket's events with `GET /events?ticket_id=...` and passed the flat, all-history array straight to `AgentTimeline.tsx`, which rendered every event in one list. Every event already carries a real `run_id` (`backend/models.py`'s `AuditEvent.run_id`, populated throughout `backend/orchestrator.py` and `backend/mcp_client.py`) — the data was never ambiguous, only unsorted by the UI. **No backend or data-model change was needed or made.**

### Correction (smallest safe change)
- New `frontend/src/runGrouping.ts`: pure functions `groupEventsByRun()` and `extractSystemEvents()` that reorganize the existing, unmodified event data client-side.
- `frontend/src/components/AgentTimeline.tsx`: rewritten to accept grouped runs, default to the most recent, offer a `<select>` to view any historical run, extract each run's real final Boss summary from that run's own `agent_end` event (not a shared in-memory value), and render system-initiated events (ticket closure, recorded approvals) in a clearly separate "Ticket-level system actions" section rather than folding them into a fabricated run.
- `frontend/src/App.tsx`: now loads and groups full ticket history on selection (never triggers a run), isolates a live run's events by timestamp-since-snapshot (so an in-progress run's feed is never mixed with history), and adds a `runningId !== null` re-entrancy guard in `handleRun` itself (defense in depth alongside the existing button `disabled` state).
- `frontend/src/components/TicketQueue.tsx` / `App.tsx`: a resolved ticket's rerun button is now visually distinct ("Re-run (resolved)") and requires an explicit `window.confirm` before making a new, real, billable agent run.
- No MCP tool, agent prompt, financial logic, or approval security was touched.

### Genuine verification performed

- **A (TypeScript + build):** `npm run build` (`tsc -b && vite build`) re-run — 0 errors, clean production bundle.
- **B (grouping logic against real evidence):** the actual `runGrouping.ts` module was transpiled with the project's own `tsc` and executed in Node directly against the real `output/audit_trail.json` (not a mock) — 17/17 checks passed: exact historical counts confirmed (101: 84, 102: 30, 103: 51), every event accounted for with no loss/duplication/cross-contamination after grouping, and groups correctly sorted most-recent-first.
- **C (Ticket 102's `close_ticket` system event):** confirmed as the sole system event for that ticket, at the exact real timestamp (`2026-10-12T21:56:21.335572+00:00`, matching the user's own observed "5:56:21 PM" local time), correctly labeled and separated from agent activity.
- **D (Ticket 103's escalation):** confirmed present and intact, correctly isolated inside its own specific run (not bled into another run).
- **A genuine, unplanned finding during this verification:** the real `output/audit_trail.json` showed 2 additional, genuine Ticket 103 agent runs timestamped *after* the documented Problem 9 run — almost certainly from the user's own manual dashboard testing triggering "Run agent team" without the (not-yet-fixed-at-that-time) confirmation guard. These were **harmless** (read-only analysis only; independently confirmed Ticket 103's status, cash balance, and payment count were all unaffected) and serve as real-world, unplanned proof of exactly the accidental-rerun risk Phase 3 asked to be closed. The corrected grouping logic handled this correctly on its own: it surfaced the true most recent run by real timestamp rather than a hardcoded assumption, while keeping the originally documented run fully present and accessible.
- **F (databases/payments/statuses/original evidence unchanged):** re-confirmed after all of the above — original DB hash unchanged, working DB has exactly 2 payments, ticket statuses still 101 open / 102 resolved / 103 open, cash still $160.00. `output/audit_trail.json` grew append-only (173 → 228 events across the period between the main audit and this correction, all genuine, none lost).
- **G (regression, Problems 5/7/8/9/10/11):** re-confirmed via the above checks — no agent/orchestrator/MCP/approval code touched; `desk_tickets.html`'s documented run IDs and Expected/Actual content untouched; the pre-submission audit's other findings unaffected.
- **H (clean-clone/security re-check):** since `frontend/src/` files changed, re-scanned the new/modified files for secrets and personal paths — none found. A full repeat clean-clone test was not re-run for this UI-only change (no new dependency, no backend/config change), consistent with bounded testing.
- **I (browser vs. non-browser, explicitly distinguished):** genuine browser automation was **not** re-attempted for this specific fix, since the standing environment tooling limitation (documented since Problem 6, re-confirmed as recently as this same Problem 11 audit) has no reason to have changed. **This fix's actual browser rendering remains NOT VERIFIED** — the tests above are real compiled-module execution and a real TypeScript build, explicitly not claimed to be a browser test.

### Final confirmation
Both databases, all payment records, all three ticket statuses, the checking balance, and every prior problem's audit evidence are unchanged by this correction. **Genuinely READY FOR GITHUB PUBLICATION** on the technical/functional front; the only standing caveat remains the same one already disclosed in the main Phase 9 verdict above (browser-rendering NOT VERIFIED, with a manual checklist provided) — nothing new was introduced by this fix.
