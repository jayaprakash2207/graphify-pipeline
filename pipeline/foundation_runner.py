"""
Foundation Runner
-----------------
Synthesizes all 4 layer outputs (BA, DA, TA, AA) into the
Enterprise Knowledge Graph and 4 read-only foundation views.

Reads:
  <input>/ba_documents/          - BA layer output (Agent 2 docs)
  <input>/da-outputs/            - DA layer output (Agent 1 schema etc.)
  <input>/ta-outputs/            - TA layer output (stack, security, NFRs)
  <input>/aa-outputs/            - AA layer output (services, APIs, deps)

Writes:
  <input>/foundation/ENTERPRISE_KNOWLEDGE_GRAPH.json
  <input>/foundation/CANONICAL_ENTERPRISE_MODEL.md
  <input>/foundation/ARCHITECTURE_INVENTORY.md
  <input>/foundation/TRACEABILITY_MATRIX.md
  <input>/foundation/FORWARD_ENGINEERING_INPUT_MAP.md

Usage:
    python foundation_runner.py --input output/eShopOnWeb
    python foundation_runner.py --input output/eShopOnWeb --run
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

FOUNDATION_PROMPT = Path(__file__).parent.parent.parent.parent / "prompts-ready-to-use" / "00_README.md"

# Output files the Foundation layer must produce
REQUIRED_OUTPUTS = [
    "ENTERPRISE_KNOWLEDGE_GRAPH.json",
    "CANONICAL_ENTERPRISE_MODEL.md",
    "ARCHITECTURE_INVENTORY.md",
    "TRACEABILITY_MATRIX.md",
    "FORWARD_ENGINEERING_INPUT_MAP.md",
]

FOUNDATION_SYNTHESIS_PROMPT = """
# Foundation Synthesis Agent

You are the Foundation / Synthesis agent. Your job is to reconcile all four
architecture layers (Business, Data, Application, Technology) into a single
Enterprise Knowledge Graph and four read-only views.

## Rules

1. NEVER invent facts. Every node must trace to evidence in the layer outputs provided.
2. Where the same concept appears in multiple layers (e.g. "Order" in BA, DA, and AA),
   merge into ONE canonical node — do not duplicate.
3. Assign confidence: HIGH (direct evidence), MEDIUM (inferred), LOW (assumed), ASSUMED (no evidence).
4. Every node must carry: id, type, owner_layer, confidence, evidence (file or layer source).
5. Record every cross-layer conflict in normalization_log with a DISC-### id.
6. Record every unresolved question in open_questions with an OQ-### id.
7. Assumptions that cannot be verified go in assumptions with an ASMP-### id.

## Node ID scheme

- BIZ-CAP-### Business capabilities
- BIZ-PROC-### Business processes
- BIZ-ACT-### Business actors
- BIZ-RULE-### Business rules
- DATA-ENT-### Domain entities
- DATA-AGG-### Aggregates
- DATA-REPO-### Repositories
- APP-SVC-### Application services
- APP-API-### APIs
- APP-IF-### Interfaces
- APP-DEP-### Dependencies
- TECH-CUR-### Current stack technologies
- TECH-INF-### Infrastructure components
- TECH-SEC-### Security components

## Output format

Produce exactly 5 files using these markers:

===FOUNDATION_START:ENTERPRISE_KNOWLEDGE_GRAPH.json===
{ ... }
===FOUNDATION_END===

===FOUNDATION_START:CANONICAL_ENTERPRISE_MODEL.md===
...
===FOUNDATION_END===

===FOUNDATION_START:ARCHITECTURE_INVENTORY.md===
...
===FOUNDATION_END===

===FOUNDATION_START:TRACEABILITY_MATRIX.md===
...
===FOUNDATION_END===

===FOUNDATION_START:FORWARD_ENGINEERING_INPUT_MAP.md===
...
===FOUNDATION_END===

The ENTERPRISE_KNOWLEDGE_GRAPH.json must have exactly these 9 top-level sections:
  metadata, business, data, application, technology,
  cross_links, assumptions, normalization_log, open_questions

The TRACEABILITY_MATRIX.md must show:
  Capability -> Process -> Entity -> Service -> API (end-to-end traceability)

The FORWARD_ENGINEERING_INPUT_MAP.md must map every graph node to the
forward-engineering document that consumes it (doc 01..20).
"""


def _claude_cmd() -> list:
    if sys.platform == "win32":
        return ["cmd", "/c", "claude", "-p", "--output-format", "text", "--no-session-persistence"]
    found = shutil.which("claude")
    if not found:
        raise RuntimeError("claude CLI not found on PATH")
    return [found, "-p", "--output-format", "text", "--no-session-persistence"]


def _read_layer_outputs(input_dir: str) -> dict:
    """Read all available layer outputs into a single context dict."""
    base = Path(input_dir)
    context = {}

    # BA outputs
    ba_dir = base / "ba_documents"
    if ba_dir.exists():
        ba_files = list(ba_dir.glob("*.md")) + list(ba_dir.glob("*.json"))
        context["ba_documents"] = {
            f.name: f.read_text(encoding="utf-8", errors="replace")[:3000]
            for f in ba_files[:10]
        }
        print(f"  BA docs found    : {len(ba_files)}")
    else:
        print("  BA docs          : NOT FOUND — run BA agents first")

    # DA outputs
    da_dir = base / "da-outputs"
    if da_dir.exists():
        da_files = list(da_dir.glob("*.md")) + list(da_dir.glob("*.json"))
        context["da_outputs"] = {
            f.name: f.read_text(encoding="utf-8", errors="replace")[:3000]
            for f in da_files[:10]
        }
        print(f"  DA outputs found : {len(da_files)}")
    else:
        print("  DA outputs       : NOT FOUND — run DA agents first")

    # TA outputs
    ta_dir = base / "ta-outputs"
    if ta_dir.exists():
        ta_files = list(ta_dir.glob("*.md")) + list(ta_dir.glob("*.json"))
        context["ta_outputs"] = {
            f.name: f.read_text(encoding="utf-8", errors="replace")[:3000]
            for f in ta_files[:10]
        }
        print(f"  TA outputs found : {len(ta_files)}")
    else:
        print("  TA outputs       : NOT FOUND — run TA agents first")

    # AA outputs
    aa_dir = base / "aa-outputs" / "final"
    if aa_dir.exists():
        aa_files = list(aa_dir.glob("*.md")) + list(aa_dir.glob("*.json"))
        context["aa_outputs"] = {
            f.name: f.read_text(encoding="utf-8", errors="replace")[:3000]
            for f in aa_files[:10]
        }
        print(f"  AA outputs found : {len(aa_files)}")
    else:
        print("  AA outputs       : NOT FOUND — run AA agents first")

    return context


def _build_prompt(context: dict) -> str:
    data_section = json.dumps(context, indent=2, ensure_ascii=False)
    return (
        f"{FOUNDATION_SYNTHESIS_PROMPT}\n\n"
        f"## Layer outputs to synthesize\n\n"
        f"```json\n{data_section[:60000]}\n```\n"
    )


def _save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "foundation_task.md"
    task_path.write_text(prompt, encoding="utf-8")
    return str(task_path)


def _parse_and_save_outputs(raw: str, foundation_dir: Path) -> list:
    """Parse FOUNDATION_START/END markers and write each file."""
    saved = []
    import re
    pattern = re.compile(
        r"===FOUNDATION_START:(.+?)===\n(.*?)===FOUNDATION_END===",
        re.DOTALL
    )
    for match in pattern.finditer(raw):
        filename = match.group(1).strip()
        content  = match.group(2).strip()
        out_path = foundation_dir / filename
        out_path.write_text(content, encoding="utf-8")
        saved.append(filename)
        print(f"  Written: {filename}")
    return saved


def run_foundation(input_dir: str, dry_run: bool = False) -> bool:
    """Build the Foundation knowledge graph from all layer outputs."""
    base           = Path(input_dir)
    foundation_dir = base / "foundation"
    foundation_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("FOUNDATION RUNNER — reading layer outputs")
    print("=" * 60)

    context   = _read_layer_outputs(input_dir)
    prompt    = _build_prompt(context)
    task_file = _save_task_file(prompt, input_dir)

    print(f"\n  Task file: {task_file}")
    print(f"  Prompt size: {len(prompt) / 1024:.1f} KB")

    if not dry_run:
        print("\n  Calling Claude for Foundation synthesis...")
        try:
            proc = subprocess.run(
                _claude_cmd(),
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=1800,
            )
        except subprocess.TimeoutExpired as exc:
            partial = exc.stdout or ""
            partial_path = foundation_dir / "foundation_raw_partial.txt"
            partial_path.write_text(partial, encoding="utf-8")
            print(f"\n  WARNING — Claude timed out after 1800 s. Partial output saved to: {partial_path}")
            return False
        except Exception as exc:
            print(f"\n  ERROR calling Claude: {exc}")
            return False

        raw_path = foundation_dir / "foundation_raw_output.txt"
        raw_path.write_text(proc.stdout or "", encoding="utf-8")

        if proc.returncode != 0:
            print(f"\n  Claude returned exit code {proc.returncode}")
            print(f"  stderr: {proc.stderr[:500]}")
            return False

        saved = _parse_and_save_outputs(proc.stdout or "", foundation_dir)

        missing = [f for f in REQUIRED_OUTPUTS if f not in saved]
        if missing:
            print(f"\n  WARNING — missing outputs: {missing}")
            print(f"  Raw output saved to: {raw_path}")
            return False

        print("\n" + "=" * 60)
        print("FOUNDATION COMPLETE")
        print("=" * 60)
        print(f"  Output dir: {foundation_dir}")
        for f in REQUIRED_OUTPUTS:
            print(f"  {f}  OK")
        print("=" * 60)
        return True

    else:
        print("\n  [dry-run] Task file written. Re-run with --run to call Claude.")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Foundation Runner — synthesize all layer outputs into the Enterprise Knowledge Graph"
    )
    parser.add_argument(
        "--input", required=True,
        help="Output directory from run_pipeline.py (contains ba_documents/, da-outputs/, ta-outputs/, aa-outputs/)"
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Actually call Claude. Without this flag, only writes the task file (dry run)."
    )
    args = parser.parse_args()

    success = run_foundation(args.input, dry_run=not args.run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
