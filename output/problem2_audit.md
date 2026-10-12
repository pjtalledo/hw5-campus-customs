# Problem 2 — Independent Grading Audit

Methodology: `output/verification_checklist.md`. All checks below were run read-only against `data/campus_customs.db`, `data/campus_customs_new.db`, `output/harness.md`, and `AI_prompts.md` on 2026-10-12.

## 1. Requirements audit

| Requirement | Verification method | Evidence | Verdict | Correction needed |
|---|---|---|---|---|
| Inspect all 9 tables in the original DB | Read `sqlite_master` schema + row data directly | `PRAGMA table_info` + `SELECT *` run on all 9 tables (this audit) | PASS | None |
| Document every field, type, PK, FK, relationships per table | Cross-check `output/harness.md` against live `PRAGMA table_info` output | Script comparison: 0 fields missing from harness across all 9 tables | PASS | None |
| No assumed relationships beyond schema/data | Compare harness's relationship claims to actual `FOREIGN KEY` clauses | Harness correctly separates enforced FKs (`tickets.lease_id`, `tickets.invoice_id`, `invoices.vendor_id`) from informal SKU/account matching | PASS | None |
| Examine all 3 open tickets | Query `tickets` table directly | All 3 rows (101, 102, 103) retrieved and cross-checked against harness's ticket descriptions | PASS | None |
| Create `output/harness.md` with table/fields/rationale | File existence + content check | File exists, contains all 9 tables with fields and rationale | PASS | None |
| Explain the 3 tickets' DB relationships | Content review of harness.md | Ticket section present, matches actual linked rows (invoice 501, lease 1, inventory/pricing lookups) | PASS | None |
| Confirm original DB unchanged / working copy identical | SHA-256 + `PRAGMA integrity_check`, independently rerun | Both files hash to `23686a90d698f7fa6f901a3f0a9774db9cbb31e13151c9e5717275f3321f360a`; both `integrity_check` = `ok` | PASS | None |
| Update `AI_prompts.md` with actual Problem 2 prompt | Direct file read | Prompt present verbatim under "Problem 2 — Study the Campus Customs Database," Result summary matches actual work done | PASS | None |
| No MCP server/agents/backend/dashboard implemented yet | Directory listing | No such files exist in the project | PASS | None |

## 2. File and structure audit

| Expected file | Exists at exact path? | Verdict |
|---|---|---|
| `data/campus_customs.db` | Yes | PASS |
| `data/campus_customs_new.db` | Yes | PASS |
| `output/harness.md` | Yes | PASS |
| `AI_prompts.md` | Yes (project root) | PASS |

No unexpected files found outside the declared scope (`data/data/campus_customs.db` is the original professor download, intentionally preserved, not deleted — consistent with Prompt 2's instruction not to delete downloaded files).

## 3. Functional verification

Commands actually executed during this audit (read-only):
- `sha256sum data/campus_customs.db data/campus_customs_new.db data/data/campus_customs.db` → all three identical.
- `PRAGMA integrity_check` on both working DBs → `ok` on both.
- `SELECT COUNT(*) FROM <table>` for all 9 tables → desk 1, tickets 3, inventory 10, pricing 4, vendors 3, leases 1, cash_accounts 1, payments 0, invoices 1 — matches harness and the Prompt 2 result summary exactly.
- Python script comparing `PRAGMA table_info` columns for all 9 tables against the text of `harness.md` → zero missing fields.
- `grep -ril "api_key\|sk-\|secret"` across the Homework 5 tree → no matches.

Verdict: PASS on all functional checks above.

## 4. Data integrity

- Original database untouched: SHA-256 unchanged since the Prompt 2 verification report, and still matches the untouched professor download in `data/data/`.
- `PRAGMA integrity_check`: `ok` on both the original and working copy.
- No rows were inserted, updated, or deleted in either database during Problem 2 (row counts match the Prompt 2 baseline exactly).
- `payments` table remains empty — no unauthorized payments exist. No negative balances present (`cash_accounts.balance = 3400.0`).

Verdict: PASS.

## 5. Security and AI compliance

- No API keys, secrets, or `.env` contents found anywhere in the Homework 5 tree.
- No agent code exists yet in Problem 2, so there is nothing to verify against the `gpt-6-luna` / Portkey requirement — marked **NOT APPLICABLE YET** (this becomes a live check starting Problem 3, once agents are implemented).
- No financial actions were taken in Problem 2, so the human-approval rule has not yet been exercised — marked **NOT APPLICABLE YET**, to be verified once agents can execute payments.

## 6. Documentation

- `AI_prompts.md` contains the actual Prompt 2 text verbatim, matching the pasted instructions exactly.
- The recorded "Result" summary for Prompt 2 was cross-checked against this audit's independent findings and is accurate — no fabricated claims found.

Verdict: PASS.

## 7. Regression testing

- Re-ran Prompt 1 and Prompt 2's original checks (directory structure, DB hash/integrity, table/row counts) — all still hold with no drift.
- No prior problem functionality exists yet to regress against beyond the DB setup itself, which is confirmed unchanged.

Verdict: PASS.

## 8. Final grader simulation

Not applicable at this stage — reserved for the end of the project once the full repository (MCP server, agents, backend, dashboard) exists.

---

## Overall Problem 2 audit result: **PASS**

No corrections were needed — the original Problem 2 implementation and documentation were independently verified to match the evidence. No changes were made to `output/harness.md` or `AI_prompts.md` content as a result of this audit (only additive documentation — this report and the checklist — was created).

### Remaining grading risks to track going forward
- **AI model/compliance checks are not yet testable** — the `gpt-6-luna` / Portkey / no-hardcoded-keys requirement has no code to verify against yet. This must be checked explicitly as soon as Problem 3 introduces agent code.
- **Human-approval and payment-safety rules are not yet testable** — `payments` is empty and no agent can act yet. This must be re-checked the moment any problem introduces payment execution logic.
- **SKU/size matching across `tickets`, `inventory`, and `pricing` is not database-enforced** — future agent code must handle missing/invalid SKU-size combinations defensively, since the schema itself won't catch a mismatch.
- **`data/data/` original download folder still exists inside the project** — harmless and intentionally preserved per instructions, but should be excluded from any future "unnecessary files" scan in the Stage 8 final grader simulation (it is scratch provenance, not a deliverable).
