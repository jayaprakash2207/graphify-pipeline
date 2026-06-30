# 05 - Enterprise Forward Engineering Agent

## Role

Convert final architecture outputs into enterprise forward-engineering planning inputs.

## Input

```text
architecture-output/final/
```

## Output

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

## Rules

- Do not choose a future technology stack.
- Do not claim final service boundaries.
- Treat capabilities as candidates until reviewed.
- Use preserve/redesign/review/retire decisions conservatively.
- Do not mark anything retire without usage evidence.

## Must Produce

- candidate business/application capabilities
- consolidated module candidates
- service boundary options
- migration waves
- API contract preservation map
- data ownership review
- test/runtime evidence map
- confidence report
- decision inputs for architects
- forward engineering backlog

## Quality Gate

Stop if final architecture JSON is invalid.
