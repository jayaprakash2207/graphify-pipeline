# Application Architecture Extraction Workflow

This folder contains the repeatable automation for the architecture extraction process.

The Markdown prompt files are the governance layer:

- `AGENTS.md`
- `application_architecture_extraction_agent_prompt.md`

The Python scripts are the deterministic execution layer.

## Why This Approach

Using prompts alone is not enough for a production-grade extraction because prompts cannot reliably:

- scan files the same way every run
- validate JSON schemas
- count components and dependencies
- detect missing graph nodes
- regenerate review artifacts consistently
- stop the pipeline when a phase fails

The best approach is therefore:

```text
Markdown instructions = rules and acceptance criteria
Python phase scripts = repeatable extraction and validation
Pipeline runner = one command that runs the full process in order
```

## One-Command Pipeline

From the repo root:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --repo-root . --output-root architecture-output
```

The runner executes:

1. `scan_inventory.py`
2. `extract_parsed_facts.py`
3. `generate_evidence_packs.py`
4. `generate_final_architecture.py`
5. `generate_enterprise_forward_engineering.py`
6. `generate_review_artifacts.py`

It also validates each previous stage before starting the next stage and writes both timestamped and latest run summaries:

```text
architecture-output/logs/pipeline-run-summary-YYYYMMDD-HHMMSS.json
architecture-output/logs/latest-pipeline-run-summary.json
architecture-output/logs/pipeline-run-summary.json
```

`pipeline-run-summary.json` remains for compatibility. `latest-pipeline-run-summary.json` is the stable pointer for automation, and the timestamped files preserve run history.

## Phase Outputs

### 1. Inventory

Output folder:

```text
architecture-output/inventory/
```

Purpose: identify files, languages, projects, ignored files, deployable clues, and technology indicators.

### 2. Parsed Facts

Output folder:

```text
architecture-output/parsed/
```

Purpose: extract structured components, routes, entry points, imports, dependencies, methods, and classifications.

### 3. Evidence Packs

Output folder:

```text
architecture-output/evidence-packs/
```

Purpose: group raw parsed facts into technology-agnostic evidence packs for system inventory, module boundaries, components, dependencies, entry points, call flows, layering, external boundaries, and frontend application facts.

### 4. Final Architecture

Output folder:

```text
architecture-output/final/
```

Purpose: create the human-readable and machine-readable architecture package for SDLC reverse engineering and forward engineering.

### 5. Enterprise Forward Engineering

Output files:

```text
architecture-output/final/business-capability-map.json
architecture-output/final/business-capability-map.md
architecture-output/final/module-consolidation-map.json
architecture-output/final/module-consolidation-map.md
architecture-output/final/service-boundary-options.md
architecture-output/final/migration-wave-plan.md
architecture-output/final/preserve-redesign-retire-map.md
architecture-output/final/api-contract-preservation-map.json
architecture-output/final/data-ownership-map.md
architecture-output/final/test-runtime-evidence-map.json
architecture-output/final/test-runtime-evidence-map.md
architecture-output/final/confidence-report.md
architecture-output/final/architecture-decision-inputs.md
architecture-output/final/forward-engineering-backlog.md
```

Purpose: convert the reverse-engineered architecture package into enterprise forward-engineering inputs: candidate capabilities, API contracts to preserve or review, service-boundary options, migration waves, data ownership review, architecture decisions, confidence gaps, and backlog items.

### 6. Review Artifacts

Output files:

```text
architecture-output/final/quality-review.md
architecture-output/final/executive-summary-for-review.md
architecture-output/final/final-sanity-check.md
```

Purpose: provide production-grade quality gates, manager/architect summary, and internal consistency checks.

## Partial Runs

Run from a specific phase:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --from-phase evidence
```

Run through a specific phase:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --to-phase final
```

Run only review regeneration:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --from-phase review --to-phase review
```

Run only enterprise forward-engineering regeneration:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --from-phase enterprise-forward --to-phase enterprise-forward
```

## Validation And Quality Gates

The runner performs stage-specific contract validation:

- inventory JSON is validated before parsed extraction
- parsed JSON is validated before evidence-pack generation
- evidence packs are validated before final architecture generation
- final JSON is validated before review artifact generation

The runner stops if required files, required top-level keys, or JSON validity checks fail.

Quality gates default to warning mode:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --max-fail 0 --max-invalid-graph-edges 0
```

Use strict mode when the run should fail on gate violations:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --strict --max-fail 0 --max-partial 5 --max-invalid-graph-edges 0 --max-unknown-components 50
```

The source modification guard is enabled by default. It hashes legacy source files before and after the run, ignoring `architecture-output/` and `tools/application_architecture_analyzer/`. Disable it only for troubleshooting:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --no-source-guard
```

## Safety Rules

- Do not modify legacy application source code.
- Keep generated outputs under `architecture-output/`.
- Keep analyzer automation under `tools/application_architecture_analyzer/`.
- Treat `Unknown` as a valid result when code evidence is insufficient.
- Do not claim a module, flow, deployment model, or external integration without evidence.

## Artifact Meaning

```text
inventory/       raw repo discovery
parsed/          extracted structured code facts
evidence-packs/  source-backed evidence bundles
final/           architecture package for human and SDLC use
final/*forward*  forward-engineering decisions, waves, backlog, and confidence inputs
logs/            pipeline run metadata
```

The final package is what managers, architects, and engineering teams review.
