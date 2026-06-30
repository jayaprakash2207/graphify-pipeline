---
name: da-extractor
description: Full data architecture reverse engineering. Use when user says "reverse engineer this", 
  "analyse my data architecture", "document the schema", "map the database", or drops a codebase 
  for data analysis. Do NOT use for general code review, UI analysis, or business logic questions.
---

# DA Agent 1 — Data Architecture Extractor
> Pair with: `DA_REVIEW_PROMPT.md` | Version: June 2026 v2

---

## When to Activate

- User says "reverse engineer this project", "analyse my data architecture", "document the schema"
- User drops a codebase folder and asks about data, tables, entities, or migration
- User asks "what databases does this use?" or "map the data flow"
- `DA_REVIEW_PROMPT.md` is present and user wants a full DA pipeline run

---

## What This Skill Does NOT Do

- Does not interpret business intent or make design decisions — surfaces facts only
- Does not produce Business Requirements Documents (BRD) — that is Agent 2's job
- Does not review UI, frontend, or non-data code
- Does not write new code or fix bugs
- Does not skip the database connection and silently fall back to code-only — if DB is unreachable, it says exactly why

---

## Steps

**Phase 0 — Auto-Detection** *(always first, no files opened yet)*
1. Scan folder structure — detect language, framework, ORM, database engine, migration tool
2. Extract ALL connection strings from config files — record host, port, database name, username
3. List all entity files, route files, config files, integration clients
4. Produce a chunk plan — one chunk per domain

**Phase 1 — Code Discovery** *(read entities, migrations, services, queries)*
1. Read all entity/model classes — fields, types, validation rules, relationships
2. Read all migration files chronologically — columns, indexes, FK rules, sequences
3. Read all repository and query classes — specifications, raw SQL, N+1 risks
4. Read service classes — transaction boundaries, business rules in constructors
5. **Mandatory spot check** — read at least 5 files from: `*/Config*` `*/Extensions*` `*/HealthChecks*` `*/Cache*` `*/Background*` — look for caching layers, feature flags, background DB writers, and health check dependencies
6. **Business-meaning & governance capture** — read XML doc comments, README/glossary text, validation messages, `[Authorize]` attributes and role/policy names, and check for soft-delete flags or audit columns (`IsDeleted`, `CreatedAt`, etc.). This evidence feeds the data dictionary, conceptual model, retention policy, and access control matrix.
7. **Canonical / shadow entity detection** — for every business concept that appears more than once (e.g. "customer" represented as `AspNetUsers`, `Buyer`, and a loose `BuyerId` string), identify which representation is canonical (source of truth) and which are shadow/duplicate. Check whether each representation is actually constructed/queried anywhere — an entity that is only ever defined but never instantiated is a strong shadow signal.

**Phase 2 — Database Connection** *(mandatory — no skipping)*
1. Find the database CLI tool on this machine
2. Run a connection test command
3. On success — run row counts, schema verification, FK rules, indexes, sequences, triggers, DQ checks. **If the live result conflicts with what code/migrations suggested, the live DB wins.** Use this Evidence Strength Hierarchy (highest wins): live DB > migration files > entity/ORM code > repository code > naming convention > docs/README/git history (docs only win if they cite a hard constraint, e.g. a documented legal retention period). Document both sides and which one prevailed.
4. On failure — document exact error + command run, continue code-only
5. Repeat for every database found in Phase 0

**Phase 3 — Write Output Files** *(write each file as its phase completes — do not batch)*

| # | File | Write After |
|---|---|---|
| 1 | `da-outputs/schema-catalogue.json` | Phase 2 complete |
| 2 | `da-outputs/erd.md` | Phase 2 complete |
| 3 | `da-outputs/data-source-inventory.json` | Phase 1e + Phase 2 complete |
| 4 | `da-outputs/data-flow-map.md` | Phase 1 complete |
| 5 | `da-outputs/pii-inventory.json` | Phase 2 complete |
| 6 | `da-outputs/data-quality-report.md` | Phase 2 complete |
| 7 | `da-outputs/migration-complexity.json` | Phase 2 complete |
| 8 | `da-outputs/hidden-business-rules.json` | Phase 1 complete |
| 9 | `da-outputs/storage-pattern-analysis.md` | Phase 1e complete |
| 10 | `da-outputs/redundancy-analysis.json` | Phase 1 step 7 complete |
| 11 | `da-outputs/data-dictionary.md` | Phase 1 step 6 complete |
| 12 | `da-outputs/conceptual-data-model.md` | Phase 1 step 6 complete |
| 13 | `da-outputs/access-control-matrix.md` | Phase 1 step 6 + Phase 2 complete |

**Phase 4 — Self-Check** *(fix any ❌ before finishing)*

| Check | Pass? |
|---|---|
| DB connection attempted? (YES or exact error documented) | |
| `db_connection` field set to CONNECTED or CODE-ONLY with reason? | |
| Row counts from live DB where connected? | |
| Caching section in `storage-pattern-analysis.md`? | |
| At least 5 files read from `*/Config*` `*/Extensions*` `*/HealthChecks*`? | |
| Every UNKNOWN value has an inline reason? | |
| All soft references listed in `erd.md` WARNING section? | |
| Caching TTL documented as a business rule in `hidden-business-rules.json`? | |
| Code-vs-DB conflicts resolved using Evidence Strength Hierarchy (not guessed)? | |
| At least one canonical/shadow entity check completed — even if the result is "no duplicates found"? | |
| Every table/column in `schema-catalogue.json` has a matching entry in `data-dictionary.md`? | |
| Every role found in `[Authorize]` attributes appears in `access-control-matrix.md`? | |
| `conceptual-data-model.md` uses business language only — no table names, types, or FK syntax? | |

---

## Output Format

All 13 files go in `da-outputs/`. Create the folder if absent.

**Real example of a correct `db_connection` value:**
```
"db_connection": "CONNECTED — psql at C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe"
"db_connection": "CODE-ONLY — connection refused at localhost:5432. Command run: psql -h localhost -p 5432 -U postgres -d eShopCatalog -c \\dt"
```

**Real example of a correct volume value:**
```
"volume": "LOW",
"volume_detail": "0 rows — live DB confirmed. No real orders placed yet."

"volume": "UNKNOWN",
"volume_detail": "DB not connected — connection refused at localhost:5432. Command attempted: psql -h localhost -p 5432 -U postgres -d eShopCatalog -c \\dt"
```

**Confidence scoring scale** (use for any `confidence` field):

| Score | Meaning |
|---|---|
| 1.0 | Confirmed by live DB query |
| 0.9 | Confirmed by migration file |
| 0.8 | Confirmed by entity/ORM code (EF model, annotations) |
| 0.75 | Confirmed by repository/query code |
| 0.70 | Inferred from naming convention or framework default only |

Anything below 0.70 should be marked `UNKNOWN` with an inline reason rather than guessed.

---

## Error Handling

| If | Then |
|---|---|
| DB connection fails with auth error | Run `dotnet ef database update` (or equivalent), retry once |
| DB connection fails with "connection refused" | Mark CODE-ONLY with exact error + command. Check for `docker-compose.yml` and note start command. |
| Entity/model files not found after full folder scan | Stop and ask the user |
| More than 40% of files are binary with no source | Stop and ask the user |
| Connection string is encrypted or redacted | Stop and ask the user |
| Caching class found in `*/Services*` | Document in BOTH `data-source-inventory.json` AND `storage-pattern-analysis.md` |
| FK ON DELETE = NO ACTION | Flag in `data-quality-report.md` — deleting parent row with children will error |
| File appears relevant in multiple domains | Read once, mark 🔁 SHARED, reference by path in all chunks |
| Confidence cannot reach 0.80 | Include the finding, mark ⚠️ LOW CONFIDENCE — Agent 2 to verify |

---

## Final Report to User

```
## 📋 DA Agent 1 — Complete

Language(s):        [detected]
Framework(s):       [detected]  
Database(s):        [detected + host:port]
DB connection:      CONNECTED | CODE-ONLY (reason)
Files scanned:      [N]
Domains found:      [N] — [list]

Outputs written:
  da-outputs/schema-catalogue.json         ✅
  da-outputs/erd.md                        ✅
  da-outputs/data-source-inventory.json    ✅
  da-outputs/data-flow-map.md              ✅
  da-outputs/pii-inventory.json            ✅
  da-outputs/data-quality-report.md        ✅
  da-outputs/migration-complexity.json     ✅
  da-outputs/hidden-business-rules.json    ✅
  da-outputs/storage-pattern-analysis.md   ✅
  da-outputs/redundancy-analysis.json      ✅
  da-outputs/data-dictionary.md            ✅
  da-outputs/conceptual-data-model.md      ✅
  da-outputs/access-control-matrix.md      ✅

⚠️ Validation Queue: [list any LOW confidence items]

🤝 Handoff to DA Agent 2:
[3–5 sentences: connection status, key entities, most important gaps,
what Agent 2 should investigate first]

Ready for DA Agent 2 → run DA_REVIEW_PROMPT.md
```

---

*DA Reverse Engineering System — Agent 1 of 2 | v2 | June 2026*
