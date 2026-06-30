"""
Layer 3 Runner
--------------
Reads Layer 2 output JSON, combines with layer3_prompt.md,
and writes a ready-to-run agent task file.
The agent output is split into 10 individual BA document .md files.

Usage:
    python layer3/layer3_runner.py --input output/eShopOnWeb
    python layer3/layer3_runner.py --input output/eShopOnWeb --run
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "02_BA_Agent2_DeepAnalyst.md"


def _claude_cmd() -> list:
    """Return base claude CLI command. Uses cmd /c on Windows to execute .cmd scripts."""
    if sys.platform == "win32":
        return ["cmd", "/c", "claude", "-p", "--output-format", "text", "--no-session-persistence"]
    found = shutil.which("claude")
    if not found:
        raise FileNotFoundError("claude CLI not found. Install from https://claude.ai/code")
    return [found, "-p", "--output-format", "text", "--no-session-persistence"]

EXPECTED_DOCUMENTS = [
    "01_capability_map.md",
    "02_value_stream.md",
    "03_process_models.md",
    "04_business_rules.md",
    "05_data_model.md",
    "06_stakeholder_map.md",
    "07_kpis_metrics.md",
    "08_motivation_model.md",
    "09_operating_model.md",
    "10_business_roadmap.md",
]


def load_layer2_output(input_dir: str) -> dict:
    path = Path(input_dir) / "layer2_output.json"
    if not path.exists():
        raise FileNotFoundError(
            f"layer2_output.json not found in {input_dir}\n"
            "Run layer2_runner.py first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_full_prompt(layer2_data: dict) -> str:
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    data_section = json.dumps(layer2_data, indent=2, ensure_ascii=False)
    return f"{prompt_text}\n\n```json\n{data_section}\n```"


def save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "layer3_agent_task.md"
    task_path.write_text(prompt, encoding="utf-8")
    return str(task_path)


def split_and_save_documents(agent_output: str, output_dir: str) -> list:
    """
    Parse the agent output and split into individual BA document files.
    Looks for ===DOCUMENT_START:<filename>=== and ===DOCUMENT_END=== markers.
    """
    docs_dir = Path(output_dir) / "ba_documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    pattern = re.compile(
        r"===DOCUMENT_START:(.+?)===(.*?)===DOCUMENT_END===",
        re.DOTALL,
    )

    saved = []
    for match in pattern.finditer(agent_output):
        filename = match.group(1).strip()
        content  = match.group(2).strip()

        file_path = docs_dir / filename
        file_path.write_text(content, encoding="utf-8")
        size_kb = file_path.stat().st_size / 1024
        print(f"  {filename:<35} {size_kb:>6.1f} KB")
        saved.append(filename)

    return saved


def run_claude_agent(task_file: str, input_dir: str) -> bool:
    print("\n  Running claude agent...")

    try:
        prompt_content = Path(task_file).read_text(encoding="utf-8")

        result = subprocess.run(
            _claude_cmd(),
            input=prompt_content,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
            check=False,
        )

    except FileNotFoundError:
        print("  [info] claude CLI not found in PATH")
        return False
    except subprocess.TimeoutExpired as e:
        print("  [warn] claude CLI timed out after 1200s")
        raw_path = Path(input_dir) / "layer3_output_raw.txt"
        raw_path.write_text(e.stdout or "", encoding="utf-8")
        print(f"  Partial output saved -> {raw_path}")
        return False

    if result.returncode != 0:
        print(f"  [warn] claude CLI returned code {result.returncode}")
        print(f"  stderr: {result.stderr[:300]}")
        return False

    agent_output = result.stdout.strip()

    # Save raw output
    raw_path = Path(input_dir) / "layer3_output_raw.txt"
    raw_path.write_text(agent_output, encoding="utf-8")

    # Check for expected markers before attempting to split
    if "===DOCUMENT_START===" not in agent_output:
        print("  [warn] Claude output does not contain ===DOCUMENT_START=== markers.")
        print(f"  Raw output saved to layer3_output_raw.txt — inspect it manually or re-run.")
        return False

    # Split into individual documents
    print("\n  Saving BA documents...")
    saved = split_and_save_documents(agent_output, input_dir)

    if not saved:
        print("  [warn] No documents found in agent output.")
        print(f"  Raw output saved -> {raw_path}")
        return False

    missing = [d for d in EXPECTED_DOCUMENTS if d not in saved]
    if missing:
        print(f"\n  [warn] Missing documents: {missing}")

    print(f"\n  {len(saved)}/10 documents saved -> {Path(input_dir) / 'ba_documents'}")
    return True


def print_manual_instructions(task_file: str, input_dir: str):
    docs_dir = Path(input_dir) / "ba_documents"
    print("\n" + "=" * 60)
    print("LAYER 3 TASK FILE READY")
    print("=" * 60)
    print(f"\n  Task file    : {task_file}")
    print(f"\n  To run via claude CLI:")
    print(f"    claude -p \"$(cat '{task_file}')\"")
    print(f"\n  To run in Claude Code (this session):")
    print(f"    Say: 'process layer3_agent_task.md and save the 10 BA")
    print(f"          documents to {docs_dir}'")
    print(f"\n  Expected output: {docs_dir}/")
    for doc in EXPECTED_DOCUMENTS:
        print(f"    - {doc}")
    print("=" * 60 + "\n")


def print_summary(input_dir: str):
    docs_dir = Path(input_dir) / "ba_documents"
    if not docs_dir.exists():
        return

    print("\n" + "=" * 60)
    print("LAYER 3 COMPLETE — BA DOCUMENTS GENERATED")
    print("=" * 60)

    total = 0
    for doc in EXPECTED_DOCUMENTS:
        path = docs_dir / doc
        if path.exists():
            size = path.stat().st_size / 1024
            total += 1
            print(f"  [{total:>2}/10] {doc}")

    print(f"\n  Documents     : {total}/10")
    print(f"  Location      : {docs_dir}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Layer 3 Runner - generate 10 BA documents from Layer 2 output"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Layer 1/2 output directory (e.g. output/eShopOnWeb)"
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
    print("BA PIPELINE - LAYER 3: BA DOCUMENT GENERATION")
    print("=" * 60)
    print(f"  Input  : {input_dir}")
    print(f"  Prompt : {PROMPT_FILE}")
    print("=" * 60 + "\n")

    # Step 1: Load Layer 2 output
    print("[1/3] Loading Layer 2 output...")
    try:
        layer2_data = load_layer2_output(input_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    meta = layer2_data.get("analysis_metadata", {})
    print(f"      business rules  : {meta.get('total_business_rules', '?')}")
    print(f"      entities        : {meta.get('total_entities', '?')}")
    print(f"      processes       : {meta.get('total_processes', '?')}")
    print(f"      roles           : {meta.get('total_roles', '?')}")
    print(f"      capabilities    : {meta.get('total_capabilities', '?')}")

    # Step 2: Build task file
    print("\n[2/3] Writing agent task file...")
    full_prompt = build_full_prompt(layer2_data)
    task_file = save_task_file(full_prompt, input_dir)
    size_kb = os.path.getsize(task_file) / 1024
    print(f"      saved: {task_file} ({size_kb:.1f} KB)")

    # Step 3: Run or show instructions
    print("\n[3/3] Agent invocation...")
    if args.run:
        success = run_claude_agent(task_file, input_dir)
        if success:
            print_summary(input_dir)
        else:
            print_manual_instructions(task_file, input_dir)
    else:
        print_manual_instructions(task_file, input_dir)


if __name__ == "__main__":
    main()
