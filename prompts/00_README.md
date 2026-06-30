# Pipeline Prompts

This folder contains all LLM prompts used by the graphify reverse engineering pipeline, plus notes for automated stages that require no LLM prompt.

---

## Prompts Overview

| File | Stage | Agent | What It Does |
|---|---|---|---|
| `01_BA_Agent1_StructuralScout.md` | BA Layer — Pass 1 | BA Agent 1 | Fast, broad structural scan of the codebase. Produces 6 structured inventory files (domain map, entity inventory, state registry, role snapshot, capability skeleton, integration map) used by BA Agent 2. |
| `02_BA_Agent2_DeepAnalyst.md` | BA Layer — Pass 2 | BA Agent 2 | Deep logic-level analysis using Agent 1's 6 inventory files. Produces 8 final Business Architecture artifacts in plain business language (capability map, process flows, business rules catalog, stakeholder matrix, value stream maps, pain point report, automation opportunities). |
| `03_DA_Agent1_DataExtractor.md` | DA Layer — Pass 1 | DA Agent 1 | Full data architecture extraction. Connects to the live database (mandatory), reads entities, migrations, repositories, and config. Produces 13 output files (schema catalogue, ERD, data dictionary, PII inventory, data quality report, access control matrix, etc.). |
| `04_DA_Agent2_DataReviewer.md` | DA Layer — Pass 2 | DA Agent 2 | Reviews and enriches DA Agent 1's 13 output files using test evidence, documentation, live DB queries, and cross-file consistency checks. Produces a `review-summary.md` and a Gate G1 readiness recommendation. |
| `05_TA_Agent1_StackScout.md` | TA Layer — Pass 1 | TA Agent 1 | Fast, broad technology architecture scan. Reads package manifests, Dockerfiles, IaC, CI/CD pipelines (with tool invocations), config files, and API contracts. Produces 6 structured inventory files. |
| `06_TA_Agent2_DeepAnalyst.md` | TA Layer — Pass 2 | TA Agent 2 | Deep pattern-level analysis using Agent 1's 6 inventory files. Produces 8 final Technology Architecture artifacts (stack assessment, architecture pattern catalog, NFR registry, technical debt register, component interaction map, security assessment, operational assessment with evidence-based CI/CD maturity). |
| `07_AA_Pipeline_Note.md` | AA Layer | Automated | NOTE ONLY — no LLM prompt. The AA pipeline is fully automated Python using Tree-sitter AST parsing. Extracts 310+ components, 55+ APIs, dependencies, and generates architecture diagrams automatically. |
| `08_Foundation_Synthesis.md` | Foundation Layer | Foundation Agent | Reconciles all four layer outputs (BA, DA, AA, TA) into a single Enterprise Knowledge Graph and 4 read-only foundation views (canonical model, architecture inventory, traceability matrix, forward engineering input map). |

---

## Run Order

```
01 → 02 → 03 → 04 → 05 → 06 → 07 (auto) → 08
```

Full sequence:

1. **01 — BA Agent 1** — run first; produces the 6 inventory files that 02 needs
2. **02 — BA Agent 2** — run after 01 completes; consumes 01's output; produces 8 BA documents
3. **03 — DA Agent 1** — run against the same codebase; produces 13 DA output files
4. **04 — DA Agent 2** — run after 03 completes; enriches and validates 03's 13 files
5. **05 — TA Agent 1** — run against the same codebase; produces 6 TA inventory files
6. **06 — TA Agent 2** — run after 05 completes; produces 8 TA documents
7. **07 — AA Pipeline** — runs automatically via `aa_runner.py`; no LLM required
8. **08 — Foundation Synthesis** — run last, after all four layers (BA, DA, TA, AA) are complete; merges everything into the Enterprise Knowledge Graph

---

## Agent 1 vs Agent 2 Pattern

Every architecture layer (BA, DA, TA) uses a two-agent pattern:

| Agent | Role | Reading Depth | Output |
|---|---|---|---|
| Agent 1 | Scanner / Mapper | Shallow — signatures, declarations, config keys, state values | Structured inventory tables (ground truth for naming) |
| Agent 2 | Analyst | Deep — method bodies, validation logic, call chains, pipeline steps | Human-readable documentation (business or technical) |

Agent 1 runs first, always. Agent 2 cannot start without Agent 1's output files.

Agent 1 **never interprets** — it maps what exists.
Agent 2 **never re-derives** — it traces and expands what Agent 1 mapped.

---

## Pipeline vs Manual Usage

| Prompt | Used by Pipeline Runner? | Manual-Only Scenarios |
|---|---|---|
| `01_BA_Agent1_StructuralScout.md` | Yes — `layer2_runner.py` loads this prompt | Also usable manually in Claude chat with a codebase |
| `02_BA_Agent2_DeepAnalyst.md` | Yes — `layer3_runner.py` loads this prompt | Also usable manually after Agent 1 completes |
| `03_DA_Agent1_DataExtractor.md` | Yes — `da_agent1_runner.py` loads this prompt | Also usable manually |
| `04_DA_Agent2_DataReviewer.md` | Yes — `da_agent2_runner.py` loads this prompt | Also usable manually after Agent 1 completes |
| `05_TA_Agent1_StackScout.md` | Yes — `ta_agent1_runner.py` loads this prompt | Also usable manually |
| `06_TA_Agent2_DeepAnalyst.md` | Yes — `ta_agent2_runner.py` loads this prompt | Also usable manually after Agent 1 completes |
| `07_AA_Pipeline_Note.md` | N/A — AA is fully automated Python | Documentation only |
| `08_Foundation_Synthesis.md` | Yes — `foundation_runner.py` embeds this prompt | Run manually only after all four layers complete |

---

## Prompt File Naming Convention

```
NN_Layer_AgentN_RoleName.md
```

- `NN` — two-digit run order (01–08)
- `Layer` — BA / DA / TA / AA / Foundation
- `AgentN` — Agent1 / Agent2 / Pipeline (automated) / (omitted for Foundation)
- `RoleName` — short descriptor of the agent's role

---

*graphify-pipeline/prompts | June 2026*
