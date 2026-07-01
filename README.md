# Graphify Pipeline — Enterprise Knowledge Graph Generator

Reverse-engineer **any codebase** into a complete Enterprise Knowledge Graph + 20 Forward Engineering documents using AST extraction and 8 Claude AI agents.

> **Sample output is already included** — browse `sample-output/` to see what the pipeline produces from eShopOnWeb (.NET) before running anything.

---

## See the Sample Output First

The `sample-output/` folder contains a fully generated example from **eShopOnWeb** (Microsoft's official .NET reference e-commerce app). No setup needed — just open:

| File | What you'll see |
|---|---|
| [`sample-output/graphify-out/graph.html`](sample-output/graphify-out/graph.html) | Interactive structural graph — open in any browser |
| [`sample-output/graphify-out/GRAPH_REPORT.md`](sample-output/graphify-out/GRAPH_REPORT.md) | Domain clusters, god nodes, architecture boundaries |
| [`sample-output/foundation/ENTERPRISE_KNOWLEDGE_GRAPH.json`](sample-output/foundation/ENTERPRISE_KNOWLEDGE_GRAPH.json) | 173 nodes, 95% HIGH confidence |
| [`sample-output/foundation/CANONICAL_ENTERPRISE_MODEL.md`](sample-output/foundation/CANONICAL_ENTERPRISE_MODEL.md) | Human-readable architecture overview |
| [`sample-output/forward-engineering/01_BRD.md`](sample-output/forward-engineering/01_BRD.md) | Business Requirements — 37 rules extracted |
| [`sample-output/forward-engineering/13_SECURITY_ARCHITECTURE.md`](sample-output/forward-engineering/13_SECURITY_ARCHITECTURE.md) | 6 critical production blockers identified |
| [`sample-output/forward-engineering/18_DEPLOYMENT_ARCHITECTURE.md`](sample-output/forward-engineering/18_DEPLOYMENT_ARCHITECTURE.md) | Full Docker-Compose + Azure CI/CD YAML |
| [`sample-output/forward-engineering/16_GENERATION_MANIFEST.json`](sample-output/forward-engineering/16_GENERATION_MANIFEST.json) | 106 nodes mapped to code-generation targets |

---

## Setup (One Time)

### Step 1 — Install Python 3.11+
Download from [python.org](https://www.python.org/downloads/). Verify:
```bash
python --version
```

### Step 2 — Install Node.js (for Claude CLI)
Download from [nodejs.org](https://nodejs.org/). Verify:
```bash
node --version
```

### Step 3 — Install Claude Code CLI and log in
```bash
npm install -g @anthropic/claude-code
claude login
```
This opens a browser to authenticate with your Anthropic account. **Required — all 8 AI agents run through Claude Code.**

### Step 4 — Install Graphify
```bash
pip install graphify-ai
```

### Step 5 — Install pipeline dependencies
```bash
pip install -r requirements.txt
```

---

## Run the Pipeline (Single Command)

```bash
python run.py --source "https://github.com/dotnet-architecture/eShopOnWeb"
```

That's it. The pipeline will:
1. Clone the repo
2. Extract all code, config, and database objects
3. Build the structural knowledge graph (Graphify)
4. Run 8 Claude AI agents across 4 architecture layers
5. Synthesize everything into an Enterprise Knowledge Graph
6. Produce 20 Forward Engineering documents

**Other usage examples:**
```bash
# Run on a local folder
python run.py --source "C:/path/to/your/project" --output ./my-results

# Skip Graphify if already done
python run.py --source "C:/path/to/project" --skip-graphify

# Custom output folder
python run.py --source "https://github.com/org/repo" --output ./my-output
```

**Expected run time:** ~1.5 to 2 hours for a medium-sized repo (200-500 files).

---

## What You Get

After the run, your output folder contains:

```
your-output/
├── graphify-out/                  ← Structural graph
│   ├── graph.html                 ← Open in browser — interactive visual
│   ├── graph.json                 ← Raw graph data
│   └── GRAPH_REPORT.md            ← Domain clusters and god nodes
│
├── ba_documents/                  ← 10 Business Architecture docs
│   ├── 01_capability_map.md
│   ├── 02_value_stream.md
│   ├── 03_process_models.md
│   ├── 04_business_rules.md
│   ├── 05_data_model.md
│   ├── 06_stakeholder_map.md
│   ├── 07_kpis_metrics.md
│   ├── 08_motivation_model.md
│   ├── 09_operating_model.md
│   └── 10_business_roadmap.md
│
├── da-outputs/                    ← 14 Data Architecture docs
├── ta-outputs/                    ← 14 Technology Architecture docs
├── aa-outputs/                    ← 32 Application Architecture docs
│
├── foundation/                    ← Enterprise Knowledge Graph
│   ├── ENTERPRISE_KNOWLEDGE_GRAPH.json
│   ├── CANONICAL_ENTERPRISE_MODEL.md
│   ├── ARCHITECTURE_INVENTORY.md
│   ├── TRACEABILITY_MATRIX.md
│   └── FORWARD_ENGINEERING_INPUT_MAP.md
│
└── forward-engineering/           ← FINAL OUTPUT — 20 documents
    ├── 01_BRD.md                  ← Business Requirements
    ├── 02_BUSINESS_CAPABILITY_MODEL.md
    ├── 03_USE_CASE_SPECIFICATION.md
    ├── 04_BUSINESS_PROCESS_MODEL.md
    ├── 05_DOMAIN_MODEL.md
    ├── 06_DATA_DICTIONARY.md
    ├── 07_DATA_MODEL_SPECIFICATION.md
    ├── 08_ERD.md
    ├── 09_DATA_FLOW_DIAGRAM.md
    ├── 10_SERVICE_CATALOG.md
    ├── 11_API_CONTRACT_SPECIFICATION.md
    ├── 12_TECHNOLOGY_BLUEPRINT.md
    ├── 13_SECURITY_ARCHITECTURE.md
    ├── 14_NFR_SPECIFICATION.md
    ├── 15_FORWARD_ENGINEERING_SPECIFICATION.md
    ├── 16_GENERATION_MANIFEST.json
    ├── 17_FORWARD_ENGINEERING_READINESS_REPORT.md
    ├── 18_DEPLOYMENT_ARCHITECTURE.md
    ├── 19_FRONTEND_ARCHITECTURE.md
    └── 20_UI_UX_SPECIFICATION.md
```

---

## How the Pipeline Works

```
Your Codebase
     │
     ▼
Step 1 — Graphify Extract       (AST parsing, no AI, ~5 min)
     │    Finds: classes, methods, imports, domain clusters
     ▼
Step 2 — Layer 1 Extraction     (Pure Python, no AI, ~2 min)
     │    Extracts: files, configs, DB schemas, log patterns
     ▼
Step 3 — BA Agent 1             (Claude AI, ~10 min)
     │    Finds: domains, entities, business rules
     ▼
Step 4 — BA Agent 2             (Claude AI, ~15 min)
     │    Produces: 10 Business Architecture documents
     ▼
Steps 5-9 — DA + TA + AA        (Claude AI, ~40 min, parallel tracks)
     │    DA: schemas, ERDs, data flows, PII inventory
     │    TA: tech stack, security, NFRs, tech debt
     │    AA: 310 components, 55 APIs, dependency graphs
     ▼
Step 10 — Foundation Synthesis  (Claude AI, ~20 min)
          Merges all 4 layers → Enterprise Knowledge Graph
          + 20 Forward Engineering documents
```

---

## Pipeline Steps Detail

| Step | Name | AI? | Time | Output |
|---|---|---|---|---|
| 1 | Graphify Extract | No | ~5 min | `graphify-out/` |
| 2 | Layer 1 Extraction | No | ~2 min | `layer1_output.json` |
| 3 | BA Agent 1 — StructuralScout | Yes | ~10 min | `layer2_output.json` |
| 4 | BA Agent 2 — DeepAnalyst | Yes | ~15 min | `ba_documents/` (10 files) |
| 5 | DA Agent 1 — DataExtractor | Yes | ~15 min | `da-outputs/` (13 files) |
| 6 | DA Agent 2 — DataReviewer | Yes | ~20 min | `da-outputs/` (14 files) |
| 7 | TA Agent 1 — StackScout | Yes | ~10 min | `ta-outputs/ta_agent1/` |
| 8 | TA Agent 2 — DeepAnalyst | Yes | ~20 min | `ta-outputs/` (14 files) |
| 9 | AA Pipeline | No | ~5 min | `aa-outputs/` (32 files) |
| 10 | Foundation Synthesis | Yes | ~20 min | `foundation/` + `forward-engineering/` |

**Steps 1-2 are free (no AI).** Steps 3-10 use Claude Code (requires Anthropic account).

---

## Supported Languages

| Language | Extensions | Notes |
|---|---|---|
| .NET / C# | `.cs`, `.csproj` | Full support — DDD, EF Core, minimal APIs |
| Java | `.java`, `pom.xml` | Full support — Spring, Maven |
| Python | `.py` | Full support — Django, FastAPI, Flask |
| JavaScript / TypeScript | `.js`, `.ts`, `.jsx`, `.tsx` | Full support — React, Node.js |

---

## Prompts

All 8 Claude prompts are in `prompts/`. The pipeline uses them automatically. If you want to run any agent manually (paste into Claude), use them in this order:

| File | Agent | What it does |
|---|---|---|
| `01_BA_Agent1_StructuralScout.md` | BA Agent 1 | Structural scan — finds domains and entities |
| `02_BA_Agent2_DeepAnalyst.md` | BA Agent 2 | Deep analysis — produces 10 BA documents |
| `03_DA_Agent1_DataExtractor.md` | DA Agent 1 | Extracts schemas, ERDs, data flows |
| `04_DA_Agent2_DataReviewer.md` | DA Agent 2 | Reviews and validates DA output |
| `05_TA_Agent1_StackScout.md` | TA Agent 1 | Scans technology stack |
| `06_TA_Agent2_DeepAnalyst.md` | TA Agent 2 | Security, NFRs, tech debt analysis |
| `07_AA_Pipeline_Note.md` | AA Pipeline | Automated Python — no manual run needed |
| `08_Foundation_Synthesis.md` | Foundation | Merges all layers → Knowledge Graph |

**Rule:** Always run Agent 1 before Agent 2 in each layer.

---

## Troubleshooting

**`claude: command not found`**
```bash
npm install -g @anthropic/claude-code
claude login
```

**`graphify: command not found`**
```bash
pip install graphify-ai
```

**`No module named 'yaml'` or similar**
```bash
pip install -r requirements.txt
```

**Agent times out on large repos**
The pipeline handles timeouts gracefully — partial output is saved. Re-run the failed step using the prompt from `prompts/` pasted directly into a Claude session.

**Windows path errors**
Use forward slashes: `python run.py --source "C:/path/to/project"`

**`git clone` fails for private repos**
```bash
python run.py --source "https://github.com/org/private-repo" --token YOUR_GITHUB_TOKEN
```

---

## Project Structure

```
graphify-pipeline/
├── run.py                          ← Single command entry point
├── README.md                       ← This file
├── requirements.txt
│
├── prompts/                        ← 8 Claude agent prompts (01-08)
│
├── pipeline/                       ← Pipeline engine
│   ├── run_pipeline.py             ← Layer 1 orchestrator
│   ├── foundation_runner.py        ← Foundation synthesis
│   ├── layer1/                     ← Extraction (Python, no AI)
│   ├── layer2/                     ← BA Agent 1 runner
│   ├── layer3/                     ← BA Agent 2 runner
│   ├── data-architecture/          ← DA Agent 1+2 runners
│   ├── technology-architecture/    ← TA Agent 1+2 runners
│   └── application-architecture/  ← AA Pipeline (Python, no AI)
│
└── sample-output/                  ← Complete eShopOnWeb example
    ├── graphify-out/               ← graph.html, GRAPH_REPORT.md
    ├── foundation/                 ← 5 foundation files
    ├── forward-engineering/        ← 20 FE documents
    └── source-code/eShopOnWeb/     ← .NET source (488 files)
```

---

## Accuracy (eShopOnWeb reference run)

| Layer | Accuracy | Basis |
|---|---|---|
| Graphify + Layer 1 | ~97% | Deterministic AST parsing |
| Business Architecture | ~88% | 37 rules with source line evidence |
| Data Architecture | ~90% | DA Agent 2 field-type corrections |
| Technology Architecture | ~87% | Stack facts + security analysis |
| Application Architecture | ~95% | 32/32 quality checks pass |
| Foundation Knowledge Graph | ~92% | 95% HIGH confidence nodes |
| **Overall** | **~88-92%** | |
