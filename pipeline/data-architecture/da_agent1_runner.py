"""
DA Agent 1 Runner
-----------------
Reads Layer 1 JSON output, attempts live DB connections using
connection strings from config.json, then combines everything
with DA_REVERSE_ENGINEERING_PROMPT_GENERIC.md to produce a
ready-to-run agent task file.

Layer 1 DB artifacts (tables, EF entities, stored procedures)
are fed as supplementary context so the agent has pre-extracted
data to cross-reference against its own code reading.

Usage:
    python data-architecture/da_agent1_runner.py --input output/eShopOnWeb
    python data-architecture/da_agent1_runner.py --input output/eShopOnWeb --run
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

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "03_DA_Agent1_DataExtractor.md"


def _claude_cmd() -> list:
    """Return base claude CLI command. Uses cmd /c on Windows to execute .cmd scripts.

    --permission-mode acceptEdits lets the agent write output files directly
    (via project .claude/settings.json's Write(output/**) allowlist) without
    an interactive prompt, which would hang in headless mode.
    """
    if sys.platform == "win32":
        return ["cmd", "/c", "claude", "-p", "--output-format", "text",
                "--no-session-persistence", "--permission-mode", "acceptEdits"]
    found = shutil.which("claude")
    if not found:
        raise FileNotFoundError("claude CLI not found. Install from https://claude.ai/code")
    return [found, "-p", "--output-format", "text", "--no-session-persistence",
            "--permission-mode", "acceptEdits"]


EXPECTED_DA_FILES = [
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

_KV_RE = re.compile(r"([\w\s]+)=([^;]*)", re.IGNORECASE)


# ── Layer 1 loading ────────────────────────────────────────────────────────────

def load_layer1_outputs(input_dir: str) -> dict:
    base = Path(input_dir)

    def read_json(filename):
        path = base / filename
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError) as exc:
                raw_text = path.read_text(encoding="utf-8", errors="replace")
                save_path = base / f"{Path(filename).stem}_raw.txt"
                save_path.write_text(raw_text, encoding="utf-8")
                print(f"  [error] JSON parse failed for {filename}: {exc}")
                print(f"  [error] Raw content saved to {save_path}")
                return {}
        return {}

    return {
        "source_code": read_json("source_code.json"),
        "database":    read_json("database.json"),
        "config":      read_json("config.json"),
        "summary":     read_json("extraction_summary.json"),
    }


# ── DB connection handling ─────────────────────────────────────────────────────

def _parse_connection_string(value: str) -> dict:
    """Extract DB type and params from a connection string or URL. Returns {} if unrecognised."""
    value = value.strip()

    # URL format: postgresql://user:pass@host:port/db
    url_m = re.match(
        r"(postgresql|postgres|mysql|sqlite)(?:\+\w+)?://"
        r"(?:([^:@]*)(?::([^@]*))?@)?"
        r"([^/:]+)(?::(\d+))?(?:/(\w+))?",
        value, re.IGNORECASE,
    )
    if url_m:
        scheme   = url_m.group(1).lower()
        user     = url_m.group(2) or ""
        password = url_m.group(3) or ""
        host     = url_m.group(4) or "localhost"
        port     = url_m.group(5) or ("5432" if "postgres" in scheme else "3306")
        database = url_m.group(6) or ""
        db_type  = "postgresql" if "postgres" in scheme else scheme
        return {"db_type": db_type, "host": host, "port": port,
                "database": database, "user": user, "password": password}

    # SQLite file reference
    if re.search(r"\.(db|sqlite|sqlite3)", value, re.I) or "sqlite" in value.lower():
        ds = re.search(r"Data Source=([^;]+)", value, re.I)
        return {"db_type": "sqlite", "path": (ds.group(1).strip() if ds else value)}

    # Key=Value pairs
    kv = {k.strip().lower(): v.strip() for k, v in _KV_RE.findall(value) if v.strip()}
    if not kv:
        return {}

    host     = kv.get("server") or kv.get("data source") or kv.get("host") or "localhost"
    database = kv.get("database") or kv.get("initial catalog") or kv.get("dbname") or ""
    user     = kv.get("user id") or kv.get("uid") or kv.get("username") or kv.get("user") or ""
    password = kv.get("password") or kv.get("pwd") or ""
    port     = kv.get("port") or ""

    if "initial catalog" in kv or ("server" in kv and "uid" not in kv and "host" not in kv):
        db_type = "sqlserver"
        port = port or "1433"
    elif kv.get("uid"):
        db_type = "mysql"
        port = port or "3306"
    elif "host" in kv:
        db_type = "postgresql"
        port = port or "5432"
    else:
        db_type = "sqlserver"
        port = port or "1433"

    return {"db_type": db_type, "host": host, "port": port,
            "database": database, "user": user, "password": password}


def _build_db_command(parsed: dict) -> list:
    """Return the CLI command list to test connectivity, or [] if unsupported."""
    db_type  = parsed.get("db_type", "")
    host     = parsed.get("host", "localhost")
    port     = str(parsed.get("port", ""))
    database = parsed.get("database", "")
    user     = parsed.get("user", "")
    password = parsed.get("password", "")

    if db_type == "sqlserver":
        server = f"{host},{port}" if port else host
        cmd = ["sqlcmd", "-S", server, "-Q", "SELECT 1", "-t", "5", "-b"]
        if database:
            cmd += ["-d", database]
        if user:
            cmd += ["-U", user, "-P", password]
        return cmd

    if db_type in ("postgresql", "postgres"):
        cmd = ["psql", "-h", host, "-c", "SELECT 1", "--connect-timeout=5"]
        if port:
            cmd += ["-p", port]
        if user:
            cmd += ["-U", user]
        if database:
            cmd += ["-d", database]
        return cmd

    if db_type == "mysql":
        cmd = ["mysql", "-h", host, "-e", "SELECT 1", "--connect-timeout=5"]
        if port:
            cmd += ["-P", port]
        if user:
            cmd += ["-u", user]
        if password:
            cmd.append(f"-p{password}")
        if database:
            cmd.append(database)
        return cmd

    return []


def attempt_db_connections(connection_strings: list) -> list:
    """Try to connect to each DB found in Layer 1 config. Returns list of result dicts."""
    results = []
    seen = set()

    for cs in connection_strings:
        raw = cs.get("value", "").strip()
        if not raw or raw in seen:
            continue
        seen.add(raw)

        parsed = _parse_connection_string(raw)
        if not parsed:
            continue

        db_type = parsed.get("db_type", "")
        entry = {
            "config_key": cs.get("key", ""),
            "db_type":    db_type,
            "database":   parsed.get("database") or parsed.get("path", ""),
            "host":       parsed.get("host", ""),
        }

        # SQLite — just check if file exists
        if db_type == "sqlite":
            path = parsed.get("path", "")
            if path and Path(path).exists():
                entry["status"] = "CONNECTED"
                entry["detail"] = f"SQLite file accessible: {path}"
            else:
                entry["status"] = "CODE-ONLY"
                entry["reason"] = f"SQLite file not found: {path}"
            results.append(entry)
            continue

        cmd = _build_db_command(parsed)
        if not cmd:
            entry["status"] = "CODE-ONLY"
            entry["reason"] = f"No CLI tool configured for {db_type}"
            results.append(entry)
            continue

        entry["command_run"] = " ".join(str(c) for c in cmd)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=10, encoding="utf-8", errors="replace", check=False,
            )
            if proc.returncode == 0:
                entry["status"] = "CONNECTED"
                entry["detail"] = (
                    f"Connected — {parsed.get('database', '')} "
                    f"at {parsed.get('host', '')}:{parsed.get('port', '')}"
                )
            else:
                entry["status"] = "CODE-ONLY"
                entry["reason"] = (proc.stderr or proc.stdout or "non-zero exit").strip()[:300]
        except FileNotFoundError:
            entry["status"] = "CODE-ONLY"
            entry["reason"] = f"{cmd[0]} CLI not found in PATH"
        except subprocess.TimeoutExpired:
            entry["status"] = "CODE-ONLY"
            entry["reason"] = "Connection timed out after 10s"

        results.append(entry)

    return results


# ── Prompt building ────────────────────────────────────────────────────────────

def build_da_context(data: dict, db_results: list) -> dict:
    """Assemble the structured context dict fed to DA Agent 1."""
    source  = data.get("source_code", [])
    db      = data.get("database", {})
    cfg     = data.get("config", {})
    summary = data.get("summary", {})

    # Adaptive limits — scale down for large codebases to keep prompt size manageable
    total_artifacts = summary.get("total_business_artifacts", 0)
    if isinstance(total_artifacts, int) and total_artifacts > 5000:
        max_data_artifacts = 20
        max_config_params  = 30
        max_tables         = 40
        max_ef_entities    = 40
        max_procedures     = 15
    elif isinstance(total_artifacts, int) and total_artifacts > 1000:
        max_data_artifacts = 35
        max_config_params  = 50
        max_tables         = 60
        max_ef_entities    = 60
        max_procedures     = 20
    else:
        max_data_artifacts = 60
        max_config_params  = 80
        max_tables         = 100
        max_ef_entities    = 100
        max_procedures     = 40

    # Data-relevant source artifacts (entities, enums, value objects, repositories)
    data_artifacts = [
        {
            "name":        a.get("name"),
            "type":        a.get("type"),
            "source_file": a.get("source_file"),
            "content":     a.get("content", "")[:600],
            "metadata":    a.get("metadata", {}),
        }
        for a in source
        if a.get("type") in ("class", "struct", "enum", "interface")
    ][:max_data_artifacts]

    return {
        "extraction_summary":     summary,
        "connection_strings":     cfg.get("connection_strings", []),
        "db_connection_results":  db_results,
        "layer1_db_artifacts": {
            "tables":            db.get("tables", [])[:max_tables],
            "ef_entities":       db.get("ef_entities", [])[:max_ef_entities],
            "stored_procedures": db.get("stored_procedures", [])[:max_procedures],
            "triggers":          db.get("triggers", [])[:20],
            "views":             db.get("views", [])[:20],
        },
        "layer1_data_entities":   data_artifacts,
        "layer1_config_params":   cfg.get("all_params", [])[:max_config_params],
    }


def build_full_prompt(context: dict, da_output_dir: Path) -> str:
    """Build the full prompt. The agent writes each output file directly to
    disk (via its file tools) instead of printing file contents in its reply —
    this avoids the stdout-truncation problem entirely and keeps this a
    single claude call (so the large extracted-data context is only sent
    once)."""
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    out_dir = da_output_dir.resolve().as_posix()

    preamble = f"""\
I'm doing a data architecture review of a .NET codebase (eShopOnWeb-style
app) and I'd like your help producing a set of analysis documents.

Below is data already extracted from the codebase by a static-analysis tool:
EF Core entity definitions, configuration files, connection strings, and the
results of connection attempts against those connection strings. The full
source tree isn't included in this message, so please base your analysis on
this extracted data together with the entity names, types, and structure
shown, plus the detailed instructions further down in this message.

For anything that can't be directly confirmed from the data given (e.g. exact
PII field classifications, row counts, or constraints not visible in the EF
entities), give your best assessment based on naming conventions and typical
patterns for this kind of app, and label those items "INFERRED" so the
reader knows it wasn't confirmed against live data.

Please write each of the 13 files below directly to disk, using your file
tools, as soon as each one is ready — don't wait until the end, and don't
print file contents in your reply. Save each file to:

  {out_dir}/<filename>

e.g. {out_dir}/schema-catalogue.json

Once all 13 files are written, reply with a short checklist (one line per
filename, ✅ written or ❌ skipped with a reason) — that's all that needs to
be in your reply.

--- EXTRACTED DATA ---
"""
    output_reminder = f"""\

---

## Reminder on output

Please write all 13 files directly to {out_dir}/ using your file tools as
you go, then reply with just the ✅/❌ checklist:

1. schema-catalogue.json
2. erd.md
3. data-source-inventory.json
4. data-flow-map.md
5. pii-inventory.json
6. data-quality-report.md
7. migration-complexity.json
8. hidden-business-rules.json
9. storage-pattern-analysis.md
10. redundancy-analysis.json
11. data-dictionary.md
12. conceptual-data-model.md
13. access-control-matrix.md
"""
    try:
        data_section = json.dumps(context, indent=2, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        print(f"  [error] JSON serialisation failed: {exc} — context may contain non-serialisable data")
        data_section = "{}"
    return f"{preamble}\n```json\n{data_section}\n```\n\n---\n\n{prompt_text}{output_reminder}"


# ── Task file / agent invocation ───────────────────────────────────────────────

def save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "da_agent1_task.md"
    task_path.write_text(prompt, encoding="utf-8")
    return str(task_path)


def split_and_save_da_files(agent_output: str, da_output_dir: Path) -> list:
    """Parse ===DA_FILE_START:<name>===...===DA_FILE_END=== and write files."""
    da_output_dir.mkdir(parents=True, exist_ok=True)

    pattern = re.compile(
        r"===DA_FILE_START:(.+?)===(.*?)===DA_FILE_END===",
        re.DOTALL,
    )

    saved = []
    for match in pattern.finditer(agent_output):
        # Agent sometimes prefixes filenames with "da-outputs/" — strip it
        filename = Path(match.group(1).strip()).name
        content  = match.group(2).strip()
        file_path = da_output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        size_kb = file_path.stat().st_size / 1024
        print(f"  {filename:<42} {size_kb:>6.1f} KB")
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
            raw_path = Path(input_dir) / "da_agent1_raw.txt"
            raw_path.write_text(partial, encoding="utf-8")
            print(f"  [warn] partial output saved to {raw_path}")
        return None
    return result.returncode, result.stdout, result.stderr


def _build_retry_prompt(missing: list, task_file: str, da_output_dir: Path) -> str:
    file_list = "\n".join(f"- {f}" for f in missing)
    out_dir = da_output_dir.resolve().as_posix()
    return (
        f"These {len(missing)} file(s) are still missing from {out_dir}/:\n"
        f"{file_list}\n\n"
        f"The full task instructions (extracted data, output format, and "
        f"per-file requirements) are in {task_file} — please read that file "
        f"for context, then write these {len(missing)} file(s) directly to "
        f"{out_dir}/<filename> using your file tools now. Reply with a short "
        f"✅/❌ checklist when done."
    )


def run_claude_agent(prompt: str, task_file: str, input_dir: str) -> bool:
    """Call claude CLI once. The agent writes each of the 13 DA files
    directly to da-outputs/ via its file tools (see build_full_prompt), so
    we just check which expected files exist afterwards.

    Writing to disk instead of printing file contents in the reply avoids
    the stdout-truncation problem (a single reply containing 13 full files
    is too large for one claude -p invocation to return) without needing
    multiple calls — so the large extracted-data context is only sent once.

    If some files are still missing afterwards, send a small follow-up
    request (pointing back at the task file for full context) asking for
    just those files, up to _MAX_RETRIES times.
    """
    da_output_dir = Path(input_dir) / "da-outputs"
    da_output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = Path(input_dir) / "da_agent1_output_raw.txt"
    print("\n  Running DA Agent 1 (claude)...")

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
    print(f"  {agent_output[:500]}")

    # Fallback: in case the agent printed file contents instead of (or as
    # well as) writing them, also try parsing markers from stdout.
    split_and_save_da_files(agent_output, da_output_dir)

    existing = [f for f in EXPECTED_DA_FILES if (da_output_dir / f).exists()]
    missing = [f for f in EXPECTED_DA_FILES if f not in existing]

    attempt = 0
    while missing and attempt < _MAX_RETRIES:
        attempt += 1
        print(f"\n  [retry {attempt}/{_MAX_RETRIES}] {len(missing)} file(s) missing: {missing}")

        retry_prompt = _build_retry_prompt(missing, task_file, da_output_dir)
        call = _call_claude(retry_prompt, input_dir=input_dir)
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
        existing = [f for f in EXPECTED_DA_FILES if (da_output_dir / f).exists()]
        missing = [f for f in EXPECTED_DA_FILES if f not in existing]

    if missing:
        print(f"\n  [warn] Missing DA files: {missing}")

    print(f"\n  {len(existing)}/13 DA files present -> {da_output_dir}")
    return not missing


def print_manual_instructions(task_file: str, input_dir: str):
    da_dir = Path(input_dir) / "da-outputs"
    print("\n" + "=" * 60)
    print("DA AGENT 1 TASK FILE READY")
    print("=" * 60)
    print(f"\n  Task file : {task_file}")
    print("\n  To run in Claude Code (this session):")
    print("    Say: 'process da_agent1_task.md and save all 13 DA")
    print(f"          output files to {da_dir}'")
    print("\n  Note: --run asks the agent to write these files directly to")
    print(f"  {da_dir}/ using its file tools (rather than printing them),")
    print("  to avoid stdout truncation on a 13-file response.")
    print(f"\n  Expected output: {da_dir}/")
    for f in EXPECTED_DA_FILES:
        print(f"    - {f}")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DA Agent 1 Runner — data architecture extraction"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Layer 1 output directory (e.g. output/eShopOnWeb)"
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
    print("BA PIPELINE — DA AGENT 1: DATA ARCHITECTURE EXTRACTION")
    print("=" * 60)
    print(f"  Input  : {input_dir}")
    print(f"  Prompt : {PROMPT_FILE}")
    print("=" * 60 + "\n")

    # Step 1: Load Layer 1 outputs
    print("[1/4] Loading Layer 1 outputs...")
    data = load_layer1_outputs(input_dir)
    db   = data.get("database", {})
    cfg  = data.get("config", {})
    print(f"      Tables found       : {len(db.get('tables', []))}")
    print(f"      EF entities        : {len(db.get('ef_entities', []))}")
    print(f"      Connection strings : {len(cfg.get('connection_strings', []))}")

    # Step 2: Attempt live DB connections
    print("\n[2/4] Attempting database connections...")
    conn_strings = cfg.get("connection_strings", [])
    db_results   = attempt_db_connections(conn_strings)
    if db_results:
        for r in db_results:
            status  = r.get("status", "CODE-ONLY")
            db_name = r.get("database") or r.get("path", "?")
            print(f"      [{status:<10}] {r.get('db_type', '?')} — {db_name}")
    else:
        print("      No connection strings found — will proceed CODE-ONLY")

    # Step 3: Build context and task file
    print("\n[3/4] Building DA Agent 1 task file...")
    context   = build_da_context(data, db_results)
    da_output_dir = Path(input_dir) / "da-outputs"
    prompt    = build_full_prompt(context, da_output_dir)
    task_file = save_task_file(prompt, input_dir)
    size_kb   = os.path.getsize(task_file) / 1024
    print(f"      saved: {task_file} ({size_kb:.1f} KB)")

    # Step 4: Run or show instructions
    print("\n[4/4] Agent invocation...")
    if args.run:
        success = run_claude_agent(prompt, task_file, input_dir)
        if not success:
            print_manual_instructions(task_file, input_dir)
            sys.exit(1)
    else:
        print_manual_instructions(task_file, input_dir)


if __name__ == "__main__":
    main()
