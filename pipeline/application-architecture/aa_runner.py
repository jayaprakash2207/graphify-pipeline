"""
AA Runner
---------
Wraps the Application Architecture extraction pipeline.
Calls run_architecture_extraction.py with the extracted source repo root
and writes all outputs to {input}/aa-outputs/.

Two phases:
  1. Python analyzer (deterministic, "parse first") — runs the pipeline stages
     inventory → source-chunks → parsed → semantic → evidence → final →
     enterprise-forward → application-blueprint → review.
  2. Claude stage chain (LLM, "reason second") — runs architecture-prompts/
     stages 04→07 sequentially over the Python evidence packs, via the claude
     CLI, writing results under aa-outputs/llm-stages/. Skipped with --skip-llm.

Usage:
    # Python analyzer + claude stage chain
    python application-architecture/aa_runner.py \
        --repo-root /path/to/source --input output/eShopOnWeb --run

    # Python analyzer only (no tokens)
    python application-architecture/aa_runner.py \
        --repo-root /path/to/source --input output/eShopOnWeb --run --skip-llm

    # Claude stage chain only (reuses existing evidence packs)
    python application-architecture/aa_runner.py \
        --input output/eShopOnWeb --llm-only
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in headers/paths don't crash cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AA_TOOLS_DIR = Path(__file__).parent / "tools" / "application_architecture_analyzer"
ORCHESTRATOR  = AA_TOOLS_DIR / "run_architecture_extraction.py"

FINAL_OUTPUTS = [
    "final/application-architecture-summary.md",
    "final/system-inventory.json",
    "final/component-registry.json",
    "final/dependency-graph.json",
    "final/architecture-pattern-report.md",
    "final/architecture-violation-register.json",
    "final/application-risk-register.json",
    "final/enterprise-application-architecture-blueprint.md",
    "final/enterprise-application-architecture-blueprint.json",
    "final/quality-review.md",
    "final/executive-summary-for-review.md",
]


# ── Claude staged reasoning chain (stages 04→07 over the Python evidence) ───────
#
# The Python analyzer performs the deterministic "parse first" stages
# (inventory → parsed facts → evidence packs). The claude CLI then runs the
# "reason second" stages from architecture-prompts/, ONE STAGE AT A TIME
# (fully sequential — no concurrent claude calls), each consuming the previous
# stage's output:
#
#   04-final-architecture          ← evidence-packs/   (from the Python pipeline)
#   05-enterprise-forward-eng       ← llm-stages/final/
#   06-quality-review               ← llm-stages/final/
#   07-workflow-audit               ← AGENTS.md + prompts + llm-stages/
#
# 00-global-rules.md is prepended to every stage. Stage 04 additionally receives
# AGENTS.md (golden rules / stage order) and the master extraction prompt
# (detailed output JSON shapes). Claude output is written under
# aa-outputs/llm-stages/ so the deterministic Python outputs are never clobbered.

AA_DIR        = Path(__file__).parent
PROMPTS_DIR   = AA_DIR / "architecture-prompts"
GLOBAL_RULES  = PROMPTS_DIR / "00-global-rules.md"
AGENTS_FILE   = AA_DIR / "AGENTS.md"
MASTER_PROMPT = AA_DIR / "application_architecture_extraction_agent_prompt.md"

LLM_STAGES = [
    {"id": "04-final-architecture",            "prompt": "04-final-architecture-agent.md",             "reads": "evidence"},
    {"id": "05-enterprise-forward-engineering", "prompt": "05-enterprise-forward-engineering-agent.md", "reads": "final"},
    {"id": "06-quality-review",                "prompt": "06-quality-review-agent.md",                 "reads": "final"},
    {"id": "07-workflow-audit",                "prompt": "07-workflow-audit-agent.md",                 "reads": "workflow"},
]

_AA_FILE_RE = re.compile(r"===AA_FILE_START:(.+?)===(.*?)===AA_FILE_END===", re.DOTALL)


def _claude_cmd() -> list:
    """Return base claude CLI command. Uses cmd /c on Windows to execute .cmd scripts."""
    if sys.platform == "win32":
        return ["cmd", "/c", "claude", "-p", "--output-format", "text", "--no-session-persistence"]
    found = shutil.which("claude")
    if not found:
        raise FileNotFoundError("claude CLI not found. Install from https://claude.ai/code")
    return [found, "-p", "--output-format", "text", "--no-session-persistence"]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _collect_context(dirs: list, cap_per_file: int = 3500, max_files: int = 40) -> str:
    """Read .json/.md/.mmd files from the given dirs into a labelled, size-capped block."""
    sections = []
    count = 0
    for d in dirs:
        d = Path(d)
        if not d.exists():
            continue
        for path in sorted(d.rglob("*")):
            if count >= max_files:
                break
            if not path.is_file() or path.suffix.lower() not in (".json", ".md", ".mmd"):
                continue
            text = _read_text(path)
            if not text:
                continue
            truncated = len(text) > cap_per_file
            body = text[:cap_per_file] + ("\n... [truncated]" if truncated else "")
            try:
                rel = path.relative_to(d.parent).as_posix()
            except ValueError:
                rel = path.name
            sections.append(f"### {rel}\n```\n{body}\n```")
            count += 1
    return "\n\n".join(sections) if sections else "[no input files found]"


def _save_marked_files(agent_output: str, base_dir: Path) -> list:
    """Parse ===AA_FILE_START:<path>===...===AA_FILE_END=== markers and save under base_dir."""
    saved = []
    for match in _AA_FILE_RE.finditer(agent_output):
        rel = match.group(1).strip().replace("\\", "/").lstrip("/")
        if rel.startswith("architecture-output/"):
            rel = rel[len("architecture-output/"):]
        parts = [p for p in Path(rel).parts if p not in ("..", "")]
        if not parts:
            continue
        rel_path = Path(*parts)
        file_path = base_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(match.group(2).strip(), encoding="utf-8")
        size_kb = file_path.stat().st_size / 1024
        print(f"      {rel_path.as_posix():<50} {size_kb:>6.1f} KB")
        saved.append(rel_path.as_posix())
    return saved


def _build_stage_prompt(stage: dict, context_text: str) -> str:
    """Assemble the full prompt for one staged claude call."""
    preamble = (
        f"I'm working through an application architecture analysis in stages, and this is\n"
        f"stage \"{stage['id']}\". Earlier stages (inventory, parser, evidence packs) were\n"
        f"already produced deterministically by a Python analyzer and are provided below\n"
        f"as INPUT CONTEXT.\n\n"
        f"Please don't write to disk or rescan the repo — instead, write out each output\n"
        f"file listed in this stage's \"Output\" section, wrapping each one in these markers\n"
        f"so I can save them to disk programmatically:\n\n"
        f"===AA_FILE_START:<relative/path/filename.ext>===\n"
        f"<full file content>\n"
        f"===AA_FILE_END===\n\n"
        f"Please use the exact relative paths from the stage's Output section "
        f"(e.g. final/system-inventory.json), and emit valid JSON for .json files.\n"
    )

    governance = ""
    if stage["id"].startswith("04"):
        governance = (
            "\n--- AGENTS.md (orchestrator golden rules & stage order) ---\n"
            f"{_read_text(AGENTS_FILE)}\n"
            "\n--- MASTER EXTRACTION PROMPT (detailed output JSON shapes) ---\n"
            f"{_read_text(MASTER_PROMPT)}\n"
        )

    reminder = (
        "\n\n---\n\n## Reminder on output format\n"
        "Please output all files from this stage's Output section, each wrapped in\n"
        "===AA_FILE_START:<path>=== / ===AA_FILE_END=== markers. I'll be parsing your\n"
        "response for these exact markers, so please give full file contents rather\n"
        "than descriptions.\n"
    )

    return (
        f"{preamble}\n"
        f"--- 00 GLOBAL RULES (apply to this stage) ---\n{_read_text(GLOBAL_RULES)}\n"
        f"{governance}\n"
        f"--- STAGE PROMPT: {stage['prompt']} ---\n{_read_text(PROMPTS_DIR / stage['prompt'])}\n\n"
        f"--- INPUT CONTEXT ---\n{context_text}\n"
        f"{reminder}"
    )


def _resolve_read_dirs(stage_reads: str, aa_root: Path, llm_root: Path) -> list:
    """Return the input directories a stage should read, with sensible fallbacks."""
    if stage_reads == "evidence":
        return [aa_root / "evidence-packs"]
    if stage_reads == "final":
        llm_final = llm_root / "final"
        if llm_final.exists() and any(llm_final.iterdir()):
            return [llm_final]
        return [aa_root / "final"]                       # fall back to Python's final/
    if stage_reads == "workflow":
        return [PROMPTS_DIR, llm_root / "final", aa_root / "final"]
    return []


def _run_llm_stage(stage: dict, context_text: str, llm_root: Path, input_dir: str) -> dict:
    """Build the stage prompt, call claude, and save marker-delimited output files."""
    prompt    = _build_stage_prompt(stage, context_text)
    task_file = Path(input_dir) / f"aa_stage_{stage['id']}_task.md"
    task_file.write_text(prompt, encoding="utf-8")   # always written for manual inspection/run

    print(f"\n  [stage {stage['id']}] calling claude... "
          f"(task: {task_file.name}, {len(prompt) / 1024:.1f} KB)")

    try:
        result = subprocess.run(
            _claude_cmd(), input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600, check=False,
        )
    except FileNotFoundError:
        print("  [info] claude CLI not found in PATH — task file written for manual run")
        return {"id": stage["id"], "saved": [], "ok": False}
    except subprocess.TimeoutExpired:
        print(f"  [warn] stage {stage['id']} timed out after 600s")
        return {"id": stage["id"], "saved": [], "ok": False}

    raw = result.stdout.strip()
    (Path(input_dir) / f"aa_stage_{stage['id']}_raw.txt").write_text(raw, encoding="utf-8")

    if result.returncode != 0:
        print(f"  [warn] stage {stage['id']} — claude returned code {result.returncode}")
        if result.stderr.strip():
            print(f"  stderr: {result.stderr.strip()[:300]}")
        return {"id": stage["id"], "saved": [], "ok": False}

    print("  saving stage outputs...")
    saved = _save_marked_files(raw, llm_root)
    if not saved:
        print(f"  [warn] stage {stage['id']} produced no marker files (raw saved)")
        return {"id": stage["id"], "saved": [], "ok": False}
    return {"id": stage["id"], "saved": saved, "ok": True}


def run_aa_claude_chain(input_dir: str) -> bool:
    """Run the sequential claude reasoning chain (stages 04→07) over the evidence packs."""
    aa_root  = Path(input_dir) / "aa-outputs"
    llm_root = aa_root / "llm-stages"
    evidence = aa_root / "evidence-packs"

    print("\n" + "=" * 60)
    print("AA CLAUDE CHAIN — STAGES 04→07 (sequential, evidence-driven)")
    print("=" * 60)

    if not evidence.exists() or not any(evidence.glob("*.json")):
        print(f"  [error] no evidence packs found in {evidence}")
        print("          run the Python AA pipeline first (aa_runner.py --run).")
        return False

    llm_root.mkdir(parents=True, exist_ok=True)
    results = []
    for stage in LLM_STAGES:
        read_dirs = _resolve_read_dirs(stage["reads"], aa_root, llm_root)
        if stage["reads"] == "workflow":
            context = (f"### AGENTS.md\n```\n{_read_text(AGENTS_FILE)[:3500]}\n```\n\n"
                       + _collect_context(read_dirs))
        else:
            context = _collect_context(read_dirs)
        results.append(_run_llm_stage(stage, context, llm_root, input_dir))

    ok = sum(1 for r in results if r["ok"])
    print("\n" + "=" * 60)
    print(f"AA CLAUDE CHAIN COMPLETE — {ok}/{len(LLM_STAGES)} stages produced output")
    print("=" * 60)
    for r in results:
        flag = "OK" if r["ok"] else "--"
        print(f"  [{flag}] {r['id']:<34} {len(r['saved'])} file(s)")
    print(f"  Location : {llm_root}")
    print("=" * 60 + "\n")
    return ok > 0


# ── Pipeline invocation ────────────────────────────────────────────────────────

def run_aa_pipeline(repo_root: str, input_dir: str) -> bool:
    output_root = Path(input_dir) / "aa-outputs"
    output_root.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(ORCHESTRATOR),
        "--repo-root",   str(repo_root),
        "--output-root", str(output_root),
        "--no-source-guard",
    ]

    print("\n  Running AA pipeline (pure Python — no LLM)...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )
    except FileNotFoundError as exc:
        print(f"  [error] orchestrator not found: {exc}")
        return False
    except subprocess.TimeoutExpired:
        print("  [warn] AA pipeline timed out after 600s")
        return False

    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)

    if result.returncode != 0:
        print(f"  [warn] AA pipeline exited with code {result.returncode}")
        return False

    return True


# ── Output reporting ───────────────────────────────────────────────────────────

def print_summary(input_dir: str):
    output_root = Path(input_dir) / "aa-outputs"
    print("\n" + "=" * 60)
    print("AA PIPELINE COMPLETE — APPLICATION ARCHITECTURE EXTRACTED")
    print("=" * 60)

    found = 0
    for rel in FINAL_OUTPUTS:
        path = output_root / rel
        if path.exists():
            size = f"{path.stat().st_size / 1024:.1f} KB"
            found += 1
        else:
            size = "MISSING"
        print(f"  {rel:<55} {size}")

    print(f"\n  {found}/{len(FINAL_OUTPUTS)} outputs present")
    print(f"  Location : {output_root}")
    print("=" * 60 + "\n")


def print_manual_instructions(repo_root: str, input_dir: str):
    output_root = Path(input_dir) / "aa-outputs"
    print("\n" + "=" * 60)
    print("AA PIPELINE — TASK READY")
    print("=" * 60)
    print(f"\n  Repo root  : {repo_root}")
    print(f"  Output     : {output_root}")
    print(f"\n  To run manually:")
    print(f"    python \"{ORCHESTRATOR}\" \\")
    print(f"      --repo-root \"{repo_root}\" \\")
    print(f"      --output-root \"{output_root}\" \\")
    print(f"      --no-source-guard")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AA Runner — Application Architecture extraction pipeline wrapper"
    )
    parser.add_argument(
        "--repo-root", default=None,
        help="Path to the extracted source code (from Layer 1). Required unless --llm-only.",
    )
    parser.add_argument(
        "--input", required=True,
        help="Layer 1 output directory (e.g. output/eShopOnWeb)",
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Run the pipeline automatically (Python analyzer, then the claude stage chain)",
    )
    parser.add_argument(
        "--skip-llm", action="store_true",
        help="Run only the deterministic Python analyzer; skip the claude stage chain",
    )
    parser.add_argument(
        "--llm-only", action="store_true",
        help="Skip the Python analyzer and run only the claude stage chain "
             "(requires existing aa-outputs/evidence-packs/)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"ERROR: --input not found: {args.input}")
        sys.exit(1)

    # ── llm-only: run just the claude chain over existing evidence packs ──────
    if args.llm_only:
        print("\n" + "=" * 60)
        print("BA PIPELINE — APPLICATION ARCHITECTURE (claude chain only)")
        print("=" * 60)
        print(f"  Input  : {args.input}")
        print("=" * 60)
        if not run_aa_claude_chain(args.input):
            sys.exit(1)
        return

    if not args.repo_root or not os.path.isdir(args.repo_root):
        print(f"ERROR: --repo-root not found: {args.repo_root}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BA PIPELINE — APPLICATION ARCHITECTURE EXTRACTION")
    print("=" * 60)
    print(f"  Repo root : {args.repo_root}")
    print(f"  Input     : {args.input}")
    print(f"  Output    : {Path(args.input) / 'aa-outputs'}")
    print(f"  Claude    : {'skipped (--skip-llm)' if args.skip_llm else 'stages 04→07 after Python analyzer'}")
    print("=" * 60 + "\n")

    if args.run:
        success = run_aa_pipeline(args.repo_root, args.input)
        if success:
            print_summary(args.input)
            if not args.skip_llm:
                chain_ok = run_aa_claude_chain(args.input)
                if not chain_ok:
                    sys.exit(1)
        else:
            print_manual_instructions(args.repo_root, args.input)
            sys.exit(1)
    else:
        print_manual_instructions(args.repo_root, args.input)


if __name__ == "__main__":
    main()
