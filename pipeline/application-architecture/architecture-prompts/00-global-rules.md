# 00 - Global Rules

Use this file for every Application Architecture extraction stage.

## Scope

This workflow reverse engineers Application Architecture from a legacy repository and produces SDLC reverse-engineering and forward-engineering inputs.

Do not perform business architecture, security deep dive, data migration design, cloud design, or testing strategy unless a later prompt explicitly asks for it.

## Safety

- Do not modify legacy application source code.
- Do not delete files.
- Do not refactor or format the legacy application.
- Do not install heavy dependencies without approval.
- Write generated outputs only under `architecture-output/`.
- Write analyzer tooling only under `tools/application_architecture_analyzer/`.

## Evidence Rules

- Every major claim must include source evidence.
- Use file paths and line numbers where available.
- Use confidence scores.
- If evidence is missing, write `unknown`.
- Add unresolved uncertainty to `architecture-output/final/open-questions.md` or the relevant stage output.
- Do not invent modules, flows, deployment topology, cloud platform, database ownership, queue ownership, or business rules.

## Ignore Rules

Do not analyze these as architecture source:

```text
.git/
node_modules/
bin/
obj/
target/
dist/
build/
coverage/
logs/
generated/
*.min.js
*.map
compiled binaries
large generated files
```

## Process Rule

Parse first, reason second:

```text
inventory -> parsed facts -> evidence packs -> final architecture -> enterprise forward engineering -> quality review
```

Never jump directly from raw source files to final architecture.
