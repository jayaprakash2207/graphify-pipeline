"""
DA Agent 2 Runner
-----------------
Reads the 13 DA output files produced by DA Agent 1,
combines them with DA_REVIEW_PROMPT.md, and writes a
ready-to-run review task file.

The agent enriches the 13 files (ADDED / CORRECTED / ENRICHED
change records) and produces review-summary.md. Updated file
contents are parsed from the agent output and saved back to
da-outputs/.

Usage:
    python data-architecture/da_agent2_runner.py --input output/eShopOnWeb
    python data-architecture/da_agent2_runner.py --input output/eShopOnWeb --run
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "04_DA_Agent2_DataReviewer.md"


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

DA_FILES = [
    "schema-catalogue.json",
    "erd.md",
    "data-source-inventory.json",
    "data-flow-map.md",
    "pii-inventory.json",
    "data-quality-report.md",
    "migration-complexity.json",
    "hidden-business-rules.json",
    "storage-pattern-analysis.md",
    "redundancy-analysis.json",
    "data-dictionary.md",
    "conceptual-data-model.md",
    "access-control-matrix.md",
]

# Max characters per DA file fed into the prompt (keeps context sane)
_MAX_CHARS_PER_FILE = 3000


# ── DA output loading ──────────────────────────────────────────────────────────

def load_da_outputs(input_dir: str) -> dict:
    """Read all 13 DA Agent 1 output files from da-outputs/."""
    da_dir = Path(input_dir) / "da-outputs"

    if not da_dir.exists():
        raise FileNotFoundError(
            f"da-outputs/ not found in {input_dir}\n"
            "Run da_agent1_runner.py first."
        )

    outputs = {}
    for filename in DA_FILES:
        path = da_dir / filename
        outputs[filename] = path.read_text(encoding="utf-8") if path.exists() else None

    found = sum(1 for v in outputs.values() if v is not None)
    if found < 10:
        raise FileNotFoundError(
            f"Only {found}/13 DA files found in {da_dir}.\n"
            "DA Agent 1 may not have completed. Run da_agent1_runner.py first."
        )
    return outputs


# ── Prompt building ────────────────────────────────────────────────────────────

def build_full_prompt(da_outputs: dict, da_output_dir: Path) -> str:
    """Build the full prompt. The agent updates files in place on disk (via
    its file tools) for any file it changes, and writes review-summary.md —
    instead of printing updated file contents in its reply. Avoids stdout
    truncation and keeps this a single claude call."""
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    out_dir = da_output_dir.resolve().as_posix()

    preamble = f"""\
I'd like you to review and enrich a set of data-architecture documents that
were produced in an earlier analysis pass. All 13 files from that pass are
included below as context sections. Please rely on your own knowledge for
any SQL verification queries.

The 13 files live on disk at {out_dir}/. For any file you make changes to
(including change records), please update it directly on disk at
{out_dir}/<filename> using your file tools, as soon as it's ready — don't
print updated file contents in your reply. If a file needs no changes, leave
it untouched.

Then write a `review-summary.md` summarizing the full review to
{out_dir}/review-summary.md using your file tools.

Once done, reply with a short checklist of which files you updated, plus
✅ review-summary.md written (or ❌ with a reason).

--- FILES FROM THE EARLIER ANALYSIS PASS ---
"""

    sections = []
    for filename, content in da_outputs.items():
        if content:
            # Cap content to keep total prompt within context limits
            preview = content[:_MAX_CHARS_PER_FILE]
            truncated = len(content) > _MAX_CHARS_PER_FILE
            tail = "\n... [truncated]" if truncated else ""
            sections.append(f"### {filename}\n```\n{preview}{tail}\n```")
        else:
            sections.append(f"### {filename}\n[NOT PRODUCED BY DA AGENT 1]")

    files_context = "\n\n".join(sections)

    output_reminder = f"""\

---

## Reminder on output

Apply all review phases (including Phase 5 cross-file consistency checks)
across the 13 files. Update any file you change directly at
{out_dir}/<filename> using your file tools, then write
{out_dir}/review-summary.md (required), then reply with the checklist.
"""

    return f"{preamble}\n{files_context}\n\n---\n\n{prompt_text}{output_reminder}"


# ── Task file / agent invocation ───────────────────────────────────────────────

def save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "da_agent2_task.md"
    task_path.write_text(prompt, encoding="utf-8")
    return str(task_path)


def split_and_save_da_files(agent_output: str, da_output_dir: Path) -> list:
    """Parse ===DA_FILE_START:<name>===...===DA_FILE_END=== and write/overwrite files."""
    pattern = re.compile(
        r"===DA_FILE_START:(.+?)===(.*?)===DA_FILE_END===",
        re.DOTALL,
    )

    saved = []
    for match in pattern.finditer(agent_output):
        filename = Path(match.group(1).strip()).name  # strip any path prefix e.g. da-outputs/
        content  = match.group(2).strip()
        file_path = da_output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        size_kb = file_path.stat().st_size / 1024
        tag = "[NEW    ]" if filename == "review-summary.md" else "[UPDATED]"
        print(f"  {tag} {filename:<40} {size_kb:>6.1f} KB")
        saved.append(filename)

    return saved


_MAX_RETRIES = 3


def _call_claude(prompt_content: str, timeout: int = 1200, input_dir: str = None):
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
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or "").strip()
        print(f"  [warn] claude CLI timed out after {timeout}s — saving partial output")
        if input_dir:
            raw_path = Path(input_dir) / "da_agent2_raw.txt"
            raw_path.write_text(partial, encoding="utf-8")
            print(f"  [warn] partial output saved to {raw_path}")
        return None
    return result.returncode, result.stdout, result.stderr


def _build_retry_prompt(task_file: str, da_output_dir: Path) -> str:
    out_dir = da_output_dir.resolve().as_posix()
    return (
        f"{out_dir}/review-summary.md is still missing.\n\n"
        f"The full task instructions (review context and output format) are "
        f"in {task_file} — please read that file for context, then write "
        f"{out_dir}/review-summary.md directly using your file tools now. "
        f"Reply with a short ✅/❌ confirmation when done."
    )


def run_claude_agent(prompt: str, task_file: str, input_dir: str) -> bool:
    """Call claude CLI once. The agent updates changed files in place and
    writes review-summary.md directly to disk, so we just check whether
    review-summary.md exists afterward and retry up to _MAX_RETRIES times if
    not. split_and_save_da_files is kept as a fallback in case the agent
    still prints file content via ===DA_FILE_START/END=== markers.
    """
    da_output_dir = Path(input_dir) / "da-outputs"
    raw_path = Path(input_dir) / "da_agent2_output_raw.txt"
    raw_path.write_text("", encoding="utf-8")
    print("\n  Running DA Agent 2 (claude)...")

    call = _call_claude(prompt, input_dir=input_dir)
    if call is None:
        return False
    returncode, stdout, stderr = call

    if returncode != 0:
        print(f"  [warn] claude CLI returned code {returncode}")
        print(f"  stderr: {stderr[:300]}")
        return False

    agent_output = stdout.strip()
    raw_path.write_text(agent_output, encoding="utf-8")
    print(f"\n  Agent reply:\n{agent_output[:2000]}")

    split_and_save_da_files(agent_output, da_output_dir)

    review_file = da_output_dir / "review-summary.md"

    attempt = 0
    while not review_file.exists() and attempt < _MAX_RETRIES:
        attempt += 1
        print(f"\n  [retry {attempt}/{_MAX_RETRIES}] review-summary.md missing")

        call = _call_claude(_build_retry_prompt(task_file, da_output_dir), input_dir=input_dir)
        if call is None:
            break
        returncode, stdout, stderr = call
        if returncode != 0:
            print(f"  [warn] claude CLI returned code {returncode} on retry")
            print(f"  stderr: {stderr[:300]}")
            break

        retry_output = stdout.strip()
        with raw_path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n--- RETRY {attempt} OUTPUT ---\n\n{retry_output}")

        split_and_save_da_files(retry_output, da_output_dir)

    if not review_file.exists():
        print("  [warn] review-summary.md was not produced")

    print(f"\n  done -> {da_output_dir}")
    return review_file.exists()


def print_manual_instructions(task_file: str, input_dir: str):
    da_dir = Path(input_dir) / "da-outputs"
    print("\n" + "=" * 60)
    print("DA AGENT 2 TASK FILE READY")
    print("=" * 60)
    print(f"\n  Task file : {task_file}")
    print(f"\n  To run in Claude Code (this session):")
    print(f"    Say: 'process da_agent2_task.md, update files in {da_dir},")
    print(f"          and write {da_dir}/review-summary.md'")
    print(f"\n  Expected new output: {da_dir}/review-summary.md")
    print("=" * 60 + "\n")


def print_summary(input_dir: str):
    da_dir = Path(input_dir) / "da-outputs"
    review = da_dir / "review-summary.md"
    print("\n" + "=" * 60)
    print("DA AGENT 2 COMPLETE — REVIEW FINISHED")
    print("=" * 60)
    print(f"  DA outputs     : {da_dir}")
    review_status = "review-summary.md exists" if review.exists() else "review-summary.md NOT produced"
    print(f"  Review summary : {review_status}")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DA Agent 2 Runner — data architecture review and enrichment"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Layer 1/DA output directory (e.g. output/eShopOnWeb)"
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Attempt to run claude CLI automatically"
    )
    args = parser.parse_args()

    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BA PIPELINE — DA AGENT 2: DATA ARCHITECTURE REVIEW")
    print("=" * 60)
    print(f"  Input  : {input_dir}")
    print(f"  Prompt : {PROMPT_FILE}")
    print("=" * 60 + "\n")

    # Step 1: Load DA Agent 1 outputs
    print("[1/3] Loading DA Agent 1 outputs...")
    try:
        da_outputs = load_da_outputs(input_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    found = sum(1 for v in da_outputs.values() if v is not None)
    print(f"      {found}/13 DA files loaded")

    # Show DB connection status from schema-catalogue
    schema_raw = da_outputs.get("schema-catalogue.json")
    if schema_raw:
        try:
            schema = json.loads(schema_raw)
            db_conn = schema.get("db_connection", "UNKNOWN")
            print(f"      DB connection from Agent 1: {str(db_conn)[:80]}")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Step 2: Build task file
    print("\n[2/3] Building DA Agent 2 task file...")
    da_output_dir = Path(input_dir) / "da-outputs"
    prompt    = build_full_prompt(da_outputs, da_output_dir)
    task_file = save_task_file(prompt, input_dir)
    size_kb   = os.path.getsize(task_file) / 1024
    print(f"      saved: {task_file} ({size_kb:.1f} KB)")

    # Step 3: Run or show instructions
    print("\n[3/3] Agent invocation...")
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
