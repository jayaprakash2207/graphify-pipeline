#!/usr/bin/env python3
"""
Optional safe runtime/test evidence collection.

This script intentionally runs tests in no-build/no-restore mode and writes
results under architecture-output/test-runtime/. It captures execution evidence
without modifying legacy source files. A failing test command is evidence, not a
pipeline failure.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unknown"


def find_dotnet_executable(output_root: Path) -> str | None:
    existing = shutil.which("dotnet")
    if existing:
        return existing
    candidates = [
        Path.home() / ".dotnet8" / "dotnet.exe",
        Path.home() / ".dotnet" / "dotnet.exe",
        output_root / "dotnet" / "dotnet.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def run_test_project(repo_root: Path, output_root: Path, project: dict[str, Any], dotnet_path: str) -> dict[str, Any]:
    project_path = repo_root / project["path"]
    result_dir = output_root / "test-runtime" / safe_name(project.get("name", project_path.stem))
    result_dir.mkdir(parents=True, exist_ok=True)
    command = [
        dotnet_path,
        "test",
        str(project_path),
        "--no-build",
        "--no-restore",
        "--logger",
        "trx;LogFileName=test-results.trx",
        "--results-directory",
        str(result_dir),
    ]
    started = utc_now()
    result = subprocess.run(
        command,
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    completed = utc_now()
    trx_files = sorted(path.relative_to(output_root).as_posix() for path in result_dir.glob("*.trx"))
    return {
        "project": project.get("name"),
        "project_path": project.get("path"),
        "command": command,
        "started_at": started,
        "completed_at": completed,
        "returncode": result.returncode,
        "status": "passed_or_completed" if result.returncode == 0 else "failed_or_not_available",
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
        "trx_files": trx_files,
        "evidence_note": "Executed with --no-build --no-restore to avoid generated build/restore side effects in legacy source.",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Collect optional no-build/no-restore runtime test evidence.")
    parser.add_argument("--repo-root", default=".", help="Legacy repository root.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    project_inventory = load_json(output_root / "inventory" / "project-inventory.json")
    test_projects = project_inventory.get("test_projects", [])

    dotnet_path = find_dotnet_executable(output_root)
    if not dotnet_path:
        projects = [
            {
                "project": project.get("name"),
                "project_path": project.get("path"),
                "command": ["dotnet", "test", project.get("path", ""), "--no-build", "--no-restore"],
                "returncode": None,
                "status": "runtime_tool_not_available",
                "stdout_tail": "",
                "stderr_tail": "dotnet executable was not found on PATH for optional runtime evidence collection.",
                "trx_files": [],
                "evidence_note": "Runtime test execution was attempted but the .NET SDK/CLI was not available to the analyzer process.",
            }
            for project in test_projects
        ]
    else:
        projects = [run_test_project(repo_root, output_root, project, dotnet_path) for project in test_projects]
    summary = {
        "test_project_count": len(test_projects),
        "executed_project_count": len(projects) if dotnet_path else 0,
        "completed_successfully": sum(1 for project in projects if project["returncode"] == 0),
        "failed_or_not_available": sum(1 for project in projects if project["returncode"] != 0),
        "runtime_tool_available": bool(dotnet_path),
    }
    payload = {
        "generated_at": utc_now(),
        "execution_mode": "dotnet_test_no_build_no_restore",
        "source_inventory": "architecture-output/inventory/project-inventory.json",
        "summary": summary,
        "projects": projects,
        "limitations": [
            "No-build/no-restore mode may fail if test assemblies have not already been built.",
            "A failed command is captured as runtime-environment evidence and does not prove application behavior is broken.",
        ],
    }
    write_json(output_root / "test-runtime" / "dotnet-test-execution.json", payload)
    print(json.dumps({"output": str(output_root / "test-runtime" / "dotnet-test-execution.json"), "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
