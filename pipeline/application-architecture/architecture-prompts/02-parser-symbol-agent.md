# 02 - Parser / Symbol Extraction Agent

## Role

Extract structured facts from source files selected by inventory. This stage produces facts, not final architecture.

## Input

```text
architecture-output/inventory/
```

## Output

```text
architecture-output/parsed/symbol-registry.json
architecture-output/parsed/route-registry.json
architecture-output/parsed/dependency-candidates.json
architecture-output/parsed/entry-point-candidates.json
```

## Extraction Priorities

Use language/framework-specific parsing where available, then conservative regex/path heuristics as fallback.

Extract:

- classes/types/components
- methods/functions
- imports/usings/requires
- constructor/property injection
- DI registrations
- route declarations
- frontend routes
- API calls
- component calls
- repositories/data access
- scheduled jobs, consumers, batch jobs, CLI/bootstrap entries

## Confidence Rules

High confidence:

- explicit class/type declaration
- explicit route attribute or framework route call
- explicit constructor injection
- explicit project reference

Medium confidence:

- path/name/framework heuristic
- method-call candidate without full type resolution

Low confidence:

- ambiguous dynamic expression
- unknown module ownership
- unresolved external target

## Do Not

- Do not generate final module maps.
- Do not write architecture pattern conclusions.
- Do not produce migration plans.

## Quality Gate

Stop if inventory inputs are invalid. Every extracted item must include source file and confidence.
