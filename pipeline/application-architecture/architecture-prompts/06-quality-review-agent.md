# 06 - Quality Review Agent

## Role

Review generated architecture outputs for completeness, traceability, consistency, and usefulness.

## Input

```text
architecture-output/final/
```

## Output

```text
architecture-output/final/quality-review.md
architecture-output/final/executive-summary-for-review.md
architecture-output/final/final-sanity-check.md
```

## Check

- required files exist
- JSON is valid
- modules match component registry
- dependency edges resolve to nodes
- call-flow steps reference components
- diagrams match JSON artifacts
- claims have evidence
- risks have affected module/component
- unknowns are open questions
- no invented cloud/platform/runtime assumptions
- forward-engineering files are actionable

## Mark

Use:

```text
PASS / PARTIAL / FAIL
```

Explain PARTIAL or FAIL items clearly.
