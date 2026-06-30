---
name: da-reviewer
description: Data architecture review and enrichment. Use when user says "review the analysis", 
  "run Agent 2", "enrich the findings", "validate the DA outputs", or after DA Agent 1 has 
  produced its 13 output files. Do NOT use before DA Agent 1 has completed. Do NOT re-run 
  the full extraction — only review and enrich what exists.
---

# DA Agent 2 — Data Architecture Reviewer
> Pair with: `DA_REVERSE_ENGINEERING_PROMPT_GENERIC.md` | Version: June 2026 v2

---

## When to Activate

- DA Agent 1 has produced files in `da-outputs/`
- User says "review the analysis", "run Agent 2", "enrich the findings", "check what was missed"
- User wants to prepare for a Gate G1 stakeholder review meeting
- User wants to raise confidence scores before sharing the documents

---

## What This Skill Does NOT Do

- Does not re-run the full extraction — only updates what new evidence changes
- Does not add findings without citing evidence (file:line or SQL result)
- Does not escalate questions to Gate G1 that can be answered by reading more code
- Does not merge the review summary into the 13 output files — `review-summary.md` is always separate
- Does not raise a confidence score without a specific test, query result, or document line as proof

---

## Pre-Flight Check — Run Before Anything Else

Read `da-outputs/schema-catalogue.json`. Check the `db_connection` field.

| If `db_connection` is | Then |
|---|---|
| `"CONNECTED"` | Proceed to Phase 1 |
| `"CODE-ONLY"` or missing | Connect to the database NOW (find the CLI tool on this machine, run a connection test, then row counts / schema / FK / index / DQ checks). Update all 13 files with live data first. Do not begin Phase 1 until done. |

---

## Steps

**Phase 1 — Test File Evidence**
1. Find all test files — record total count by type and framework used
2. Read tests in priority order:
   - Priority 1: Business rule tests (`*Entities*`, `*Domain*`, `*Services*` — price, quantity, validation, transfer)
   - Priority 2: Repository / integration tests — look for comments about InMemory vs SQL DB differences
   - Priority 3: Functional / E2E tests — confirm hardcoded passwords, addresses, emails
   - Priority 4: Builders / factories (`*Builder*`, `*Factory*`, `*Fixture*`) — reveal valid domain data shapes
3. For each finding a test changes — write a change record (see format below) and update the output file

**Phase 2 — Documentation Review**
1. Read `README.md` and all files in `docs/`
2. Extract: stated purpose (demo vs production), deployment model, external system references, known limitations, demo credentials
3. Apply findings to relevant output files — record each as a change record

**Phase 3 — Database Verification** *(if DB was connected in Agent 1)*
1. Run targeted confirmation queries for findings from Phases 1–2
2. Update any finding where live data contradicts or confirms Agent 1's assumption
3. **Conflict resolution** — when a test, doc, or DB result disagrees with Agent 1's code-based finding, don't average the two scores. Rank both against this Evidence Strength Hierarchy (highest wins): live DB > migration files > entity/ORM code > tests > repository code > naming convention > docs/git history (docs/git only win if they cite a hard constraint). The higher-ranked source wins; record both in the change record's `evidence_detail`.

**Phase 4 — Spot Check of Unreferenced Files**
1. List all source files referenced in the 13 output files
2. Open files from directories NOT yet covered: `*/Config*` `*/Extensions*` `*/HealthChecks*` `*/Cache*` `*/Background*` `*/Events*`
3. For each new file — check for missed caching layers, feature flags, background DB writers, health check dependencies
4. Record every new file read and whether it produced a finding

**Phase 5 — Cross-File Consistency Check**

| Check | Files |
|---|---|
| Same table count | `schema-catalogue.json` ↔ `erd.md` |
| PII columns match | `pii-inventory.json` ↔ `schema-catalogue.json` |
| Row counts match | `schema-catalogue.json` ↔ `migration-complexity.json` |
| Business rules in flow map | `hidden-business-rules.json` ↔ `data-flow-map.md` |
| Cache in both places | `data-source-inventory.json` ↔ `storage-pattern-analysis.md` |
| FK delete rules consistent | `schema-catalogue.json` ↔ `migration-complexity.json` |
| Canonical entity claims match actual table/usage evidence | `redundancy-analysis.json` ↔ `schema-catalogue.json` |
| Every table/column has a dictionary entry, and none invent meanings absent from code | `data-dictionary.md` ↔ `schema-catalogue.json` |
| Every concept in the conceptual model traces to a real aggregate root | `conceptual-data-model.md` ↔ `schema-catalogue.json` |
| Every PII table/column appears in the access matrix with cited evidence | `access-control-matrix.md` ↔ `pii-inventory.json` |

Fix every contradiction found. Record each as a CORRECTED change record.

**Phase 6 — Write `da-outputs/review-summary.md`**

Include these 6 sections:
1. **Overview** — files reviewed (13 of 13), total change count by type (ADDED/CORRECTED/ENRICHED)
2. **Quality scores** — overall confidence before vs. after review
3. **Key corrections** — the most significant CORRECTED change records, with file + finding
4. **Cross-file consistency results** — outcome of each Phase 5 check (pass/fixed)
5. **Open questions for Gate G1** — anything requiring business intent, legal input, or infrastructure sizing that code-reading alone can't resolve
6. **Gate G1 recommendation** — READY or NOT READY, with reason if not ready

---

## Output Format

**Change record (add to every updated output file):**
```json
{
  "change_id": "RC-007",
  "type": "CORRECTED",
  "finding_id": "storage-pattern-analysis.md — Caching",
  "what": "Original said 'Cache Type: None'. IMemoryCache IS active via CachedCatalogViewModelService (30s sliding TTL).",
  "evidence_source": "spot check",
  "evidence_detail": "src/Web/Services/CachedCatalogViewModelService.cs + ConfigureWebServices.cs:17",
  "confidence_before": 0.0,
  "confidence_after": 1.0,
  "phase_found": "Phase 4 spot check"
}
```

**Change types:**

| Type | Meaning |
|---|---|
| ADDED | New finding not in Agent 1 |
| CORRECTED | Agent 1 was wrong — now fixed |
| ENRICHED | Agent 1 was correct — now has more evidence |

---

## Error Handling

| If | Then |
|---|---|
| `da-outputs/` folder missing or has fewer than 10 files | Stop — ask user to run DA Agent 1 first |
| `schema-catalogue.json` is empty or has 0 tables | Stop — Agent 1 may not have completed |
| Spot check reveals fundamentally different architecture (event sourcing, CQRS read DB, multi-tenancy) | Stop — ask user if Agent 1 should re-run with this knowledge |
| Test contradicts an Agent 1 finding | Mark CORRECTED — never silently update without recording the change |
| Open question can be answered by reading more code | Read the code and answer it — do not escalate to Gate G1 |
| Open question requires business intent, legal input, or infrastructure sizing | Add to Gate G1 list with role assigned |

---

## Final Report to User

```
## 📋 DA Agent 2 — Review Complete

Files reviewed:   13 of 13
Changes made:     [N] ADDED, [N] CORRECTED, [N] ENRICHED

Quality scores:
  Before review:  [X.XX] overall
  After review:   [X.XX] overall

Key corrections:
  - [most important correction]
  - [second most important]

Open questions for Gate G1:  [N]
  → See da-outputs/review-summary.md

Gate G1 recommendation:  READY | NOT READY ([reason])
```

---

*DA Reverse Engineering System — Agent 2 of 2 | v2 | June 2026*
