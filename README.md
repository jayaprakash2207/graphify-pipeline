# Graphify Pipeline — Enterprise Knowledge Graph Generator

Reverse-engineer any codebase into a structured Enterprise Knowledge Graph using AST extraction and 8 Claude AI agents across 4 architecture layers.

---

## What This Pipeline Does

The pipeline takes any codebase — a GitHub URL, a local folder, or a zip file — and produces a complete, evidence-based enterprise architecture package without any manual documentation effort.

It works in two stages:

1. **Graphify (AST extraction)** — Parses the codebase using Tree-sitter to build a structural graph of every file, class, function, and cross-file relationship. No AI cost. Pure deterministic analysis.

2. **8 Claude AI agents across 4 architecture layers** — Each agent reads the extracted code and produces specific architecture documents:

| Layer | Agents | What They Produce |
|-------|--------|-------------------|
| Business Architecture | Agent 1 + Agent 2 | Capability maps, process flows, business rules, stakeholder matrix |
| Data Architecture | Agent 1 + Agent 2 | Schema catalogue, ERD, data dictionary, PII inventory, data flow map |
| Technology Architecture | Agent 1 + Agent 2 | Technology stack, security assessment, NFR analysis, tech debt register |
| Application Architecture | Agent 1 + Agent 2 | Dependency graph, API contracts, violation register, call flows |

All four layers feed into a **Foundation synthesis** step that unifies everything into one Enterprise Knowledge Graph.

---

## What You Get (Output)

After a full pipeline run, your output folder looks like this:

```
your-output/
├── graphify-out/                      <- Structural graph (god nodes, communities)
│   ├── graph.html                     <- Interactive visual — open in any browser
│   ├── graph.json                     <- Raw graph data (274+ nodes, edges)
│   └── GRAPH_REPORT.md                <- Human-readable architecture summary
│
├── ba_documents/                      <- 10 Business Architecture documents
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
├── da-outputs/                        <- 14 Data Architecture documents
│   ├── schema_catalogue.md
│   ├── erd.md
│   ├── data_dictionary.md
│   ├── pii_inventory.md
│   └── ... (10 more files)
│
├── ta-outputs/                        <- 9 Technology Architecture documents
│   ├── technology_stack_assessment.md
│   ├── security_architecture_assessment.md
│   ├── nfr_registry.md
│   └── ... (6 more files)
│
├── aa-outputs/                        <- 32 Application Architecture documents
│   ├── dependency_graph.md
│   ├── api_contracts.md
│   ├── violation_register.md
│   └── ... (29 more files)
│
├── foundation/                        <- Enterprise Knowledge Graph (synthesized)
│   ├── ENTERPRISE_KNOWLEDGE_GRAPH.json
│   ├── CANONICAL_ENTERPRISE_MODEL.md
│   ├── ARCHITECTURE_INVENTORY.md
│   ├── TRACEABILITY_MATRIX.md
│   └── FORWARD_ENGINEERING_INPUT_MAP.md
│
└── forward-engineering/               <- FINAL OUTPUT — 20 Forward Engineering docs
    ├── 01_BRD.md                      <- Business Requirements (37 rules)
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
    ├── 13_SECURITY_ARCHITECTURE.md    <- 6 critical blockers identified
    ├── 14_NFR_SPECIFICATION.md
    ├── 15_FORWARD_ENGINEERING_SPECIFICATION.md
    ├── 16_GENERATION_MANIFEST.json    <- 106 nodes, Wave 1-5 order
    ├── 17_FORWARD_ENGINEERING_READINESS_REPORT.md
    ├── 18_DEPLOYMENT_ARCHITECTURE.md  <- Docker + Azure CI/CD YAML
    ├── 19_FRONTEND_ARCHITECTURE.md
    └── 20_UI_UX_SPECIFICATION.md
```

The `forward-engineering/` folder is the final deliverable. It contains 20 production-ready documents covering every layer of the application — from business rules to deployment architecture — ready for code generation, migration planning, or modernization.

---

## Sample Output

The `sample-output/` folder in this repo contains a fully generated example from **eShopOnWeb** — the official Microsoft .NET reference e-commerce application.

| What to open | How to view it |
|---|---|
| `sample-output/graphify-out/graph.html` | Open in any browser — interactive node graph |
| `sample-output/graphify-out/GRAPH_REPORT.md` | Structural clusters, god nodes, domain boundaries |
| `sample-output/foundation/ENTERPRISE_KNOWLEDGE_GRAPH.json` | 173 nodes, 95% HIGH confidence |
| `sample-output/foundation/CANONICAL_ENTERPRISE_MODEL.md` | Human-readable architecture |
| `sample-output/forward-engineering/01_BRD.md` | Business Requirements — 37 rules |
| `sample-output/forward-engineering/13_SECURITY_ARCHITECTURE.md` | 6 critical production blockers |
| `sample-output/forward-engineering/16_GENERATION_MANIFEST.json` | 106 nodes mapped to code-gen targets |
| `sample-output/forward-engineering/18_DEPLOYMENT_ARCHITECTURE.md` | Full Docker + Azure CI/CD YAML |
| `sample-output/source-code/eShopOnWeb/` | Full .NET source (488 files) — the input |

The eShopOnWeb sample produced: 173 graph nodes (95% HIGH confidence), 5 foundation documents, and 20 forward engineering documents (676KB total) — complete end to end.

---

## Prerequisites

Install these before running the pipeline:

**1. Python 3.11 or higher**

Download from [python.org](https://www.python.org/downloads/). Verify with:
```bash
python --version
```

**2. Claude Code CLI**

```bash
npm install -g @anthropic/claude-code
claude login
```

You will need an Anthropic account. Claude Code is the AI engine that runs all 8 agents.

**3. Graphify**

```bash
pip install graphify-ai
```

Graphify handles the AST parsing and structural graph generation.

**4. Pipeline dependencies**

```bash
pip install -r requirements.txt
```

---

## Quick Start

```bash
# Clone this repo
git clone <repo-url>
cd graphify-pipeline

# Install dependencies
pip install -r requirements.txt
pip install graphify-ai

# Run on a public GitHub repository
python run.py --source "https://github.com/dotnet-architecture/eShopOnWeb"

# Run on a local folder
python run.py --source "C:/path/to/your/project" --output ./my-results

# Run with a private repo (provide a Git token)
python run.py --source "https://github.com/your-org/private-repo" --token YOUR_GIT_TOKEN

# Run Layer 1 only (extraction, no agents)
python run.py --source "C:/path/to/project" --output ./my-results
# Then run agents manually with the prompts in prompts/ (see Prompts section below)
```

After the run completes, open `your-output/graphify-out/graph.html` in a browser to see the structural graph, then browse `your-output/foundation/` for the knowledge graph documents.

---

## Pipeline Steps

The pipeline runs 10 steps in sequence. Each step must complete before the next one starts — agents never run in parallel, which keeps Claude token usage predictable.

| Step | Name | What It Does | Output |
|------|------|-------------|--------|
| 0 | Input Resolution | Clones a GitHub URL, unzips an archive, or points to a local folder | Local copy of codebase |
| 1 | Language Detection | Counts file extensions to identify the primary language (.NET, Java, Python, JS/TS) | Language label |
| 2 | File Filtering | Walks the directory tree; keeps source files, skips `node_modules`, `bin`, `obj`, `.git`, test fixtures | Clean file list |
| 3 | Source Code Extraction | Language-specific AST/regex parser extracts every class, method, interface, and enum | `source_code.json` |
| 4 | Database Extraction | Scans `.sql` files, EF Core migration files, and stored procedure definitions | `database.json` |
| 5 | Config Extraction | Reads `appsettings.json`, `.yml`, and `.xml` config files; tags business params (thresholds, limits, rates) | `config.json` |
| 6 | Log Extraction | Mines `.log` and `.txt` files for timestamped business events and process sequences | `logs.json` |
| 7 | Graphify | Runs `graphify update .` to build the AST-based structural graph with god nodes and community structure | `graphify-out/` |
| 8 | AI Agents (BA, DA, TA, AA) | Runs all 8 Claude agents sequentially across the 4 architecture layers | `ba_documents/`, `da-outputs/`, `ta-outputs/`, `aa-outputs/` |
| 9 | Foundation Synthesis | Merges all 4 layers into one unified Enterprise Knowledge Graph | `foundation/` |

Steps 0–7 are deterministic (no AI, no API cost). Steps 8–9 use Claude.

---

## Prompts

The `prompts/` folder contains the 8 Claude prompts — one per agent. These are the same prompts the pipeline uses automatically when you run `python run.py --full-run`.

If you prefer to run agents manually (paste into Claude directly), use them in this order:

```
01_BA_Agent1_StructuralScout.md     Business layer — structural scan
02_BA_Agent2_DeepAnalyst.md         Business layer — deep analysis and document generation
03_DA_Agent1_DataExtractor.md       Data layer — schema and entity extraction
04_DA_Agent2_DataReviewer.md        Data layer — validation and review
05_TA_Agent1_StackScout.md          Technology layer — stack inventory scan
06_TA_Agent2_DeepAnalyst.md         Technology layer — pattern and risk analysis
07_AA_Agent1_AppExtractor.md        Application layer — service and dependency extraction
08_AA_Agent2_QualityReview.md       Application layer — quality review and validation
```

**Important:** Each layer has two agents. Always run Agent 1 before Agent 2 — Agent 2 needs Agent 1's output as its input. Run each agent in a fresh Claude conversation.

---

## Supported Languages

The pipeline handles projects written in any of these languages:

| Language | File Types | Parser |
|----------|-----------|--------|
| .NET / C# | `.cs`, `.vb` | Regex-based AST walker |
| Java | `.java` | Regex-based method/class extractor |
| Python | `.py` | Python `ast` module (native) |
| JavaScript / TypeScript | `.js`, `.ts`, `.jsx`, `.tsx` | Regex function/class detector |

Mixed-language projects are supported — the pipeline detects the primary language and runs the appropriate extractor.

---

## Accuracy

Based on the eShopOnWeb reference run:

| Layer | Accuracy | Notes |
|-------|----------|-------|
| Extraction (Step 3–6) | ~80% | Strong on code and config; weak when no log files exist in repo |
| Business Architecture documents | ~78% average | Rules and entities are high confidence; roadmap is inferred |
| Data Architecture documents | ~85% | Schema and relationships extracted directly from code |
| Technology Architecture documents | ~87% | Stack inventory is fact-based; risk analysis is interpreted |
| Application Architecture documents | ~90% | Dependency graphs and API contracts are code-traced |
| Foundation Knowledge Graph | ~97% | Synthesis of all four layers |

Documents marked as "inferred" (motivation model, operating model, roadmap) require business stakeholder review before use.

---

## Troubleshooting

**`claude: command not found`**
Run `npm install -g @anthropic/claude-code` then `claude login`. Make sure Node.js is installed first.

**`graphify: command not found`**
Run `pip install graphify-ai`. If `pip` is not found, use `python -m pip install graphify-ai`.

**Timeout errors during agent steps**
Agents run sequentially by default. Large repositories (500+ files) take longer. This is expected — let the run complete. Do not interrupt mid-agent.

**`git clone` fails for a private repository**
Pass `--token YOUR_GIT_TOKEN` to `run.py`. Generate a Personal Access Token in your GitHub/GitLab settings with `repo` read scope.

**`No module named 'yaml'`**
Run `pip install -r requirements.txt` from the `graphify-pipeline/` directory.

**Agent output is incomplete (partial documents)**
Re-run only the failed agent using the corresponding prompt from `prompts/`. Agent 2 can be re-run without re-running Agent 1 if Agent 1's output is already saved.

**Windows path errors**
Use forward slashes or raw strings in `--source` paths: `C:/path/to/project` or `"C:\path\to\project"`.

---

## Project Structure

```
graphify-pipeline/
├── run.py                  <- Entry point: --source, --output, --token, --full-run
├── requirements.txt        <- Python dependencies
├── README.md               <- This file
│
├── prompts/                <- 8 Claude agent prompts (run in order 01–08)
│
├── layer1/                 <- Extraction layer (deterministic, no AI)
│   ├── pipeline.py         <- 8-step orchestrator
│   ├── input_resolver.py   <- Handles GitHub URL / zip / local path
│   ├── language_detector.py
│   ├── file_filter.py
│   ├── cleaner.py
│   ├── output_saver.py
│   ├── database_extractor.py
│   ├── config_extractor.py
│   ├── log_extractor.py
│   └── extractors/
│       ├── dotnet_extractor.py
│       ├── java_extractor.py
│       ├── python_extractor.py
│       └── javascript_extractor.py
│
├── layer2/                 <- BA processing layer (Claude agent)
├── layer3/                 <- BA document generation layer (Claude agent)
├── data-architecture/      <- DA agents (2 agents)
├── technology-architecture/<- TA agents (2 agents)
├── application-architecture/<- AA agents (2 agents)
├── foundation_runner.py    <- Final synthesis: Enterprise Knowledge Graph
│
└── sample-output/          <- Complete example output from eShopOnWeb (.NET)
    ├── graphify-out/
    ├── ba_documents/
    ├── da-outputs/
    ├── ta-outputs/
    ├── aa-outputs/
    └── foundation/
```
