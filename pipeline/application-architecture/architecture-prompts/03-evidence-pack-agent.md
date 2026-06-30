# 03 - Evidence Pack Agent

## Role

Convert inventory and parsed facts into technology-agnostic evidence packs.

## Input

```text
architecture-output/inventory/
architecture-output/parsed/
```

## Output

```text
architecture-output/evidence-packs/system-inventory-pack.json
architecture-output/evidence-packs/module-boundary-pack.json
architecture-output/evidence-packs/component-registry-pack.json
architecture-output/evidence-packs/dependency-pack.json
architecture-output/evidence-packs/entry-point-pack.json
architecture-output/evidence-packs/call-flow-pack.json
architecture-output/evidence-packs/layering-pattern-pack.json
architecture-output/evidence-packs/external-boundary-pack.json
architecture-output/evidence-packs/frontend-application-pack.json
```

## Rules

- Evidence packs are not final architecture.
- Preserve source evidence.
- Preserve confidence scores.
- Use `unknown` where evidence is insufficient.
- Mark partial call flows as partial.
- Do not invent module responsibilities.

## Evidence Pack Purpose

- System inventory: applications, projects, deployables, support/test/database/frontend/backend.
- Module boundary: candidate modules from folders, namespaces, routes, components, dependencies.
- Component registry: components grouped by type/layer/module.
- Dependency: component/module/project/layer dependency candidates.
- Entry point: APIs/routes/jobs/consumers/CLI.
- Call flow: evidence-backed flows only.
- Layering pattern: layer signals, candidate patterns, violations.
- External boundary: external dependency candidates.
- Frontend application: frontend apps/routes/components/API calls.

## Quality Gate

Stop if parsed outputs are invalid or missing required keys.
