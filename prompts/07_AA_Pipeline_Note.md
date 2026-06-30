# AA Pipeline Note — Application Architecture (Fully Automated)

## No LLM Prompt Required

The Application Architecture (AA) pipeline stage is **fully automated Python** — it requires no LLM prompt and no manual agent interaction.

## What the AA Pipeline Does

The AA pipeline uses **Tree-sitter AST parsing** to extract the following directly from source code without any LLM call:

- **310+ components** — classes, modules, interfaces, enums, and functions extracted via static AST analysis
- **55 APIs** — REST endpoints, GraphQL resolvers, gRPC service definitions, and event handlers discovered from route registrations and decorators
- **Dependencies** — import/require/using statements parsed to build a full intra-project and third-party dependency graph
- **Architecture diagrams** — component diagrams, dependency graphs, and layering views generated automatically from the extracted graph

## How to Run

```bash
python pipeline/application-architecture/aa_runner.py --input output/<project-name>
```

The runner reads from Layer 1 extraction output and writes to `aa-outputs/` in the project output folder.

## Outputs Written

| File | Contents |
|---|---|
| `aa-outputs/components.json` | All 310+ detected components with types, file locations, and metadata |
| `aa-outputs/apis.json` | All 55+ detected API endpoints with methods, paths, and handler references |
| `aa-outputs/dependencies.json` | Full dependency graph (intra-project + third-party) |
| `aa-outputs/architecture-diagram.md` | Auto-generated Mermaid component diagram |
| `aa-outputs/layer-map.json` | Components grouped by architectural layer (controller / service / repository / domain) |
| `aa-outputs/aa-summary.md` | Plain-English summary of the application architecture |

## How It Fits in the Pipeline

The AA stage runs **after Layer 1** (Python extraction) and **before Foundation Synthesis** (prompt 08).

Its outputs feed the Foundation Synthesis agent as the `aa-outputs/` context — providing the application-layer component and API inventory that the Foundation agent merges with BA, DA, and TA outputs into the Enterprise Knowledge Graph.

## No LLM Prompt

Because Tree-sitter AST parsing is deterministic and code-accurate, the AA stage does not benefit from or require an LLM. Running an LLM over raw AST output would add cost and latency with no accuracy gain.

If you need a human-readable explanation of a specific component or API cluster, use:
```
graphify explain "<component-name>"
```

---

*AA Pipeline — Fully Automated | Tree-sitter AST | June 2026*
