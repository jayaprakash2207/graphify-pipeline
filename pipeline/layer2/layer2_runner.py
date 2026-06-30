"""
Layer 2 Runner
--------------
Reads Layer 1 JSON output, combines with layer2_prompt.md,
and writes a ready-to-run agent task file.

Small projects (< SMALL_THRESHOLD business artifacts): single Claude call.
Large projects (>= SMALL_THRESHOLD business artifacts): domain-chunked mode —
  splits artifacts by top-level module, runs up to MAX_CHUNKS parallel Claude
  calls, then merges and deduplicates the results.

Usage:
    python layer2/layer2_runner.py --input output/eShopOnWeb
    python layer2/layer2_runner.py --input output/eShopOnWeb --run
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "01_BA_Agent1_StructuralScout.md"
MAX_METHODS       = 80
MAX_CONFIG_PARAMS = 60

SMALL_THRESHOLD = 500   # below this → single Claude call
CHUNK_METHODS   = 80    # business methods per domain chunk
MAX_CHUNKS      = 6     # max parallel Claude calls


def _claude_cmd() -> list:
    """Return base claude CLI command. Uses cmd /c on Windows to execute .cmd scripts."""
    if sys.platform == "win32":
        return ["cmd", "/c", "claude", "-p", "--output-format", "text", "--no-session-persistence"]
    found = shutil.which("claude")
    if not found:
        raise FileNotFoundError("claude CLI not found. Install from https://claude.ai/code")
    return [found, "-p", "--output-format", "text", "--no-session-persistence"]


def load_layer1_outputs(input_dir: str) -> dict:
    base = Path(input_dir)

    def read(filename):
        path = base / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    return {
        "source_code": read("source_code.json"),
        "database":    read("database.json"),
        "config":      read("config.json"),
        "summary":     read("extraction_summary.json"),
    }


# ── Single-call mode (small projects) ─────────────────────────────────────────

def build_agent_context(data: dict) -> dict:
    """
    Trim the raw Layer 1 output to a focused subset that fits
    comfortably in a single agent context window.
    """
    source = data.get("source_code", [])
    db     = data.get("database", {})
    cfg    = data.get("config", {})

    business_methods = [
        {
            "name":              a.get("name"),
            "type":              a.get("type"),
            "business_category": a.get("business_category"),
            "source_file":       a.get("source_file"),
            "content":           a.get("content", "")[:800],
            "metadata":          a.get("metadata", {}),
        }
        for a in source
        if a.get("is_business_artifact")
    ][:MAX_METHODS]

    structural = [
        {
            "name":        a.get("name"),
            "type":        a.get("type"),
            "source_file": a.get("source_file"),
        }
        for a in source
        if not a.get("is_business_artifact") and a.get("type") in ("class", "interface", "enum")
    ][:40]

    db_context = {
        "tables":            db.get("tables", [])[:30],
        "ef_entities":       db.get("ef_entities", [])[:30],
        "stored_procedures": db.get("stored_procedures", [])[:20],
        "triggers":          db.get("triggers", []),
    }

    business_params  = cfg.get("business_params", [])[:MAX_CONFIG_PARAMS]
    feature_flags    = cfg.get("feature_flags", [])[:20]
    role_definitions = cfg.get("role_definitions", [])[:20]

    return {
        "business_methods": business_methods,
        "structural_types": structural,
        "database":         db_context,
        "config": {
            "business_params":  business_params,
            "feature_flags":    feature_flags,
            "role_definitions": role_definitions,
        },
        "extraction_summary": data.get("summary", {}),
    }


def build_full_prompt(context: dict) -> str:
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    data_section = json.dumps(context, indent=2, ensure_ascii=False)
    return f"{prompt_text}\n\n```json\n{data_section}\n```"


def save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "layer2_agent_task.md"
    task_path.write_text(prompt, encoding="utf-8")
    return str(task_path)


def _extract_json(raw: str):
    """Extract and parse JSON from a claude response string. Returns None on failure."""
    if "```json" in raw:
        try:
            start = raw.index("```json") + 7
            end   = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        except (ValueError, json.JSONDecodeError):
            pass
    if "```" in raw:
        try:
            start = raw.index("```") + 3
            end   = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        except (ValueError, json.JSONDecodeError):
            pass
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return None


def run_claude_agent(task_file: str, output_dir: str) -> bool:
    """
    Attempt to run the claude CLI with the task file.
    Returns True if successful, False if claude CLI is not available.
    """
    output_path = Path(output_dir) / "layer2_output.json"

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
        raw_out_path = Path(output_dir) / "layer2_output_raw.txt"
        partial = (e.stdout or "")
        raw_out_path.write_text(partial, encoding="utf-8")
        print(f"  Partial output saved -> {raw_out_path}")
        return False

    if result.returncode != 0:
        print(f"  [warn] claude CLI returned code {result.returncode}")
        print(f"  stderr: {result.stderr[:300]}")
        return False

    parsed = _extract_json(result.stdout)
    if parsed is None:
        raw_out_path = Path(output_dir) / "layer2_output_raw.txt"
        raw_out_path.write_text(result.stdout, encoding="utf-8")
        print("Claude returned non-JSON output. Raw output saved to layer2_output_raw.txt. Run convert_layer2.py to convert.")
        return False

    output_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Layer 2 output saved -> {output_path}")
    return True


# ── Chunked mode (large projects) ─────────────────────────────────────────────

def _module_key(source_file: str) -> str:
    """Return the top-level domain module name from a source file path."""
    if not source_file:
        return "unknown"
    # Normalise to forward-slash parts
    parts = Path(source_file.replace("\\", "/")).parts
    skip = {"", "/", "\\", "src", "main", "java", "kotlin", "lib", "app",
            "source", "sources", "code", "module", "modules"}
    for part in parts:
        clean = part.rstrip(":").lower()
        if clean not in skip and not part.endswith(":"):
            return part
    return parts[-2] if len(parts) >= 2 else "unknown"


def _build_shared_context(data: dict) -> dict:
    """Shared parts (DB, config, structural types) included in every chunk."""
    source = data.get("source_code", [])
    db     = data.get("database", {})
    cfg    = data.get("config", {})

    structural = [
        {"name": a.get("name"), "type": a.get("type"), "source_file": a.get("source_file")}
        for a in source
        if not a.get("is_business_artifact") and a.get("type") in ("class", "interface", "enum")
    ][:40]

    return {
        "structural_types": structural,
        "database": {
            "tables":            db.get("tables", [])[:30],
            "ef_entities":       db.get("ef_entities", [])[:30],
            "stored_procedures": db.get("stored_procedures", [])[:20],
            "triggers":          db.get("triggers", [])[:10],
        },
        "config": {
            "business_params":  cfg.get("business_params", [])[:MAX_CONFIG_PARAMS],
            "feature_flags":    cfg.get("feature_flags", [])[:20],
            "role_definitions": cfg.get("role_definitions", [])[:20],
        },
    }


def build_chunks(data: dict) -> list:
    """
    Split business artifacts into domain chunks by top-level module.
    Returns list of (module_name, context_dict) tuples.
    """
    source   = data.get("source_code", [])
    summary  = data.get("summary", {})
    business = [a for a in source if a.get("is_business_artifact")]

    # Group by module, sort largest first, keep top MAX_CHUNKS
    groups = {}
    for a in business:
        key = _module_key(a.get("source_file", ""))
        groups.setdefault(key, []).append(a)
    sorted_modules = sorted(groups.items(), key=lambda x: -len(x[1]))[:MAX_CHUNKS]

    shared          = _build_shared_context(data)
    total_artifacts = len(business)
    total_modules   = len(groups)

    chunks = []
    for module_name, artifacts in sorted_modules:
        methods = [
            {
                "name":              a.get("name"),
                "type":              a.get("type"),
                "business_category": a.get("business_category"),
                "source_file":       a.get("source_file"),
                "content":           a.get("content", "")[:800],
                "metadata":          a.get("metadata", {}),
            }
            for a in artifacts
        ][:CHUNK_METHODS]

        context = {
            "chunked_processing": {
                "module":          module_name,
                "chunk_artifacts": len(methods),
                "total_artifacts": total_artifacts,
                "total_modules":   total_modules,
                "note": (
                    "This is one domain chunk of a large codebase. "
                    "Analyse the provided business_methods and produce the full BA JSON output. "
                    "Shared structural, database, and config context is included for cross-referencing."
                ),
            },
            "business_methods": methods,
            **shared,
            "extraction_summary": summary,
        }
        chunks.append((module_name, context))

    return chunks


def _run_chunk(module_name: str, context: dict, prompt_text: str,
               results: list, raw_dir: Path, idx: int) -> None:
    """Run one Claude call for a domain chunk. Appends result dict to results."""
    data_section = json.dumps(context, indent=2, ensure_ascii=False)
    prompt = f"{prompt_text}\n\n```json\n{data_section}\n```"

    print(f"  [chunk {idx+1}] {module_name} ({len(context['business_methods'])} methods) — calling claude...")

    try:
        result = subprocess.run(
            _claude_cmd(),
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
            check=False,
        )
    except FileNotFoundError:
        print(f"  [chunk {idx+1}] {module_name} — claude CLI not found")
        results.append({"module": module_name, "data": None, "error": "claude_not_found"})
        return
    except subprocess.TimeoutExpired as e:
        print(f"  [chunk {idx+1}] {module_name} — timed out after 1200s")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in module_name)[:20]
        raw_path = raw_dir / f"layer2_chunk_{idx+1}_{safe_name}_raw.txt"
        raw_path.write_text(e.stdout or "", encoding="utf-8")
        results.append({"module": module_name, "data": None, "error": "timeout"})
        return

    raw = result.stdout.strip()
    # Save raw output for debugging
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in module_name)[:20]
    raw_path = raw_dir / f"layer2_chunk_{idx+1}_{safe_name}_raw.txt"
    raw_path.write_text(raw, encoding="utf-8")

    if result.returncode != 0:
        print(f"  [chunk {idx+1}] {module_name} — claude returned code {result.returncode}")
        results.append({"module": module_name, "data": None, "error": f"returncode_{result.returncode}"})
        return

    parsed = _extract_json(raw)
    if parsed:
        print(f"  [chunk {idx+1}] {module_name} — OK")
        results.append({"module": module_name, "data": parsed, "error": None})
    else:
        print(f"  [chunk {idx+1}] {module_name} — JSON parse failed (raw saved to {raw_path.name})")
        results.append({"module": module_name, "data": None, "error": "json_parse_failed"})


def _merge_lists(lists: list, key_field: str = "name") -> list:
    """Merge multiple lists, deduplicating by key_field."""
    seen = {}
    for lst in lists:
        if not isinstance(lst, list):
            continue
        for item in lst:
            if isinstance(item, dict):
                k = item.get(key_field) or item.get("id") or str(item)
            else:
                k = str(item)
            if k not in seen:
                seen[k] = item
    return list(seen.values())


def merge_layer2_outputs(chunk_results: list, summary: dict) -> dict:
    """Combine partial JSON outputs from multiple chunked Claude calls."""
    valid = [r["data"] for r in chunk_results if r.get("data")]
    if not valid:
        return {}

    merged = {}
    all_keys = set()
    for part in valid:
        all_keys.update(part.keys())

    for key in all_keys:
        values = [p[key] for p in valid if key in p]
        if not values:
            continue
        if all(isinstance(v, list) for v in values):
            merged[key] = _merge_lists(values)
        elif all(isinstance(v, dict) for v in values):
            merged[key] = values[0]
        else:
            merged[key] = next((v for v in values if v), values[0])

    if "analysis_metadata" not in merged:
        merged["analysis_metadata"] = {}
    if isinstance(merged.get("analysis_metadata"), dict):
        merged["analysis_metadata"]["chunked_processing"] = {
            "chunks_run":       len(chunk_results),
            "chunks_succeeded": len(valid),
            "modules":          [r["module"] for r in chunk_results],
            "total_artifacts":  summary.get("total_business_artifacts", 0),
        }

    return merged


def run_claude_agent_chunked(data: dict, output_dir: str) -> bool:
    """Split into domain chunks, run parallel Claude calls, merge and save results."""
    output_path = Path(output_dir) / "layer2_output.json"
    raw_dir     = Path(output_dir)

    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    chunks = build_chunks(data)
    if not chunks:
        print("  [warn] No chunks built — no business artifacts found")
        return False

    print(f"\n  Chunked mode: {len(chunks)} domain chunks, one at a time (sequential)...")

    # Run each chunk to completion before starting the next — no concurrent
    # claude calls, so chunks never contend for tokens.
    results = []
    for idx, (module_name, context) in enumerate(chunks):
        _run_chunk(module_name, context, prompt_text, results, raw_dir, idx)

    succeeded = sum(1 for r in results if r.get("data"))
    print(f"\n  {succeeded}/{len(chunks)} chunks succeeded")

    if succeeded == 0:
        print("  [warn] All chunks failed — no Layer 2 output produced")
        return False

    summary = data.get("summary", {})
    merged  = merge_layer2_outputs(results, summary)

    output_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"  Layer 2 output saved -> {output_path} ({size_kb:.1f} KB)")
    return True


# ── Shared UI ──────────────────────────────────────────────────────────────────

def print_manual_instructions(task_file: str, output_dir: str):
    print("\n" + "=" * 60)
    print("LAYER 2 TASK FILE READY")
    print("=" * 60)
    print(f"\n  Task file : {task_file}")
    print(f"\n  To run via claude CLI:")
    print(f"    claude -p \"$(cat '{task_file}')\"")
    print(f"\n  To run in Claude Code (this session):")
    print(f"    Say: 'process layer2_agent_task.md and save output to {output_dir}/layer2_output.json'")
    print(f"\n  Expected output: {output_dir}/layer2_output.json")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Layer 2 Runner - prepare and optionally run the BA extraction agent"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Layer 1 output directory (e.g. output/eShopOnWeb)"
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Attempt to run claude CLI automatically (needs claude in PATH)"
    )
    args = parser.parse_args()

    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BA PIPELINE - LAYER 2: PROCESSING")
    print("=" * 60)
    print(f"  Input  : {input_dir}")
    print(f"  Prompt : {PROMPT_FILE}")
    print("=" * 60 + "\n")

    # Step 1: Load Layer 1 outputs
    print("[1/3] Loading Layer 1 outputs...")
    data            = load_layer1_outputs(input_dir)
    summary         = data.get("summary", {})
    total_artifacts = summary.get("total_business_artifacts", 0)
    print(f"      business artifacts : {summary.get('total_business_artifacts', '?')}")
    print(f"      db objects         : {summary.get('total_db_objects', '?')}")
    print(f"      config params      : {summary.get('total_config_params', '?')}")

    large_project = isinstance(total_artifacts, int) and total_artifacts >= SMALL_THRESHOLD
    mode_label    = f"chunked (>= {SMALL_THRESHOLD})" if large_project else f"single-call (< {SMALL_THRESHOLD})"
    print(f"      mode               : {mode_label}")

    if not large_project:
        # ── Small project: single Claude call ──────────────────────────────────
        print("\n[2/3] Building agent context (trimming to fit)...")
        context = build_agent_context(data)
        print(f"      business methods   : {len(context['business_methods'])}")
        print(f"      structural types   : {len(context['structural_types'])}")
        print(f"      ef entities        : {len(context['database']['ef_entities'])}")
        print(f"      business params    : {len(context['config']['business_params'])}")

        print("\n[3/3] Writing agent task file...")
        full_prompt = build_full_prompt(context)
        task_file   = save_task_file(full_prompt, input_dir)
        size_kb     = os.path.getsize(task_file) / 1024
        print(f"      saved: {task_file} ({size_kb:.1f} KB)")

        if args.run:
            success = run_claude_agent(task_file, input_dir)
            if not success:
                print_manual_instructions(task_file, input_dir)
        else:
            print_manual_instructions(task_file, input_dir)

    else:
        # ── Large project: domain-chunked mode ────────────────────────────────
        print(f"\n[2/3] Partitioning {total_artifacts} artifacts into domain chunks...")
        chunks = build_chunks(data)
        print(f"      chunks planned     : {len(chunks)}")
        for i, (mod, ctx) in enumerate(chunks):
            print(f"      chunk {i+1}: {mod} ({len(ctx['business_methods'])} methods)")

        print("\n[3/3] Running chunked Claude agents...")
        if args.run:
            success = run_claude_agent_chunked(data, input_dir)
            if not success:
                print(
                    "\n  [info] Chunked run failed. "
                    "Check layer2_chunk_*_raw.txt files in the output directory."
                )
        else:
            # Save sample task file (first chunk) for manual inspection
            if chunks:
                module_name, first_ctx = chunks[0]
                prompt_text  = PROMPT_FILE.read_text(encoding="utf-8")
                data_section = json.dumps(first_ctx, indent=2, ensure_ascii=False)
                sample_prompt = f"{prompt_text}\n\n```json\n{data_section}\n```"
                task_file = save_task_file(sample_prompt, input_dir)
                size_kb   = os.path.getsize(task_file) / 1024
                print(f"      sample task (chunk 1/{len(chunks)}): {task_file} ({size_kb:.1f} KB)")
            print_manual_instructions(str(Path(input_dir) / "layer2_agent_task.md"), input_dir)


if __name__ == "__main__":
    main()
