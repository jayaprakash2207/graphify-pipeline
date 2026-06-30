"""BA Pipeline — orchestrates Layer 1 extraction and all downstream agents."""

import argparse
import shutil
import subprocess
import sys

# Force UTF-8 output on Windows so unicode chars in paths/names don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from layer1.pipeline import Layer1Pipeline


# ── Full-run orchestration ─────────────────────────────────────────────────────

def _run_subprocess(label: str, cmd: list, results: list) -> None:
    """Run a subprocess, capture its output, and append a result dict to results."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        results.append({
            "label":      label,
            "stdout":     proc.stdout,
            "stderr":     proc.stderr,
            "returncode": proc.returncode,
        })
    except (OSError, ValueError) as exc:
        results.append({
            "label":      label,
            "stdout":     "",
            "stderr":     str(exc),
            "returncode": -1,
        })


def _flush_results(results: list) -> None:
    """Print buffered output from a completed subprocess."""
    for r in results:
        ok = r["returncode"] == 0
        print("\n" + "=" * 60)
        print(f"{r['label']} — {'COMPLETE' if ok else 'FAILED (see below)'}")
        print("=" * 60)
        if r["stdout"]:
            print(r["stdout"].rstrip())
        if not ok and r["stderr"]:
            print(f"[stderr] {r['stderr'][:500]}")


def _run_step(label: str, cmd: list) -> dict:
    """Run a single pipeline step synchronously, print its output, return the result dict."""
    results = []
    _run_subprocess(label, cmd, results)
    _flush_results(results)
    return results[0] if results else {}


def _run_step_or_exit(label: str, cmd: list) -> dict:
    """Run a step; if it fails, print the reason and stop the whole pipeline immediately."""
    result = _run_step(label, cmd)
    if result.get("returncode") != 0:
        reason = (result.get("stderr") or result.get("stdout") or "no output captured").strip()
        print("\n" + "=" * 60)
        print("PIPELINE STOPPED — a step failed")
        print("=" * 60)
        print(f"  Step       : {label}")
        print(f"  Command    : {' '.join(str(c) for c in cmd)}")
        print(f"  Exit code  : {result.get('returncode')}")
        print(f"  Reason     : {reason[:1000]}")
        print("=" * 60 + "\n")
        sys.exit(1)
    return result


def run_full_pipeline(input_dir: str, repo_root: str = None) -> None:
    """
    Orchestrate all layers after Layer 1 completes — fully sequential.

    Each agent runs to completion before the next one starts, so concurrent
    claude CLI calls never contend for tokens:

        BA track : Layer 2  → Layer 3       (BA documents)
        DA track : DA Agnt1 → DA Agnt2      (data architecture)
        TA track : TA Agnt1 → TA Agnt2      (technology architecture)
        AA track : AA Pipeline              (Python analyzer → claude stages 04→07)

    Order: BA agents, then DA agents, then the TA agents, then the AA pipeline
    last. The TA and AA tracks both require the extracted repo source
    (repo_root) and are skipped if it is unavailable. The AA pipeline first
    runs its deterministic Python analyzer, then its own sequential claude
    stage chain — so it stays consistent with the one-agent-at-a-time design.
    """
    py = sys.executable

    print("\n" + "=" * 60)
    print("FULL RUN — SEQUENTIAL (one agent at a time)")
    print("=" * 60 + "\n")

    # ── BA track : Layer 2 → Layer 3 ──────────────────────────────────────────
    _run_step_or_exit("Layer 2 (BA Analysis)",
                       [py, "layer2/layer2_runner.py", "--input", input_dir, "--run"])
    _run_step_or_exit("Layer 3 (BA Documents)",
                       [py, "layer3/layer3_runner.py", "--input", input_dir, "--run"])

    # ── DA track : DA Agent 1 → DA Agent 2 ────────────────────────────────────
    _run_step_or_exit("DA Agent 1 (Data Architecture)",
                       [py, "data-architecture/da_agent1_runner.py", "--input", input_dir, "--run"])
    _run_step_or_exit("DA Agent 2 (DA Review)",
                       [py, "data-architecture/da_agent2_runner.py", "--input", input_dir, "--run"])

    # ── TA track : TA Agent 1 → TA Agent 2 (requires repo source) ─────────────
    if repo_root:
        _run_step_or_exit("TA Agent 1 (Stack Scout)",
                           [py, "technology-architecture/ta_agent1_runner.py",
                            "--input", input_dir, "--run", "--repo-root", repo_root])
        _run_step_or_exit("TA Agent 2 (Deep Analyst)",
                           [py, "technology-architecture/ta_agent2_runner.py",
                            "--input", input_dir, "--run", "--repo-root", repo_root])

    # ── AA track : pure Python, runs last (no token cost) ─────────────────────
    if repo_root:
        _run_step_or_exit("AA Pipeline (Application Architecture)",
                           [py, "application-architecture/aa_runner.py",
                            "--input", input_dir, "--run", "--repo-root", repo_root])

    # ── Foundation : synthesize all 4 layers → Enterprise Knowledge Graph ──────
    _run_step_or_exit("Foundation (Knowledge Graph Synthesis)",
                       [py, "foundation_runner.py", "--input", input_dir, "--run"])

    print("\n" + "=" * 60)
    print("FULL PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  BA documents  : {input_dir}/ba_documents/")
    print(f"  DA outputs    : {input_dir}/da-outputs/")
    if repo_root:
        print(f"  TA outputs    : {input_dir}/ta-outputs/")
        print(f"  AA outputs    : {input_dir}/aa-outputs/")
    print(f"  Knowledge Graph: {input_dir}/foundation/")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    """Parse arguments, run Layer 1, and optionally orchestrate all downstream layers."""
    parser = argparse.ArgumentParser(
        description="BA Pipeline — Extract Business & Data Architecture from Legacy Applications"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="GitHub/GitLab/Bitbucket URL, local folder path, or .zip file path",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory for extracted artifacts (default: output)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Git token for private repositories",
    )
    parser.add_argument(
        "--app-url",
        default=None,
        help="Running application URL for UI extraction (optional)",
    )
    parser.add_argument(
        "--full-run",
        action="store_true",
        help=(
            "Run all layers automatically after Layer 1, fully sequentially: "
            "Layer 2, Layer 3, DA Agent 1, DA Agent 2, TA Agent 1, TA Agent 2, "
            "then the AA Pipeline"
        ),
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("BA PIPELINE — LAYER 1: EXTRACTION")
    print("=" * 60)
    print(f"Source   : {args.source}")
    print(f"Output   : {args.output}")
    print(f"Full run : {'yes' if args.full_run else 'no (Layer 1 only)'}")
    print("=" * 60 + "\n")

    pipeline = Layer1Pipeline(
        source=args.source,
        output_dir=args.output,
        git_token=args.token,
        app_url=args.app_url,
    )

    # keep_source=True preserves the extracted temp dir so AA can read it
    result = pipeline.run(keep_source=args.full_run)

    if result["success"]:
        s = result["summary"]
        print("\n" + "=" * 60)
        print("LAYER 1 COMPLETE")
        print("=" * 60)
        print(f"  Language detected  : {s.get('language', 'unknown')}")
        print(f"  Methods extracted  : {s.get('total_methods', 0)}")
        print(f"  Classes extracted  : {s.get('total_classes', 0)}")
        print(f"  Interfaces found   : {s.get('total_interfaces', 0)}")
        print(f"  Enums found        : {s.get('total_enums', 0)}")
        print(f"  Business artifacts : {s.get('total_business_artifacts', 0)}")
        print(f"  DB objects found   : {s.get('total_db_objects', 0)}")
        print(f"  Config params      : {s.get('total_config_params', 0)}")
        print(f"  Business params    : {s.get('total_business_params', 0)}")
        print(f"  Log events found   : {s.get('log_events_found', 0)}")
        print(f"  Output saved to    : {result['output_dir']}")
        print("=" * 60 + "\n")

        if args.full_run:
            local_path = result.get("local_path")
            temp_dir   = result.get("temp_dir")
            try:
                run_full_pipeline(args.output, repo_root=local_path)
            finally:
                # Clean up extracted source after all downstream agents finish
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print("Next steps:")
            print(f"  Layer 2 : python layer2/layer2_runner.py --input {args.output}")
            print(f"  DA Agnt1: python data-architecture/da_agent1_runner.py --input {args.output}")
            print(f"  TA Agnt1: python technology-architecture/ta_agent1_runner.py --repo-root <source> --input {args.output}")
            print(f"  AA      : python application-architecture/aa_runner.py --repo-root <source> --input {args.output}")
            print("  (or re-run with --full-run to automate all layers)\n")
    else:
        print(f"\nERROR: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
