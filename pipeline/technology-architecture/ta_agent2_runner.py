"""
TA Agent 2 Runner — Deep Analyst
----------------------------------
Reads the 6 inventory files produced by TA Agent 1 (Stack Scout), collects
deeper repo context for pattern/NFR/risk analysis, and combines everything
with TA_DEEPANALYST_PROMPT.md to produce a ready-to-run agent task file.

The agent produces 8 final TA outputs + ta-review-summary.md under ta-outputs/:
  technology-stack-assessment.md
  architecture-pattern-catalog.md
  component-interaction-contract-map.md
  data-architecture-assessment.md
  security-architecture-assessment.md
  nfr-registry.md
  technical-debt-risk-register.md
  operational-architecture-assessment.md
  ta-review-summary.md

Usage:
    python technology-architecture/ta_agent2_runner.py --repo-root /path/to/source --input output/eShopOnWeb
    python technology-architecture/ta_agent2_runner.py --repo-root /path/to/source --input output/eShopOnWeb --run
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from ta_agent1_runner import collect_repo_context

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "06_TA_Agent2_DeepAnalyst.md"

TA_AGENT1_FILES = [
    "technology-stack-inventory.md",
    "component-service-map.md",
    "data-store-registry.md",
    "infrastructure-deployment-blueprint.md",
    "integration-dependency-graph.md",
    "security-configuration-snapshot.md",
]

EXPECTED_TA2_FILES = [
    "technology-stack-assessment.md",
    "architecture-pattern-catalog.md",
    "component-interaction-contract-map.md",
    "data-architecture-assessment.md",
    "security-architecture-assessment.md",
    "nfr-registry.md",
    "technical-debt-risk-register.md",
    "operational-architecture-assessment.md",
    "ta-review-summary.md",
]

# Max characters per Agent 1 file fed into the prompt (keeps context sane)
_MAX_CHARS_PER_FILE = 3000


def _claude_cmd() -> list:
    """Return base claude CLI command. Uses cmd /c on Windows to execute .cmd scripts.

    --permission-mode acceptEdits lets the agent write its output files
    directly to disk (via Write/Edit tools) without an interactive prompt,
    which is required for the write-to-disk output approach used here.
    """
    if sys.platform == "win32":
        return ["cmd", "/c", "claude", "-p", "--output-format", "text", "--no-session-persistence", "--permission-mode", "acceptEdits"]
    found = shutil.which("claude")
    if not found:
        raise FileNotFoundError("claude CLI not found. Install from https://claude.ai/code")
    return [found, "-p", "--output-format", "text", "--no-session-persistence", "--permission-mode", "acceptEdits"]


# ── TA Agent 1 output loading ───────────────────────────────────────────────────

def load_ta_agent1_outputs(input_dir: str) -> dict:
    """Read TA Agent 1's 6 output files from ta-outputs/ta_agent1/."""
    ta_dir = Path(input_dir) / "ta-outputs" / "ta_agent1"

    if not ta_dir.exists():
        raise FileNotFoundError(
            f"ta-outputs/ta_agent1/ not found in {input_dir}\n"
            "Run ta_agent1_runner.py first."
        )

    outputs = {}
    for filename in TA_AGENT1_FILES:
        path = ta_dir / filename
        outputs[filename] = path.read_text(encoding="utf-8") if path.exists() else None

    found = sum(1 for v in outputs.values() if v is not None)
    if found < 3:
        raise FileNotFoundError(
            f"Only {found}/6 TA Agent 1 files found in {ta_dir}.\n"
            "TA Agent 1 may not have completed. Run ta_agent1_runner.py first."
        )
    return outputs


# ── Prompt building ────────────────────────────────────────────────────────────

def build_full_prompt(ta1_outputs: dict, repo_context: str, ta_output_dir: Path) -> str:
    """Build the full prompt. The agent writes each of the 9 output files
    directly to disk (via its file tools) instead of printing file contents
    in its reply — avoids stdout truncation and keeps this a single claude
    call (so the large context is only sent once)."""
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    out_dir = ta_output_dir.resolve().as_posix()

    preamble = f"""\
I'm doing a deeper technology architecture analysis of a codebase, building
on an earlier "Stack Scout" inventory pass. That pass produced 6 inventory
files, included below as ground truth context, followed by deeper repo files
for pattern/NFR/risk analysis (including CI/CD pipeline files for the
Operational Architecture Assessment).

Please write each of the 9 output files below directly to disk, using your
file tools, as soon as each one is ready — don't wait until the end, and
don't print file contents in your reply. Save each file to:

  {out_dir}/<filename>

e.g. {out_dir}/technology-stack-assessment.md

Once all 9 files are written, reply with a short checklist (one line per
filename, ✅ written or ❌ skipped with a reason).

--- STACK SCOUT INVENTORY FILES (from the earlier pass) ---
"""

    sections = []
    for filename, content in ta1_outputs.items():
        if content:
            preview = content[:_MAX_CHARS_PER_FILE]
            truncated = len(content) > _MAX_CHARS_PER_FILE
            tail = "\n... [truncated]" if truncated else ""
            sections.append(f"### {filename}\n```\n{preview}{tail}\n```")
        else:
            sections.append(f"### {filename}\n[NOT PRODUCED BY TA AGENT 1]")

    ta1_section = "\n\n".join(sections)

    output_reminder = f"""\

---

## Reminder on output

Please write all 9 files directly to {out_dir}/ using your file tools as you
go, then reply with the ✅/❌ checklist:

1. technology-stack-assessment.md
2. architecture-pattern-catalog.md
3. component-interaction-contract-map.md
4. data-architecture-assessment.md
5. security-architecture-assessment.md
6. nfr-registry.md
7. technical-debt-risk-register.md
8. operational-architecture-assessment.md
9. ta-review-summary.md
"""

    return (
        f"{preamble}\n{ta1_section}\n\n"
        f"--- DEEP REPO CONTEXT (incl. CI/CD pipeline files) ---\n{repo_context}\n\n"
        f"---\n\n{prompt_text}{output_reminder}"
    )


# ── Task file / agent invocation ───────────────────────────────────────────────

def save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "ta_agent2_task.md"
    task_path.write_text(prompt, encoding="utf-8")
    return str(task_path)


def split_and_save_ta_files(agent_output: str, ta_output_dir: Path) -> list:
    """Parse ===TA_FILE_START:<name>===...===TA_FILE_END=== and write files."""
    ta_output_dir.mkdir(parents=True, exist_ok=True)

    pattern = re.compile(r"===TA_FILE_START:(.+?)===(.*?)===TA_FILE_END===", re.DOTALL)

    saved = []
    for match in pattern.finditer(agent_output):
        filename = Path(match.group(1).strip()).name
        content = match.group(2).strip()
        file_path = ta_output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        size_kb = file_path.stat().st_size / 1024
        print(f"  {filename:<42} {size_kb:>6.1f} KB")
        saved.append(filename)

    return saved


_MAX_RETRIES = 3


def _call_claude(prompt_content: str, input_dir: str = None, timeout: int = 1200):
    """Run claude CLI with the given prompt. Returns (returncode, stdout, stderr) or None on launch failure."""
    try:
        result = subprocess.run(
            _claude_cmd(),
            input=prompt_content,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        print("  [info] claude CLI not found in PATH")
        return None
    except subprocess.TimeoutExpired as e:
        print(f"  [warn] claude CLI timed out after {timeout}s — saving partial output")
        if input_dir is not None:
            partial = (e.output or b"").decode("utf-8", errors="replace") if isinstance(e.output, bytes) else (e.output or "")
            raw_path = Path(input_dir) / "ta_agent2_raw.txt"
            raw_path.write_text(partial, encoding="utf-8")
            print(f"  [warn] partial output saved to {raw_path}")
        return False
    return result.returncode, result.stdout, result.stderr


def _build_retry_prompt(missing: list, task_file: str, ta_output_dir: Path) -> str:
    file_list = "\n".join(f"- {f}" for f in missing)
    out_dir = ta_output_dir.resolve().as_posix()
    return (
        f"These {len(missing)} file(s) are still missing from {out_dir}/:\n"
        f"{file_list}\n\n"
        f"The full task instructions (Stack Scout inventory, repo context, "
        f"output format, and per-file requirements) are in {task_file} — "
        f"please read that file for context, then write these {len(missing)} "
        f"file(s) directly to {out_dir}/<filename> using your file tools now. "
        f"Reply with a short ✅/❌ checklist when done."
    )


def run_claude_agent(prompt: str, task_file: str, input_dir: str) -> bool:
    """Call claude CLI once. The agent writes its 9 output files directly to
    disk, so we just check which of EXPECTED_TA2_FILES exist afterward and
    retry (asking only for the missing ones) up to _MAX_RETRIES times.
    split_and_save_ta_files is kept as a fallback in case the agent still
    prints file content via ===TA_FILE_START/END=== markers.
    """
    ta_output_dir = Path(input_dir) / "ta-outputs"
    ta_output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = Path(input_dir) / "ta_agent2_output_raw.txt"
    raw_path.write_text("", encoding="utf-8")
    print("\n  Running TA Agent 2 - Deep Analyst (claude)...")

    call = _call_claude(prompt, input_dir=input_dir)
    if call is None or call is False:
        return False
    returncode, stdout, stderr = call

    if returncode != 0:
        print(f"  [warn] claude CLI returned code {returncode}")
        print(f"  stderr: {stderr[:300]}")
        return False

    agent_output = stdout.strip()
    raw_path.write_text(agent_output, encoding="utf-8")
    print(f"\n  Agent reply:\n{agent_output[:2000]}")

    split_and_save_ta_files(agent_output, ta_output_dir)

    missing = [f for f in EXPECTED_TA2_FILES if not (ta_output_dir / f).exists()]

    attempt = 0
    while missing and attempt < _MAX_RETRIES:
        attempt += 1
        print(f"\n  [retry {attempt}/{_MAX_RETRIES}] missing file(s): {missing}")

        retry_prompt = _build_retry_prompt(missing, task_file, ta_output_dir)
        call = _call_claude(retry_prompt, input_dir=input_dir)
        if call is None or call is False:
            break
        returncode, stdout, stderr = call
        if returncode != 0:
            print(f"  [warn] claude CLI returned code {returncode} on retry")
            print(f"  stderr: {stderr[:300]}")
            break

        retry_output = stdout.strip()
        with raw_path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n--- RETRY {attempt} OUTPUT ---\n\n{retry_output}")

        split_and_save_ta_files(retry_output, ta_output_dir)
        missing = [f for f in EXPECTED_TA2_FILES if not (ta_output_dir / f).exists()]

    if missing:
        print(f"  [warn] missing TA Agent 2 file(s): {missing}")

    saved_count = len(EXPECTED_TA2_FILES) - len(missing)
    print(f"\n  {saved_count}/9 TA Agent 2 files present -> {ta_output_dir}")
    return not missing


def print_manual_instructions(task_file: str, input_dir: str):
    ta_dir = Path(input_dir) / "ta-outputs"
    print("\n" + "=" * 60)
    print("TA AGENT 2 (DEEP ANALYST) TASK FILE READY")
    print("=" * 60)
    print(f"\n  Task file : {task_file}")
    print("\n  To run in Claude Code (this session):")
    print("    Say: 'process ta_agent2_task.md and write all 9 TA")
    print(f"          output files directly to {ta_dir}'")
    print(f"\n  Expected output: {ta_dir}/")
    for f in EXPECTED_TA2_FILES:
        print(f"    - {f}")
    print("=" * 60 + "\n")


def print_summary(input_dir: str):
    ta_dir = Path(input_dir) / "ta-outputs"
    review = ta_dir / "ta-review-summary.md"
    print("\n" + "=" * 60)
    print("TA AGENT 2 COMPLETE — TECHNOLOGY ARCHITECTURE ANALYSIS FINISHED")
    print("=" * 60)
    print(f"  TA outputs     : {ta_dir}")
    review_status = "ta-review-summary.md exists" if review.exists() else "ta-review-summary.md NOT produced"
    print(f"  Review summary : {review_status}")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TA Agent 2 Runner — Technology Architecture deep analysis"
    )
    parser.add_argument(
        "--repo-root", required=True,
        help="Path to the extracted source code (from Layer 1)",
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Layer 1/TA output directory (e.g. output/eShopOnWeb)",
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Attempt to run claude CLI automatically",
    )
    args = parser.parse_args()

    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)
    if not os.path.isdir(args.repo_root):
        print(f"ERROR: --repo-root not found: {args.repo_root}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BA PIPELINE — TA AGENT 2: DEEP ANALYST")
    print("=" * 60)
    print(f"  Repo root : {args.repo_root}")
    print(f"  Input     : {input_dir}")
    print(f"  Prompt    : {PROMPT_FILE}")
    print("=" * 60 + "\n")

    print("[1/4] Loading TA Agent 1 outputs...")
    try:
        ta1_outputs = load_ta_agent1_outputs(input_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    found = sum(1 for v in ta1_outputs.values() if v is not None)
    print(f"      {found}/6 TA Agent 1 files loaded")

    print("\n[2/4] Collecting deep repo context (incl. CI/CD pipeline files)...")
    repo_context = collect_repo_context(args.repo_root, cap_per_file=4000, max_files=80)
    file_count = repo_context.count("### ")
    print(f"      {file_count} relevant file(s) collected")

    print("\n[3/4] Building TA Agent 2 task file...")
    ta_output_dir = Path(input_dir) / "ta-outputs"
    prompt = build_full_prompt(ta1_outputs, repo_context, ta_output_dir)
    task_file = save_task_file(prompt, input_dir)
    size_kb = os.path.getsize(task_file) / 1024
    print(f"      saved: {task_file} ({size_kb:.1f} KB)")

    print("\n[4/4] Agent invocation...")
    if args.run:
        success = run_claude_agent(prompt, task_file, input_dir)
        if success:
            print_summary(input_dir)
        else:
            print_manual_instructions(task_file, input_dir)
            sys.exit(1)
    else:
        print_manual_instructions(task_file, input_dir)


if __name__ == "__main__":
    main()
