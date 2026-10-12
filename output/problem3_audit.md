# Problem 3 — Independent Grading Audit (Build the MCP Server, 12 points)

Methodology: `output/verification_checklist.md`. This audit does not trust or reuse the original Problem 3 verification report's conclusions — every check below was rerun fresh, with new evidence captured on 2026-10-12.

## 1. Requirements and deliverables

| Requirement | Test method | Evidence | Verdict | Correction needed |
|---|---|---|---|---|
| `mcp_server/server.py` exists and uses FastMCP | File check + grep for `from fastmcp import FastMCP` and `FastMCP(` | Both present (lines 11, 15) | PASS | None |
| Exactly three MCP tools registered | Executed: fresh `asyncio.run(server.mcp.list_tools())` | Returned exactly 3: `get_ticket_101_restock_info`, `get_ticket_102_rent_and_cash_info`, `get_ticket_103_pricing_and_inventory_info` | PASS | None |
| All tools use `data/campus_customs_new.db` | Code read + executed: printed `server.DB_PATH`, confirmed it resolves to the working copy | `DB_PATH` = `.../Homework 5/data/campus_customs_new.db`; original DB path never referenced in code | PASS | None |
| `output/harness.md` documents each tool, tables, ticket, business purpose | Content read | Problem 3 section present with 3 tool entries, each naming tables, ticket number, and a specific one-sentence rationale | PASS | None |
| `mcp_server/README.md` accurately describes implementation | Cross-checked tool names/tables/DB path against actual code | Exact match — tool names identical in code, harness.md, and README.md (verified via grep diff) | PASS | None |
| `AI_prompts.md` contains actual prompts used | Content read | Problem 3 prompt present verbatim, with a Result section describing only tests actually run | PASS | None |
| Requirements that cannot be verified due to incomplete assignment text | Review of available instructions | None identified — the pasted Problem 3 instructions were complete enough to verify every stated requirement | NOT APPLICABLE | — |

## 2. Independent functional tests (fresh, isolated — server never started/connected)

For each tool, ground truth was computed via **separate, independently written SQL queries** against `data/campus_customs_new.db`, then compared field-by-field to the tool's actual return value using Python `assert` statements (not visual inspection).

| Tool | Test method | Evidence | Verdict |
|---|---|---|---|
| `get_ticket_101_restock_info` | Independent SQL (ticket → inventory → invoice → vendor) vs. tool output, `assert`-compared | All 4 sub-objects (`ticket`, `inventory_at_sku_size`, `linked_invoice`, `supplying_vendor`) matched exactly | PASS |
| `get_ticket_102_rent_and_cash_info` | Independent SQL (ticket → lease, desk, cash_accounts) vs. tool output, `assert`-compared | All 4 fields matched exactly, including `cash_accounts` as a list | PASS |
| `get_ticket_103_pricing_and_inventory_info` | Independent SQL (ticket → inventory at size, inventory all sizes, pricing) plus independently recomputed margin vs. tool output, `assert`-compared | All 6 fields matched exactly, including computed `margin_per_unit` ($36.00) and `margin_pct_of_list_price` (62.07%) | PASS |
| Output structure / data types | Inspected returned dict shapes | Each tool returns a flat JSON-serializable dict; nested objects are plain dicts or `None`; lists used only where multiple rows are possible (`cash_accounts`, `inventory_all_sizes_for_sku`) | PASS |
| Tool registry discoverability | Executed: `asyncio.run(server.mcp.list_tools())`, fresh process | 3 tools discoverable by name | PASS |
| Server was not started/connected | Confirmed no `mcp.run()` call was made during testing — only direct function calls and `list_tools()` | No server process opened; no network/stdio transport touched | PASS |

## 3. Security and database integrity

| Check | Test method | Evidence | Verdict |
|---|---|---|---|
| No tool writes to the original DB | Code read: zero `INSERT`/`UPDATE`/`DELETE` statements anywhere in `server.py` | Grep for those keywords returns no matches | PASS |
| Original DB SHA-256 unchanged | Executed: fresh `sha256sum` | `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a` — matches every prior recorded hash | PASS |
| SQLite integrity checks pass | Executed: `PRAGMA integrity_check` on both DBs | `ok` on both `campus_customs.db` and `campus_customs_new.db` | PASS |
| No SQL injection vulnerabilities | Code read + executed: inspected tool input schemas via `list_tools()` | All queries use static strings with `?` placeholders; all three tools additionally take **zero external parameters** (`properties: {}`), so there is no attacker-controlled input path into SQL at all | PASS |
| No hardcoded API keys/credentials | Executed: grep for `sk-`, `api_key`, `PORTKEY` | No matches | PASS |
| No payment or inventory mutation functionality | Code read | Only `SELECT` queries present | PASS |
| No unnecessary AI model calls | Code read | No LLM/Portkey/OpenAI imports or calls anywhere in `mcp_server/` | PASS |
| No unrelated future-problem functionality | Directory listing | No agent, FastAPI backend, or React dashboard files exist anywhere in the project | PASS |

## 4. Edge case testing

All edge cases were run against **disposable copies** created in the session scratch directory (never the original `data/campus_customs.db` nor the working `data/campus_customs_new.db`), with `server.DB_PATH` temporarily monkey-patched in-process to point at each disposable copy. All scratch copies were deleted after testing.

| Edge case | Setup | Observed behavior | Verdict | Defect or future enhancement? |
|---|---|---|---|---|
| Missing ticket ID (ticket 101 deleted) | `DELETE FROM tickets WHERE id=101` on a disposable copy | Tool returned `{"error": "Ticket 101 not found in database."}` — no exception, no invented data | PASS | N/A — handled correctly |
| Dangling invoice reference (`invoice_id` pointed at a non-existent invoice) | `UPDATE tickets SET invoice_id=9999 WHERE id=101` | `linked_invoice` and `supplying_vendor` both resolved to `None`; no crash | PASS | N/A — handled correctly |
| Missing inventory record (exact SKU/size row deleted) | `DELETE FROM inventory WHERE sku='CC-TEE-WHITE' AND size='S'` | `inventory_at_sku_size` returned `None`; no crash, no fabricated quantity | PASS | N/A — handled correctly |
| NULL `lease_id` on ticket 102 | `UPDATE tickets SET lease_id=NULL WHERE id=102` | `lease` returned `None`; no crash | PASS | N/A — handled correctly |
| Empty `cash_accounts` table | `DELETE FROM cash_accounts` | `cash_accounts` returned `[]`, not `None` or an error — correct, since the tool queries a list of rows | PASS | N/A — handled correctly |
| Missing pricing row for a valid SKU | `DELETE FROM pricing WHERE sku='CC-HOOD-NAVY'` | `pricing`, `margin_per_unit`, and `margin_pct_of_list_price` all returned `None`, no divide-by-zero, no invented margin | PASS | N/A — handled correctly |
| Unexpected input types | N/A — all three tools take zero parameters, so there is no external input surface to pass an unexpected type into | NOT APPLICABLE | NOT APPLICABLE | By design — no input parameters exist |

No genuine defects were found in any edge case. All failure modes degrade to `None`/`[]`/a clear error message rather than crashing or fabricating data.

## 5. Documentation consistency

| Comparison | Method | Result |
|---|---|---|
| Tool names: code vs. `harness.md` vs. `README.md` | `grep -oP` extraction of tool names from all three files | Identical set and order of 3 names in all three files |
| Database path description | Compared README's stated path-resolution strategy to actual `DB_PATH` expression in code | Matches — README correctly describes resolution relative to the server file's own location, not the launch directory |
| Tables referenced per tool | Compared harness.md's "tables read" per tool to the actual SQL in `server.py` | Matches exactly for all 3 tools |

Verdict: PASS — no documentation drift found.

## 6. Regression testing (Problems 1–2)

| Check | Evidence | Verdict |
|---|---|---|
| All 9 tables still exist with unchanged row counts | Fresh `COUNT(*)` on all 9 tables: desk 1, tickets 3, inventory 10, pricing 4, vendors 3, leases 1, cash_accounts 1, payments 0, invoices 1 — identical to the Problem 2 baseline | PASS |
| All 3 original tickets remain available | Fresh query: tickets 101, 102, 103 all present, all `status = 'open'` | PASS |
| Original database remains intact | SHA-256 unchanged (see Section 3) | PASS |
| Problem 2 harness content not lost | `output/harness.md` still contains all original 9 table sections and the 3-ticket explanation section, in addition to the new Problem 3 section | PASS |

## 7. Reproducibility

| Check | Evidence | Verdict |
|---|---|---|
| `requirements.txt` exists | Present, lists `fastmcp` and `python-dotenv` | PASS |
| Declared packages match what the server actually needs | `server.py` imports only `fastmcp` (plus Python stdlib `sqlite3`, `pathlib`) — both declared dependencies are accounted for; `python-dotenv` is not yet imported anywhere in code (reserved for future Portkey/API-key loading in later problems, consistent with the project's "never hardcode keys" rule) | PASS, with a note |
| Project-specific `.venv` exists for Homework 5 | `.venv/` created in this project folder, not shared with other homeworks | PASS |
| No unrelated dependencies introduced | `pip freeze` in the Homework 5 `.venv` shows only `fastmcp`, `fastmcp-slim` (a fastmcp sub-dependency), `python-dotenv`, and their transitive requirements — nothing unrelated to Problem 3 | PASS |

Note: `requirements.txt` does not pin exact versions (e.g., `fastmcp==4.1.0`). This is not a stated requirement violation — the assignment text does not mandate version pinning — but it is flagged as a reproducibility risk below.

## 8. Corrections made

**None.** No genuine defects were found in Problem 3's implementation or documentation during this independent audit. No code, harness.md, or README.md content required changes, so no "rerun after fix" step was necessary.

---

## Final tally

- **Total checks passed:** 33
- **Total checks failed:** 0
- **Total checks not verified:** 0 (one item — "requirements that cannot be verified due to incomplete assignment text" — was explicitly marked **NOT APPLICABLE**, not unverified, since the available Problem 3 text was complete enough to check everything it stated; one edge case — "unexpected input types" — was also marked **NOT APPLICABLE** since the tools take no parameters)
- **Files changed by this audit:** None in `mcp_server/` or `output/harness.md`/`README.md` (no defects to fix). Created: `output/problem3_audit.md` (this file). Temporary scratch database copies used for edge-case testing were created outside the project directory and deleted after use — no trace left in the project.
- **Database integrity status:** Both `data/campus_customs.db` and `data/campus_customs_new.db` pass `PRAGMA integrity_check` (`ok`); original database SHA-256 unchanged (`23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`) throughout this audit.
- **Is Problem 3 ready to close:** **Yes.** Every stated requirement passed independent, freshly executed verification with no defects found.

### Remaining risks for final submission
- `requirements.txt` is unpinned — a future `pip install` could pull a newer, behaviorally different `fastmcp` release. Low risk today since the API surface used (`FastMCP`, `@mcp.tool`) is stable, but worth pinning before final submission for strict reproducibility.
- The three tools currently take no parameters and operate only on the fixed tickets 101/102/103 — this is correct and sufficient for Problem 3's stated scope, but future problems (agents) will need to confirm whether more general, parameterized lookups are required, or whether these ticket-specific tools remain the intended design.
- `payments` is still empty and no agent/payment logic exists yet — the human-approval-before-payment rule and the `gpt-6-luna`/Portkey compliance rule remain untestable until Problem 4 or later introduces that code; this is carried forward from the Problem 2 audit, not new to Problem 3.
- `data/data/` (the original professor download) still exists in the tree, intentionally preserved; it should be excluded from any future "unnecessary files" scan in the Stage 8 final grader simulation.
