"""
TA Agent 1 Runner — Stack Scout
--------------------------------
Scans the extracted repo source for technology-architecture evidence
(manifests, Dockerfiles, compose/k8s/Terraform manifests, CI/CD pipeline
files, config files) and combines it with TA_STACKSCOUT_PROMPT.md to
produce a ready-to-run agent task file.

The agent produces 6 inventory files under ta-outputs/ta_agent1/:
  technology-stack-inventory.md
  component-service-map.md
  data-store-registry.md
  infrastructure-deployment-blueprint.md
  integration-dependency-graph.md
  security-configuration-snapshot.md

Usage:
    python technology-architecture/ta_agent1_runner.py --repo-root /path/to/source --input output/eShopOnWeb
    python technology-architecture/ta_agent1_runner.py --repo-root /path/to/source --input output/eShopOnWeb --run
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

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "05_TA_Agent1_StackScout.md"

EXPECTED_TA1_FILES = [
    "technology-stack-inventory.md",
    "component-service-map.md",
    "data-store-registry.md",
    "infrastructure-deployment-blueprint.md",
    "integration-dependency-graph.md",
    "security-configuration-snapshot.md",
]

# Directories / patterns excluded from repo scanning
_EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".nuxt",
    "__pycache__", "coverage", ".cache", "vendor", "bin", "obj",
}
_EXCLUDE_SUFFIXES = (".min.js", ".bundle.js", ".map", ".compiled.js", ".compiled.ts")

# Filename patterns considered relevant for technology architecture scanning
_RELEVANT_PATTERNS = [
    re.compile(r"^package\.json$", re.I),
    re.compile(r"^package-lock\.json$", re.I),
    re.compile(r".*\.csproj$", re.I),
    re.compile(r".*\.sln$", re.I),
    re.compile(r"^pom\.xml$", re.I),
    re.compile(r"^build\.gradle(\.kts)?$", re.I),
    re.compile(r"^requirements.*\.txt$", re.I),
    re.compile(r"^pyproject\.toml$", re.I),
    re.compile(r"^go\.mod$", re.I),
    re.compile(r"^Gemfile$", re.I),
    re.compile(r"^Dockerfile.*$", re.I),
    re.compile(r"^docker-compose.*\.ya?ml$", re.I),
    re.compile(r".*\.tf$", re.I),
    re.compile(r".*\.tfvars$", re.I),
    re.compile(r"^(deployment|service|ingress|configmap|statefulset|daemonset|job|cronjob).*\.ya?ml$", re.I),
    re.compile(r"^Jenkinsfile$", re.I),
    re.compile(r"^azure-pipelines\.ya?ml$", re.I),
    re.compile(r"^\.gitlab-ci\.ya?ml$", re.I),
    re.compile(r"^bitbucket-pipelines\.ya?ml$", re.I),
    re.compile(r"^appsettings.*\.json$", re.I),
    re.compile(r"^application.*\.(yml|yaml|properties)$", re.I),
    re.compile(r"^\.env(\.example|\.sample)?$", re.I),
    re.compile(r"^nginx.*\.conf$", re.I),
    re.compile(r"^web\.config$", re.I),
]

# Directories scanned in full for CI/CD and IaC files regardless of filename pattern
_ALWAYS_SCAN_DIRS = {".github", ".circleci", "k8s", "kubernetes", "manifests", "terraform", "infra", "infrastructure", "helm"}


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


def _is_relevant(path: Path, repo_root: Path) -> bool:
    if any(path.name.endswith(suf) for suf in _EXCLUDE_SUFFIXES):
        return False
    try:
        rel_parts = path.relative_to(repo_root).parts
    except ValueError:
        rel_parts = path.parts
    if any(part in _ALWAYS_SCAN_DIRS for part in rel_parts[:-1]):
        return path.suffix.lower() in (".yml", ".yaml", ".tf", ".tfvars", ".json", "") or path.name in ("Jenkinsfile",)
    return any(p.match(path.name) for p in _RELEVANT_PATTERNS)


def collect_repo_context(repo_root: str, cap_per_file: int = 4000, max_files: int = 80) -> str:
    """Walk the repo root and collect relevant technology-architecture files."""
    root = Path(repo_root)
    sections = []
    count = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS and not d.startswith(".") or d in _ALWAYS_SCAN_DIRS]
        if count >= max_files:
            break
        for filename in sorted(filenames):
            if count >= max_files:
                break
            file_path = Path(dirpath) / filename
            if not _is_relevant(file_path, root):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not text.strip():
                continue
            truncated = len(text) > cap_per_file
            body = text[:cap_per_file] + ("\n... [truncated]" if truncated else "")
            try:
                rel = file_path.relative_to(root).as_posix()
            except ValueError:
                rel = file_path.name
            sections.append(f"### {rel}\n```\n{body}\n```")
            count += 1

    return "\n\n".join(sections) if sections else "[no relevant technology files found]"


# ── Prompt building ────────────────────────────────────────────────────────────

def build_full_prompt(repo_context: str, ta_output_dir: Path) -> str:
    """Build the full prompt. The agent writes each output file directly to
    disk (via its file tools) instead of printing file contents in its reply —
    this avoids the stdout-truncation problem entirely and keeps this a
    single claude call (so the large repo-context is only sent once)."""
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    out_dir = ta_output_dir.resolve().as_posix()

    preamble = f"""\
I'm doing a technology architecture review of a codebase and would like your
help with the "Stack Scout" pass: building an inventory of the technology
stack, components, data stores, infrastructure, integrations, and security
configuration.

Below are the relevant repo files I've collected (manifests, Dockerfiles,
compose/k8s/Terraform manifests, CI/CD config, app config files). Please use
these as your scanning input for Chunk 0 and the layer-by-layer inventory
chunks described in the instructions further down — the full repo isn't
attached here, so work from what's provided rather than asking for more files.

Please write each of the 6 output files below directly to disk, using your
file tools, as soon as each one is ready — don't wait until the end, and
don't print file contents in your reply. Save each file to:

  {out_dir}/<filename>

e.g. {out_dir}/technology-stack-inventory.md

Once all 6 files are written, reply with a short checklist (one line per
filename, ✅ written or ❌ skipped with a reason) plus the Final Response
Assembly summary and Validation Queue as plain text — that's all that needs
to be in your reply.

--- REPO FILES (collected from repo root) ---
"""

    output_reminder = f"""\

---

## Reminder on output

Please write all 6 files directly to {out_dir}/ using your file tools as you
go, then reply with the ✅/❌ checklist plus the Final Response Assembly
summary and Validation Queue:

1. technology-stack-inventory.md
2. component-service-map.md
3. data-store-registry.md
4. infrastructure-deployment-blueprint.md
5. integration-dependency-graph.md
6. security-configuration-snapshot.md
"""

    return f"{preamble}\n{repo_context}\n\n---\n\n{prompt_text}{output_reminder}"


# ── Task file / agent invocation ───────────────────────────────────────────────

def save_task_file(prompt: str, input_dir: str) -> str:
    task_path = Path(input_dir) / "ta_agent1_task.md"
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
            raw_path = Path(input_dir) / "ta_agent1_raw.txt"
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
        f"The full task instructions (repo context, output format, and "
        f"per-file requirements) are in {task_file} — please read that file "
        f"for context, then write these {len(missing)} file(s) directly to "
        f"{out_dir}/<filename> using your file tools now. Reply with a short "
        f"✅/❌ checklist when done."
    )


def run_claude_agent(prompt: str, task_file: str, input_dir: str) -> bool:
    """Call claude CLI once. The agent writes its 6 output files directly to
    disk, so we just check which of EXPECTED_TA1_FILES exist afterward and
    retry (asking only for the missing ones) up to _MAX_RETRIES times.
    split_and_save_ta_files is kept as a fallback in case the agent still
    prints file content via ===TA_FILE_START/END=== markers.
    """
    ta_output_dir = Path(input_dir) / "ta-outputs" / "ta_agent1"
    ta_output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = Path(input_dir) / "ta_agent1_output_raw.txt"
    raw_path.write_text("", encoding="utf-8")
    print("\n  Running TA Agent 1 - Stack Scout (claude)...")

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

    missing = [f for f in EXPECTED_TA1_FILES if not (ta_output_dir / f).exists()]

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
        missing = [f for f in EXPECTED_TA1_FILES if not (ta_output_dir / f).exists()]

    if missing:
        print(f"  [warn] missing TA Agent 1 file(s): {missing}")

    saved_count = len(EXPECTED_TA1_FILES) - len(missing)
    print(f"\n  {saved_count}/6 TA Agent 1 files present -> {ta_output_dir}")
    return not missing


def print_manual_instructions(task_file: str, input_dir: str):
    ta_dir = Path(input_dir) / "ta-outputs" / "ta_agent1"
    print("\n" + "=" * 60)
    print("TA AGENT 1 (STACK SCOUT) TASK FILE READY")
    print("=" * 60)
    print(f"\n  Task file : {task_file}")
    print("\n  To run in Claude Code (this session):")
    print("    Say: 'process ta_agent1_task.md and write all 6 TA")
    print(f"          output files directly to {ta_dir}'")
    print(f"\n  Expected output: {ta_dir}/")
    for f in EXPECTED_TA1_FILES:
        print(f"    - {f}")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TA Agent 1 Runner — Technology Architecture stack scout"
    )
    parser.add_argument(
        "--repo-root", required=True,
        help="Path to the extracted source code (from Layer 1)",
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Layer 1 output directory (e.g. output/eShopOnWeb)",
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
    print("BA PIPELINE — TA AGENT 1: STACK SCOUT")
    print("=" * 60)
    print(f"  Repo root : {args.repo_root}")
    print(f"  Input     : {input_dir}")
    print(f"  Prompt    : {PROMPT_FILE}")
    print("=" * 60 + "\n")

    print("[1/3] Scanning repo for technology architecture evidence...")
    repo_context = collect_repo_context(args.repo_root)
    found = repo_context.count("### ")
    print(f"      {found} relevant file(s) collected")

    print("\n[2/3] Building TA Agent 1 task file...")
    ta_output_dir = Path(input_dir) / "ta-outputs" / "ta_agent1"
    prompt = build_full_prompt(repo_context, ta_output_dir)
    task_file = save_task_file(prompt, input_dir)
    size_kb = os.path.getsize(task_file) / 1024
    print(f"      saved: {task_file} ({size_kb:.1f} KB)")

    print("\n[3/3] Agent invocation...")
    if args.run:
        success = run_claude_agent(prompt, task_file, input_dir)
        if not success:
            print_manual_instructions(task_file, input_dir)
            sys.exit(1)
    else:
        print_manual_instructions(task_file, input_dir)


if __name__ == "__main__":
    main()
