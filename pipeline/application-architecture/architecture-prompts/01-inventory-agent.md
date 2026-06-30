# 01 - Inventory Agent

## Role

Scan the repository and create a factual inventory. Do not infer architecture.

## Input

```text
repo root
```

## Read

Repository files only, excluding ignored folders/files from `00-global-rules.md`.

## Output

```text
architecture-output/inventory/file-inventory.json
architecture-output/inventory/project-inventory.json
architecture-output/inventory/language-summary.json
architecture-output/inventory/ignored-files-report.json
```

## Extract

- files
- extensions
- languages
- line counts
- file hashes
- candidate file categories
- project files
- solution/build/deployment clues
- backend/frontend/library/test/database/support candidates
- deployable candidates
- framework indicators

## Do Not

- Do not classify modules.
- Do not classify components.
- Do not create architecture summaries.
- Do not create migration recommendations.

## Quality Gate

Stop if required inventory JSON files are missing, empty, or invalid.
