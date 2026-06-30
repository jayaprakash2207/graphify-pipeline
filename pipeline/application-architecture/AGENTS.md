# AGENTS.md - Application Architecture Extraction Orchestrator

## Purpose

This repository uses a staged Application Architecture extraction workflow for SDLC reverse engineering and forward engineering.

Do not place every instruction in this file. This file is only the lightweight orchestrator. Stage-specific rules live under:

```text
architecture-prompts/
```

## Golden Rules

- Do not modify legacy application source code.
- Do not invent architecture facts.
- Use `unknown` when evidence is missing.
- Every major claim must have source evidence.
- Keep generated outputs under `architecture-output/`.
- Keep analyzer tooling under `tools/application_architecture_analyzer/`.
- Parser/structured extraction comes before architecture reasoning.

## Stage Order

Run the workflow in this order:

```text
1. Inventory
2. Source chunking
3. Parser / symbol extraction
4. Semantic extraction where supported
5. Evidence packs
6. Final architecture
7. Enterprise forward engineering
8. Enterprise application architecture blueprint
9. Quality review
10. Workflow audit when requested
```

Use the stage prompts:

```text
architecture-prompts/00-global-rules.md
architecture-prompts/01-inventory-agent.md
architecture-prompts/02-parser-symbol-agent.md
architecture-prompts/03-evidence-pack-agent.md
architecture-prompts/04-final-architecture-agent.md
architecture-prompts/05-enterprise-forward-engineering-agent.md
architecture-prompts/06-quality-review-agent.md
architecture-prompts/07-workflow-audit-agent.md
```

## One-Command Workflow

From the repository root:

```powershell
python tools/application_architecture_analyzer/run_architecture_extraction.py --repo-root . --output-root architecture-output
```

## Required Discipline

Each stage must use only the approved input from the previous stage:

```text
Inventory reads repo source.
Source chunking reads inventory plus relevant source files.
Parser reads inventory, source chunks, and relevant source files.
Semantic extraction reads inventory plus relevant source files when a supported compiler backend is available.
Evidence reads inventory and parsed outputs.
Final architecture reads evidence packs.
Enterprise forward engineering reads final architecture outputs.
Enterprise application architecture blueprint reads final and forward-engineering outputs.
Quality review reads generated outputs.
```

Do not jump directly from raw repo files to final architecture conclusions.

## Current Acceptance Standard

The output is acceptable only when it is:

- source-backed
- machine-readable
- human-readable
- diagrammed
- explicit about unknowns
- useful for migration and forward engineering
- validated by quality review
