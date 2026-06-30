# 07 - Workflow Audit Agent

## Role

Audit the workflow itself for enterprise readiness and reuse.

## Input

```text
AGENTS.md
architecture-prompts/
tools/application_architecture_analyzer/
architecture-output/
```

## Output

```text
architecture-output/final/architecture-workflow-audit.md
architecture-output/final/missing-output-fixes.md
architecture-output/final/fix-implementation-summary.md when fixes are made
```

## Check

- stage completeness
- stage input/output contracts
- source modification guard
- schema validation
- run history
- graph normalization
- quality gates
- no repo-specific hardcoding
- parser breadth and extension points
- hallucination handling
- forward-engineering usefulness

## Verdict

Use one:

```text
ENTERPRISE READY
MOSTLY READY WITH MINOR FIXES
NOT READY
```

Include score out of 100 and specific fixes.
