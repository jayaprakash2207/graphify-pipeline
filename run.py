"""
Graphify Pipeline — Master Orchestrator
========================================
Single-command entry point that runs the entire Graphify pipeline end-to-end.

Usage examples:
    python run.py --source "https://github.com/org/repo" --output ./my-results
    python run.py --source "C:/path/to/local/repo" --output ./my-results
    python run.py --source "https://github.com/dotnet-architecture/eShopOnWeb" --output ./results
    python run.py --source "https://github.com/org/repo" --output ./results --skip-graphify
    python run.py --source "C:/already/cloned" --output ./results --skip-clone

Pipeline sequence:
    Step  1  — Graphify Extract
    Step  2  — Layer 1 (source code + DB + config extraction)
    Step  3  — Layer 2 BA Agent 1 (Structural Scout)
    Step  4  — Layer 3 BA Agent 2 (Deep Analyst)
    Steps 5-6 — DA Agent 1 → DA Agent 2         (sequential, run after step 4)
    Steps 7-8 — TA Agent 1 → TA Agent 2         (sequential, run after step 4)
    Step  9  — AA Pipeline                       (run after step 4)
    Steps 5-9 run concurrently using threads; 5+6 are internally sequential,
    7+8 are internally sequential, 9 is standalone.
    Step 10  — Foundation (Knowledge Graph Synthesis, runs after all above)
"""

# ── Standard library ──────────────────────────────────────────────────────────
import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Path constants ─────────────────────────────────────────────────────────────
# run.py lives at graphify-pipeline/run.py
# pipeline/ lives at graphify-pipeline/pipeline/
SCRIPT_DIR   = Path(__file__).parent.resolve()
PIPELINE_DIR = SCRIPT_DIR / "pipeline"

# ── ANSI colour helpers (degraded gracefully on Windows when not supported) ───
_USE_COLOR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def red(t):    return _c("31", t)
def bold(t):   return _c("1",  t)
def cyan(t):   return _c("36", t)
def dim(t):    return _c("2",  t)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Subprocess helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _run(cmd: list, *, label: str, cwd: str = None, timeout: int = 1800) -> dict:
    """
    Run a subprocess synchronously.  Returns a result dict with keys:
        label, cmd_str, returncode, stdout, stderr, duration_s
    Never raises — errors are captured in the dict.
    """
    cmd_str = " ".join(str(c) for c in cmd)
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "label":      label,
            "cmd_str":    cmd_str,
            "returncode": proc.returncode,
            "stdout":     proc.stdout or "",
            "stderr":     proc.stderr or "",
            "duration_s": time.monotonic() - t0,
        }
    except subprocess.TimeoutExpired:
        return {
            "label":      label,
            "cmd_str":    cmd_str,
            "returncode": -1,
            "stdout":     "",
            "stderr":     f"Timed out after {timeout}s",
            "duration_s": time.monotonic() - t0,
        }
    except Exception as exc:
        return {
            "label":      label,
            "cmd_str":    cmd_str,
            "returncode": -1,
            "stdout":     "",
            "stderr":     str(exc),
            "duration_s": time.monotonic() - t0,
        }


def _print_step_result(result: dict) -> None:
    """Print a formatted block for a completed step."""
    ok  = result["returncode"] == 0
    dur = f"{result['duration_s']:.1f}s"
    sep = "=" * 64
    status_str = green("COMPLETE") if ok else red("FAILED")
    print(f"\n{sep}")
    print(f"{bold(result['label'])} — {status_str}  {dim('(' + dur + ')')}")
    print(sep)
    if result["stdout"].strip():
        # Indent stdout for readability
        for line in result["stdout"].rstrip().splitlines():
            print(f"  {line}")
    if not ok and result["stderr"].strip():
        print(f"\n  {red('[stderr]')} {result['stderr'][:800].strip()}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Step banner printer
# ═══════════════════════════════════════════════════════════════════════════════

_TOTAL_STEPS = 10

def _banner(step: int, label: str) -> None:
    """Print a prominent step header."""
    print(f"\n{'─' * 64}")
    print(bold(cyan(f"[STEP {step}/{_TOTAL_STEPS}]  {label}")))
    print(f"{'─' * 64}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — graphify CLI helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _graphify_cmd() -> list:
    """Return the base graphify CLI command, handling Windows .cmd wrappers."""
    if sys.platform == "win32":
        return ["cmd", "/c", "graphify"]
    found = shutil.which("graphify")
    if not found:
        raise RuntimeError(
            "graphify CLI not found on PATH.  "
            "Install it with:  pip install graphify-cli"
        )
    return [found]


def _is_github_url(source: str) -> bool:
    """Return True if source looks like a remote git URL."""
    s = source.lower()
    return s.startswith("http://") or s.startswith("https://") or s.startswith("git@")


def clone_repo(url: str, output_dir: Path) -> str:
    """
    Clone a remote repository under output_dir/repo-clone/.
    Returns the local path to the cloned repo.
    Raises RuntimeError on failure.
    """
    clone_root = output_dir / "repo-clone"
    clone_root.mkdir(parents=True, exist_ok=True)

    # Use graphify clone if available, fall back to plain git clone
    graphify = shutil.which("graphify") or ("cmd /c graphify" if sys.platform == "win32" else None)

    print(f"  Cloning {url}")
    print(f"  Into    {clone_root}")

    # Try graphify clone first
    result = _run(
        _graphify_cmd() + ["clone", url, "--out", str(clone_root)],
        label="graphify clone",
        timeout=600,
    )

    if result["returncode"] == 0:
        # graphify clone typically puts the repo in a sub-folder; find it
        subdirs = [d for d in clone_root.iterdir() if d.is_dir()]
        if subdirs:
            local_path = str(subdirs[0])
            print(f"  Cloned to: {local_path}")
            return local_path
        return str(clone_root)

    # Fall back to git clone
    print(f"  {yellow('graphify clone failed, trying git clone...')}")
    result2 = _run(
        ["git", "clone", "--depth", "1", url, str(clone_root / "repo")],
        label="git clone",
        timeout=600,
    )
    if result2["returncode"] != 0:
        raise RuntimeError(
            f"Could not clone repository.\n"
            f"graphify clone stderr: {result['stderr'][:400]}\n"
            f"git clone stderr:      {result2['stderr'][:400]}"
        )
    return str(clone_root / "repo")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Individual step runners
# ═══════════════════════════════════════════════════════════════════════════════

def step_graphify_extract(source: str, graphify_out: Path) -> dict:
    """Step 1 — graphify extract."""
    graphify_out.mkdir(parents=True, exist_ok=True)
    cmd = _graphify_cmd() + [
        "extract", source,
        "--out", str(graphify_out),
        "--backend", "claude-cli",
    ]
    return _run(cmd, label="[STEP 1/10] Graphify Extract", timeout=1800)


def step_layer1(source: str, pipeline_out: Path) -> dict:
    """Step 2 — Layer 1 extraction via run_pipeline.py."""
    pipeline_out.mkdir(parents=True, exist_ok=True)
    runner = PIPELINE_DIR / "run_pipeline.py"
    cmd = [
        sys.executable, str(runner),
        "--source", source,
        "--output", str(pipeline_out),
    ]
    return _run(cmd, label="[STEP 2/10] Layer 1 — Source Extraction", cwd=str(PIPELINE_DIR))


def step_layer2(pipeline_out: Path) -> dict:
    """Step 3 — BA Agent 1 (Layer 2 Structural Scout)."""
    runner = PIPELINE_DIR / "layer2" / "layer2_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
    ]
    return _run(cmd, label="[STEP 3/10] Layer 2 — BA Agent 1 (Structural Scout)", cwd=str(PIPELINE_DIR))


def step_layer3(pipeline_out: Path) -> dict:
    """Step 4 — BA Agent 2 (Layer 3 Deep Analyst)."""
    runner = PIPELINE_DIR / "layer3" / "layer3_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
    ]
    return _run(cmd, label="[STEP 4/10] Layer 3 — BA Agent 2 (Deep Analyst)", cwd=str(PIPELINE_DIR))


def step_da_agent1(pipeline_out: Path) -> dict:
    """Step 5 — DA Agent 1."""
    runner = PIPELINE_DIR / "data-architecture" / "da_agent1_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
    ]
    return _run(cmd, label="[STEP 5/10] DA Agent 1 — Data Architecture", cwd=str(PIPELINE_DIR))


def step_da_agent2(pipeline_out: Path) -> dict:
    """Step 6 — DA Agent 2."""
    runner = PIPELINE_DIR / "data-architecture" / "da_agent2_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
    ]
    return _run(cmd, label="[STEP 6/10] DA Agent 2 — DA Review", cwd=str(PIPELINE_DIR))


def step_ta_agent1(pipeline_out: Path, repo_root: str) -> dict:
    """Step 7 — TA Agent 1 (Stack Scout)."""
    runner = PIPELINE_DIR / "technology-architecture" / "ta_agent1_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
        "--repo-root", repo_root,
    ]
    return _run(cmd, label="[STEP 7/10] TA Agent 1 — Stack Scout", cwd=str(PIPELINE_DIR))


def step_ta_agent2(pipeline_out: Path, repo_root: str) -> dict:
    """Step 8 — TA Agent 2 (Deep Analyst)."""
    runner = PIPELINE_DIR / "technology-architecture" / "ta_agent2_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
        "--repo-root", repo_root,
    ]
    return _run(cmd, label="[STEP 8/10] TA Agent 2 — Deep Analyst", cwd=str(PIPELINE_DIR))


def step_aa_pipeline(pipeline_out: Path, repo_root: str) -> dict:
    """Step 9 — Application Architecture pipeline."""
    runner = PIPELINE_DIR / "application-architecture" / "aa_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
        "--repo-root", repo_root,
    ]
    return _run(cmd, label="[STEP 9/10] AA Pipeline — Application Architecture", cwd=str(PIPELINE_DIR))


def step_foundation(pipeline_out: Path) -> dict:
    """Step 10 — Foundation / Knowledge Graph Synthesis."""
    runner = PIPELINE_DIR / "foundation_runner.py"
    cmd = [
        sys.executable, str(runner),
        "--input", str(pipeline_out),
        "--run",
    ]
    return _run(cmd, label="[STEP 10/10] Foundation — Knowledge Graph Synthesis", cwd=str(PIPELINE_DIR))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Parallel track runner (DA + TA + AA after step 4)
# ═══════════════════════════════════════════════════════════════════════════════

def _run_da_track(pipeline_out: Path, results: list, lock: threading.Lock) -> None:
    """Run DA Agent 1 then DA Agent 2 sequentially (one thread)."""
    r1 = step_da_agent1(pipeline_out)
    with lock:
        results.append(r1)
        _print_step_result(r1)

    # Run Agent 2 even if Agent 1 failed — it will skip gracefully
    r2 = step_da_agent2(pipeline_out)
    with lock:
        results.append(r2)
        _print_step_result(r2)


def _run_ta_track(pipeline_out: Path, repo_root: str, results: list, lock: threading.Lock) -> None:
    """Run TA Agent 1 then TA Agent 2 sequentially (one thread)."""
    r1 = step_ta_agent1(pipeline_out, repo_root)
    with lock:
        results.append(r1)
        _print_step_result(r1)

    r2 = step_ta_agent2(pipeline_out, repo_root)
    with lock:
        results.append(r2)
        _print_step_result(r2)


def _run_aa_track(pipeline_out: Path, repo_root: str, results: list, lock: threading.Lock) -> None:
    """Run AA Pipeline (one thread)."""
    r = step_aa_pipeline(pipeline_out, repo_root)
    with lock:
        results.append(r)
        _print_step_result(r)


def run_parallel_tracks(pipeline_out: Path, repo_root: str) -> list:
    """
    Run DA, TA, and AA tracks concurrently.
    DA Agent 1 → DA Agent 2 are sequential within the DA thread.
    TA Agent 1 → TA Agent 2 are sequential within the TA thread.
    All three tracks start at the same time.
    Returns list of all result dicts.
    """
    results: list = []
    lock = threading.Lock()

    print(f"\n{bold(yellow('Starting parallel tracks: DA + TA + AA'))}")
    print(dim("  DA: steps 5+6 sequential in thread 1"))
    print(dim("  TA: steps 7+8 sequential in thread 2"))
    print(dim("  AA: step  9   in thread 3"))
    print()

    threads = [
        threading.Thread(target=_run_da_track, args=(pipeline_out, results, lock), daemon=True),
        threading.Thread(target=_run_ta_track, args=(pipeline_out, repo_root, results, lock), daemon=True),
        threading.Thread(target=_run_aa_track, args=(pipeline_out, repo_root, results, lock), daemon=True),
    ]

    t_start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    elapsed = time.monotonic() - t_start
    print(f"\n{dim(f'All parallel tracks finished in {elapsed:.1f}s')}")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Output summary
# ═══════════════════════════════════════════════════════════════════════════════

def _count_files(path: Path) -> int:
    """Count files recursively under path, or 0 if it does not exist."""
    if not path.exists():
        return 0
    return sum(1 for _ in path.rglob("*") if _.is_file())


def print_final_summary(
    output_dir:   Path,
    graphify_out: Path,
    pipeline_out: Path,
    all_results:  list,
    total_time_s: float,
) -> None:
    """Print the final run summary with step statuses, file counts, and timings."""
    sep = "═" * 64
    print(f"\n{sep}")
    print(bold(green("GRAPHIFY PIPELINE — FINAL SUMMARY")))
    print(sep)

    # Per-step status table
    ok_steps   = [r for r in all_results if r["returncode"] == 0]
    fail_steps = [r for r in all_results if r["returncode"] != 0]

    print(f"\n{bold('Step results:')}")
    for r in all_results:
        icon    = green("OK  ") if r["returncode"] == 0 else red("FAIL")
        dur_str = dim(f"({r['duration_s']:.1f}s)")
        print(f"  {icon}  {r['label']}  {dur_str}")

    # Output folder summary
    print(f"\n{bold('Output folders:')}")
    folders = {
        "Graphify graph":       graphify_out,
        "Layer 1 artifacts":    pipeline_out,
        "BA documents":         pipeline_out / "ba_documents",
        "DA outputs":           pipeline_out / "da-outputs",
        "TA outputs":           pipeline_out / "ta-outputs",
        "AA outputs":           pipeline_out / "aa-outputs",
        "Foundation graph":     pipeline_out / "foundation",
    }
    for label, folder in folders.items():
        exists = folder.exists()
        count  = _count_files(folder) if exists else 0
        status = green(f"{count:>4} files") if exists and count > 0 else dim("  —  not created")
        print(f"  {status}  {label:<22}  {dim(str(folder))}")

    # Totals
    print(f"\n{bold('Totals:')}")
    print(f"  Steps completed : {green(str(len(ok_steps)))} / {len(all_results)}")
    if fail_steps:
        print(f"  Steps failed    : {red(str(len(fail_steps)))}")
        for r in fail_steps:
            print(f"    - {r['label']}")
            if r["stderr"].strip():
                print(f"      {dim(r['stderr'][:200].strip())}")
    print(f"  Total wall time : {bold(f'{total_time_s:.1f}s')}  "
          f"{dim('(' + str(int(total_time_s // 60)) + 'm ' + str(int(total_time_s % 60)) + 's)')}")

    print(f"\n{bold('Root output dir:')}  {output_dir}")
    print(sep + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Main orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

def orchestrate(
    source:         str,
    output_dir:     Path,
    skip_graphify:  bool,
    skip_clone:     bool,
) -> int:
    """
    Run the full pipeline.  Returns an exit code (0 = all OK, 1 = one or more failures).
    """
    all_results:   list  = []
    t_pipeline_start = time.monotonic()

    # ── Resolve output paths ──────────────────────────────────────────────────
    output_dir   = output_dir.resolve()
    graphify_out = output_dir / "graphify-out"
    pipeline_out = output_dir / "pipeline-out"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'═' * 64}")
    print(bold(cyan("GRAPHIFY PIPELINE — MASTER ORCHESTRATOR")))
    print(f"{'═' * 64}")
    print(f"  Source       : {source}")
    print(f"  Output root  : {output_dir}")
    print(f"  Skip graphify: {skip_graphify}")
    print(f"  Skip clone   : {skip_clone}")
    print(f"  Pipeline dir : {PIPELINE_DIR}")
    print(f"{'═' * 64}\n")

    # ── Determine local repo path ─────────────────────────────────────────────
    local_repo_path: str = source  # default: source is already local

    if _is_github_url(source):
        if skip_clone:
            print(yellow("  --skip-clone set, but source is a URL — skipping clone."))
            print(yellow("  downstream TA/AA steps that need --repo-root will be skipped.\n"))
            local_repo_path = ""
        else:
            print(bold("Cloning remote repository..."))
            try:
                local_repo_path = clone_repo(source, output_dir)
                print(green(f"  Local repo: {local_repo_path}\n"))
            except RuntimeError as exc:
                print(red(f"  Clone failed: {exc}"))
                print(yellow("  Continuing without local repo — TA/AA steps will be skipped.\n"))
                local_repo_path = ""

    # ── STEP 1: Graphify extract ──────────────────────────────────────────────
    if skip_graphify:
        print(yellow(f"[STEP 1/{_TOTAL_STEPS}] Graphify Extract — SKIPPED (--skip-graphify)\n"))
        all_results.append({
            "label":      f"[STEP 1/{_TOTAL_STEPS}] Graphify Extract",
            "cmd_str":    "skipped",
            "returncode": 0,
            "stdout":     "Skipped by --skip-graphify",
            "stderr":     "",
            "duration_s": 0.0,
        })
    else:
        _banner(1, "Graphify Extract")
        r = step_graphify_extract(source, graphify_out)
        all_results.append(r)
        _print_step_result(r)

    # ── STEP 2: Layer 1 ───────────────────────────────────────────────────────
    _banner(2, "Layer 1 — Source Extraction")
    r2 = step_layer1(source, pipeline_out)
    all_results.append(r2)
    _print_step_result(r2)

    if r2["returncode"] != 0:
        print(red("  Layer 1 failed — cannot continue with downstream agents."))
        print_final_summary(output_dir, graphify_out, pipeline_out, all_results,
                            time.monotonic() - t_pipeline_start)
        return 1

    # ── STEP 3: Layer 2 (BA Agent 1) ─────────────────────────────────────────
    _banner(3, "Layer 2 — BA Agent 1 (Structural Scout)")
    r3 = step_layer2(pipeline_out)
    all_results.append(r3)
    _print_step_result(r3)

    # ── STEP 4: Layer 3 (BA Agent 2) ─────────────────────────────────────────
    _banner(4, "Layer 3 — BA Agent 2 (Deep Analyst)")
    r4 = step_layer3(pipeline_out)
    all_results.append(r4)
    _print_step_result(r4)

    # ── STEPS 5-9: Parallel tracks (DA + TA + AA) ────────────────────────────
    #
    # DA Agent 1 → DA Agent 2  (sequential within the DA thread)
    # TA Agent 1 → TA Agent 2  (sequential within the TA thread, needs repo)
    # AA Pipeline              (standalone thread, needs repo)
    #
    # TA and AA are skipped if local_repo_path is not available.
    print(f"\n{'─' * 64}")
    print(bold(cyan(f"[STEPS 5-9/{_TOTAL_STEPS}]  Parallel Tracks")))
    print(f"{'─' * 64}")

    if local_repo_path:
        parallel_results = run_parallel_tracks(pipeline_out, local_repo_path)
    else:
        print(yellow("  No local repo path — running DA track only (TA + AA require repo)."))
        parallel_results = []
        da_lock = threading.Lock()
        _run_da_track(pipeline_out, parallel_results, da_lock)
        # Add skipped placeholders for TA and AA
        for label in [
            f"[STEP 7/{_TOTAL_STEPS}] TA Agent 1 — Stack Scout",
            f"[STEP 8/{_TOTAL_STEPS}] TA Agent 2 — Deep Analyst",
            f"[STEP 9/{_TOTAL_STEPS}] AA Pipeline — Application Architecture",
        ]:
            parallel_results.append({
                "label":      label,
                "cmd_str":    "skipped (no local repo)",
                "returncode": 0,
                "stdout":     "Skipped — no local repo path available",
                "stderr":     "",
                "duration_s": 0.0,
            })

    all_results.extend(parallel_results)

    # ── STEP 10: Foundation ───────────────────────────────────────────────────
    _banner(10, "Foundation — Knowledge Graph Synthesis")
    r10 = step_foundation(pipeline_out)
    all_results.append(r10)
    _print_step_result(r10)

    # ── Final summary ─────────────────────────────────────────────────────────
    total_time = time.monotonic() - t_pipeline_start
    print_final_summary(output_dir, graphify_out, pipeline_out, all_results, total_time)

    # Exit code: 0 if all non-skipped steps passed, else 1
    failed = [r for r in all_results if r["returncode"] != 0 and r["cmd_str"] != "skipped"]
    return 0 if not failed else 1


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Argument parsing and entry point
# ═══════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description=(
            "Graphify Pipeline — run the full reverse-engineering pipeline "
            "from a GitHub URL or local folder to a complete Enterprise Knowledge Graph."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --source "https://github.com/dotnet-architecture/eShopOnWeb" --output ./results
  python run.py --source "C:/projects/my-app" --output ./results
  python run.py --source "https://github.com/org/repo" --output ./results --skip-graphify
  python run.py --source "C:/projects/my-app" --output ./results --skip-clone

Pipeline output structure:
  <output>/graphify-out/        — Graphify knowledge graph (step 1)
  <output>/pipeline-out/        — Layer 1 artifacts (step 2)
  <output>/pipeline-out/ba_documents/   — BA Agent outputs (steps 3-4)
  <output>/pipeline-out/da-outputs/     — DA Agent outputs (steps 5-6)
  <output>/pipeline-out/ta-outputs/     — TA Agent outputs (steps 7-8)
  <output>/pipeline-out/aa-outputs/     — AA Agent outputs (step  9)
  <output>/pipeline-out/foundation/     — Knowledge Graph  (step 10)
""",
    )

    parser.add_argument(
        "--source",
        required=True,
        metavar="SOURCE",
        help=(
            "GitHub/GitLab URL (e.g. https://github.com/org/repo) "
            "or local folder path (e.g. C:/projects/my-app)"
        ),
    )
    parser.add_argument(
        "--output",
        default="./graphify-output",
        metavar="DIR",
        help="Root output directory (default: ./graphify-output)",
    )
    parser.add_argument(
        "--skip-graphify",
        action="store_true",
        default=False,
        help="Skip step 1 (graphify extract) — useful if you already ran it",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        default=False,
        help=(
            "Skip cloning even if source is a URL — use when the repo is "
            "already available locally and you pass the URL only for metadata"
        ),
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    exit_code = orchestrate(
        source        = args.source,
        output_dir    = Path(args.output),
        skip_graphify = args.skip_graphify,
        skip_clone    = args.skip_clone,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
