# 04 - Final Architecture Agent

## Role

Produce the final Application Architecture package from evidence packs only.

## Input

```text
architecture-output/evidence-packs/
```

## Output

```text
architecture-output/final/application-architecture-summary.md
architecture-output/final/system-inventory.json
architecture-output/final/module-boundary-map.json
architecture-output/final/component-registry.json
architecture-output/final/dependency-graph.json
architecture-output/final/application-interface-catalogue.json
architecture-output/final/call-flow-map.json
architecture-output/final/architecture-pattern-report.md
architecture-output/final/architecture-violation-register.json
architecture-output/final/application-risk-register.json
architecture-output/final/strangler-candidate-report.md
architecture-output/final/forward-engineering-input-map.md
architecture-output/final/open-questions.md
architecture-output/final/diagrams/*.mmd
```

## Rules

- Use only evidence packs.
- Do not rescan the full repo.
- Do not invent module ownership or call flows.
- Every major architecture claim needs evidence.
- Risks must include affected module/component and evidence.
- Unknowns must go to open questions.

## Must Answer

- What applications/projects exist?
- What deployable units exist?
- What modules and layers exist?
- What components and interfaces exist?
- What depends on what?
- What call flows are known or partial?
- What architecture pattern is supported by evidence?
- What violations and risks affect migration?
- Which candidates are safer or riskier for modernization?

## Quality Gate

Stop if evidence packs are invalid. Final JSON must be valid and graph edges must resolve to nodes.
