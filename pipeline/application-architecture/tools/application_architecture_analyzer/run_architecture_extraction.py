#!/usr/bin/env python3
"""
Run the full Application Architecture extraction pipeline.

The pipeline keeps prompt/instruction material as the governance layer, while
the scripts do the repeatable work:

1. inventory
2. source chunks
3. parsed facts
4. optional semantic facts
5. evidence packs
6. final architecture artifacts
7. enterprise forward-engineering artifacts
8. enterprise application architecture blueprint
9. review artifacts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASES = [
    {
        "id": "inventory",
        "script": "scan_inventory.py",
        "outputs": [
            "inventory/file-inventory.json",
            "inventory/project-inventory.json",
            "inventory/language-summary.json",
            "inventory/ignored-files-report.json",
        ],
    },
    {
        "id": "source-chunks",
        "script": "generate_source_chunks.py",
        "outputs": [
            "parsed/source-chunk-index.json",
        ],
    },
    {
        "id": "parsed",
        "script": "extract_parsed_facts.py",
        "outputs": [
            "parsed/symbol-registry.json",
            "parsed/route-registry.json",
            "parsed/dependency-candidates.json",
            "parsed/entry-point-candidates.json",
        ],
    },
    {
        "id": "semantic",
        "script": "extract_roslyn_semantic_facts.py",
        "outputs": [
            "parsed/roslyn-semantic-facts.json",
        ],
    },
    {
        "id": "evidence",
        "script": "generate_evidence_packs.py",
        "outputs": [
            "evidence-packs/system-inventory-pack.json",
            "evidence-packs/module-boundary-pack.json",
            "evidence-packs/component-registry-pack.json",
            "evidence-packs/dependency-pack.json",
            "evidence-packs/entry-point-pack.json",
            "evidence-packs/call-flow-pack.json",
            "evidence-packs/layering-pattern-pack.json",
            "evidence-packs/external-boundary-pack.json",
            "evidence-packs/frontend-application-pack.json",
        ],
    },
    {
        "id": "final",
        "script": "generate_final_architecture.py",
        "outputs": [
            "final/application-architecture-summary.md",
            "final/system-inventory.json",
            "final/module-boundary-map.json",
            "final/component-registry.json",
            "final/dependency-graph.json",
            "final/application-interface-catalogue.json",
            "final/call-flow-map.json",
            "final/architecture-pattern-report.md",
            "final/architecture-violation-register.json",
            "final/application-risk-register.json",
            "final/strangler-candidate-report.md",
            "final/forward-engineering-input-map.md",
            "final/open-questions.md",
            "final/diagrams/system-context.mmd",
            "final/diagrams/container-view.mmd",
            "final/diagrams/component-view.mmd",
            "final/diagrams/dependency-view.mmd",
            "final/diagrams/call-flow-view.mmd",
        ],
    },
    {
        "id": "runtime-evidence",
        "script": "run_runtime_evidence.py",
        "optional": True,
        "outputs": [
            "test-runtime/dotnet-test-execution.json",
        ],
    },
    {
        "id": "enterprise-forward",
        "script": "generate_enterprise_forward_engineering.py",
        "outputs": [
            "final/business-capability-map.json",
            "final/business-capability-map.md",
            "final/module-consolidation-map.json",
            "final/module-consolidation-map.md",
            "final/service-boundary-options.md",
            "final/migration-wave-plan.md",
            "final/preserve-redesign-retire-map.md",
            "final/api-contract-preservation-map.json",
            "final/data-ownership-map.md",
            "final/test-runtime-evidence-map.json",
            "final/test-runtime-evidence-map.md",
            "final/confidence-report.md",
            "final/architecture-decision-inputs.md",
            "final/forward-engineering-backlog.md",
        ],
    },
    {
        "id": "application-blueprint",
        "script": "generate_enterprise_application_architecture_blueprint.py",
        "outputs": [
            "final/enterprise-application-architecture-blueprint.md",
            "final/enterprise-application-architecture-blueprint.json",
        ],
    },
    {
        "id": "review",
        "script": "generate_review_artifacts.py",
        "outputs": [
            "final/quality-review.md",
            "final/executive-summary-for-review.md",
            "final/final-sanity-check.md",
        ],
    },
]

REQUIRED_KEYS = {
    "inventory": {
        "inventory/file-inventory.json": ["repo_root", "summary", "files"],
        "inventory/project-inventory.json": ["repo_root", "projects", "deployable_units", "summary"],
        "inventory/language-summary.json": ["languages", "total_files_scanned"],
        "inventory/ignored-files-report.json": ["ignored_files", "total_files_ignored"],
    },
    "parsed": {
        "parsed/source-chunk-index.json": ["chunks", "summary", "chunking_strategy"],
        "parsed/symbol-registry.json": ["components", "summary", "technology_stacks_used_for_parsing"],
        "parsed/route-registry.json": ["routes", "summary"],
        "parsed/dependency-candidates.json": ["dependencies", "summary"],
        "parsed/entry-point-candidates.json": ["entry_points", "summary"],
    },
    "semantic": {
        "parsed/roslyn-semantic-facts.json": ["status", "summary", "semantic_components", "dependency_candidates"],
    },
    "evidence": {
        "evidence-packs/system-inventory-pack.json": ["evidence_pack_type", "source_files_used", "confidence"],
        "evidence-packs/module-boundary-pack.json": ["evidence_pack_type", "module_candidates", "confidence"],
        "evidence-packs/component-registry-pack.json": ["evidence_pack_type", "components", "confidence"],
        "evidence-packs/dependency-pack.json": ["evidence_pack_type", "component_dependencies", "module_dependencies", "cycles"],
        "evidence-packs/entry-point-pack.json": ["evidence_pack_type", "entry_points"],
        "evidence-packs/call-flow-pack.json": ["evidence_pack_type", "flows"],
        "evidence-packs/layering-pattern-pack.json": ["evidence_pack_type", "detected_layers", "candidate_patterns"],
        "evidence-packs/external-boundary-pack.json": ["evidence_pack_type", "external_dependencies"],
        "evidence-packs/frontend-application-pack.json": ["evidence_pack_type", "frontend_apps"],
    },
    "final": {
        "final/system-inventory.json": ["applications", "deployable_units", "open_questions"],
        "final/module-boundary-map.json": ["modules"],
        "final/component-registry.json": ["components"],
        "final/dependency-graph.json": ["nodes", "edges", "cycles"],
        "final/application-interface-catalogue.json": ["interfaces"],
        "final/call-flow-map.json": ["flows"],
        "final/architecture-violation-register.json": ["violations"],
        "final/application-risk-register.json": ["risks"],
    },
    "enterprise-forward": {
        "final/business-capability-map.json": ["capabilities", "summary"],
        "final/module-consolidation-map.json": ["consolidated_modules", "summary"],
        "final/api-contract-preservation-map.json": ["api_contracts", "summary"],
        "final/test-runtime-evidence-map.json": ["capability_test_evidence", "summary", "runtime_execution_status"],
    },
    "application-blueprint": {
        "final/enterprise-application-architecture-blueprint.json": [
            "architecture_blueprint",
            "implementation_model",
            "invocation_model",
            "behavior_model",
            "forward_engineering_contract",
        ],
    },
    "runtime-evidence": {
        "test-runtime/dotnet-test-execution.json": ["summary", "projects", "execution_mode"],
    },
}

PREVIOUS_CONTRACT_BY_PHASE = {
    "source-chunks": "inventory",
    "parsed": "inventory",
    "semantic": "parsed",
    "evidence": "semantic",
    "final": "evidence",
    "enterprise-forward": "final",
    "application-blueprint": "enterprise-forward",
    "runtime-evidence": "final",
    "review": "application-blueprint",
}

SOURCE_GUARD_EXCLUDES = {
    "architecture-output",
    "tools/application_architecture_analyzer",
    ".git",
    "bin",
    "obj",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "logs",
}

OUTPUT_JSON_VALIDATION_EXCLUDES = {
    "dotnet",
    ".dotnet",
    "node_modules",
    "venv",
    ".venv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def should_guard_file(repo_root: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(repo_root).as_posix()
    except ValueError:
        return False
    for excluded in SOURCE_GUARD_EXCLUDES:
        if rel == excluded or rel.startswith(excluded.rstrip("/") + "/"):
            return False
    return path.is_file()


def source_snapshot(repo_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in repo_root.rglob("*"):
        if not should_guard_file(repo_root, path):
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        snapshot[path.relative_to(repo_root).as_posix()] = digest
    return snapshot


def compare_source_snapshots(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    before_keys = set(before)
    after_keys = set(after)
    modified = sorted(path for path in before_keys & after_keys if before[path] != after[path])
    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)
    return {
        "changed": bool(modified or added or removed),
        "modified": modified,
        "added": added,
        "removed": removed,
    }


def validate_contract(output_root: Path, contract_name: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path, keys in REQUIRED_KEYS.get(contract_name, {}).items():
        path = output_root / relative_path
        if not path.exists():
            findings.append({"path": relative_path, "valid": False, "error": "missing file"})
            continue
        if path.stat().st_size == 0:
            findings.append({"path": relative_path, "valid": False, "error": "empty file"})
            continue
        try:
            payload = load_json(path)
        except Exception as exc:  # noqa: BLE001 - report validation failure.
            findings.append({"path": relative_path, "valid": False, "error": f"invalid JSON: {exc}"})
            continue
        missing = [key for key in keys if key not in payload]
        findings.append(
            {
                "path": relative_path,
                "valid": not missing,
                "error": None if not missing else "missing keys: " + ", ".join(missing),
            }
        )
    return findings


def contract_is_valid(findings: list[dict[str, Any]]) -> bool:
    return all(item.get("valid") for item in findings)


def run_phase(script_dir: Path, phase: dict[str, Any], repo_root: Path, output_root: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_dir / phase["script"]),
        "--output-root",
        str(output_root),
    ]
    if phase["id"] in {"inventory", "source-chunks", "parsed", "semantic", "runtime-evidence"}:
        command.extend(["--repo-root", str(repo_root)])

    started = utc_now()
    result = subprocess.run(
        command,
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    completed = utc_now()
    return {
        "phase": phase["id"],
        "script": phase["script"],
        "command": command,
        "started_at": started,
        "completed_at": completed,
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "outputs": validate_outputs(output_root, phase["outputs"]),
    }


def graph_edge_findings(output_root: Path) -> dict[str, Any]:
    path = output_root / "final" / "dependency-graph.json"
    if not path.exists():
        return {"invalid_edge_count": 0, "invalid_edges": []}
    graph = load_json(path)
    node_ids = {node.get("id") for node in graph.get("nodes", [])}
    invalid = [
        {"from": edge.get("from"), "to": edge.get("to")}
        for edge in graph.get("edges", [])
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids
    ]
    return {"invalid_edge_count": len(invalid), "invalid_edges": invalid[:20]}


def quality_counts(output_root: Path) -> dict[str, int]:
    review = output_root / "final" / "quality-review.md"
    if not review.exists():
        return {"pass": 0, "partial": 0, "fail": 0}
    text = review.read_text(encoding="utf-8")
    return {
        "pass": len(__import__("re").findall(r"\|\s*\d+\s*\|[^\r\n]*\|\s*PASS\s*\|", text)),
        "partial": len(__import__("re").findall(r"\|\s*\d+\s*\|[^\r\n]*\|\s*PARTIAL\s*\|", text)),
        "fail": len(__import__("re").findall(r"\|\s*\d+\s*\|[^\r\n]*\|\s*FAIL\s*\|", text)),
    }


def unknown_component_count(output_root: Path) -> int:
    path = output_root / "final" / "component-registry.json"
    if not path.exists():
        return 0
    registry = load_json(path)
    return sum(
        1
        for component in registry.get("components", [])
        if component.get("type") == "Unknown"
        or component.get("layer") == "Unknown"
        or component.get("module") == "Unknown"
    )


def evaluate_quality_gates(output_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    counts = quality_counts(output_root)
    graph = graph_edge_findings(output_root)
    unknown_count = unknown_component_count(output_root)
    thresholds = {
        "max_fail": args.max_fail,
        "max_partial": args.max_partial,
        "max_invalid_graph_edges": args.max_invalid_graph_edges,
        "max_unknown_components": args.max_unknown_components,
    }
    violations = []
    if args.max_fail is not None and counts["fail"] > args.max_fail:
        violations.append(f"quality FAIL count {counts['fail']} exceeds --max-fail {args.max_fail}")
    if args.max_partial is not None and counts["partial"] > args.max_partial:
        violations.append(f"quality PARTIAL count {counts['partial']} exceeds --max-partial {args.max_partial}")
    if args.max_invalid_graph_edges is not None and graph["invalid_edge_count"] > args.max_invalid_graph_edges:
        violations.append(
            f"invalid graph edge count {graph['invalid_edge_count']} exceeds --max-invalid-graph-edges {args.max_invalid_graph_edges}"
        )
    if args.max_unknown_components is not None and unknown_count > args.max_unknown_components:
        violations.append(
            f"unknown component count {unknown_count} exceeds --max-unknown-components {args.max_unknown_components}"
        )
    return {
        "mode": "strict" if args.strict else "warning",
        "thresholds": thresholds,
        "quality_counts": counts,
        "graph": graph,
        "unknown_component_count": unknown_count,
        "violations": violations,
        "passed": not violations or not args.strict,
    }


def validate_outputs(output_root: Path, relative_paths: list[str]) -> list[dict[str, Any]]:
    records = []
    for relative_path in relative_paths:
        path = output_root / relative_path
        records.append(
            {
                "path": relative_path,
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return records


def validate_json_outputs(output_root: Path) -> list[dict[str, Any]]:
    json_paths = sorted(output_root.rglob("*.json"))
    results = []
    for path in json_paths:
        relative_parts = path.relative_to(output_root).parts
        if relative_parts and relative_parts[0] in OUTPUT_JSON_VALIDATION_EXCLUDES:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            results.append({"path": str(path.relative_to(output_root)), "valid": True, "error": None})
        except Exception as exc:  # noqa: BLE001 - report validation errors verbatim.
            results.append({"path": str(path.relative_to(output_root)), "valid": False, "error": str(exc)})
    return results


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    script_dir = Path(__file__).resolve().parent
    start_index = next((idx for idx, phase in enumerate(PHASES) if phase["id"] == args.from_phase), None)
    if start_index is None:
        raise SystemExit(f"Unknown phase {args.from_phase!r}. Valid phases: {', '.join(p['id'] for p in PHASES)}")

    selected_phases = PHASES[start_index:]
    if args.to_phase:
        end_index = next((idx for idx, phase in enumerate(PHASES) if phase["id"] == args.to_phase), None)
        if end_index is None:
            raise SystemExit(f"Unknown phase {args.to_phase!r}. Valid phases: {', '.join(p['id'] for p in PHASES)}")
        selected_phases = PHASES[start_index : end_index + 1]

    output_root.mkdir(parents=True, exist_ok=True)
    source_before = source_snapshot(repo_root) if args.source_guard else {}
    run_records = []
    failed = False
    for phase in selected_phases:
        if phase.get("optional") and phase["id"] == "runtime-evidence" and not args.run_runtime_tests:
            run_records.append(
                {
                    "phase": phase["id"],
                    "script": phase["script"],
                    "optional": True,
                    "skipped": True,
                    "reason": "runtime tests are disabled by default; pass --run-runtime-tests to collect no-build/no-restore evidence",
                }
            )
            continue
        print(f"==> {phase['id']}: {phase['script']}")
        previous_contract = PREVIOUS_CONTRACT_BY_PHASE.get(phase["id"])
        if previous_contract:
            pre_findings = validate_contract(output_root, previous_contract)
            if not contract_is_valid(pre_findings):
                run_records.append(
                    {
                        "phase": phase["id"],
                        "script": phase["script"],
                        "returncode": None,
                        "pre_stage_contract": previous_contract,
                        "pre_stage_validation": pre_findings,
                        "skipped": True,
                    }
                )
                failed = True
                break
        record = run_phase(script_dir, phase, repo_root, output_root)
        record["post_stage_validation"] = validate_contract(output_root, phase["id"])
        run_records.append(record)
        print(record["stdout"].strip())
        if record["stderr"].strip():
            print(record["stderr"].strip(), file=sys.stderr)
        if record["returncode"] != 0:
            failed = True
            break
        missing_outputs = [item for item in record["outputs"] if not item["exists"]]
        if missing_outputs:
            record["missing_outputs"] = missing_outputs
            failed = True
            break
        if record["post_stage_validation"] and not contract_is_valid(record["post_stage_validation"]):
            failed = True
            break

    json_validation = validate_json_outputs(output_root)
    invalid_json = [item for item in json_validation if not item["valid"]]
    if invalid_json:
        failed = True

    quality_gates = evaluate_quality_gates(output_root, args)
    if quality_gates["violations"] and args.strict:
        failed = True

    source_after = source_snapshot(repo_root) if args.source_guard else {}
    source_guard = compare_source_snapshots(source_before, source_after) if args.source_guard else {"enabled": False}
    if args.source_guard:
        source_guard["enabled"] = True
    if source_guard.get("changed") and args.strict:
        failed = True

    summary = {
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "output_root": str(output_root),
        "phases": run_records,
        "json_validation": json_validation,
        "quality_gates": quality_gates,
        "source_guard": source_guard,
        "success": not failed,
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    timestamped_summary = output_root / "logs" / f"pipeline-run-summary-{timestamp}.json"
    latest_summary = output_root / "logs" / "latest-pipeline-run-summary.json"
    compatibility_summary = output_root / "logs" / "pipeline-run-summary.json"
    write_json(timestamped_summary, summary)
    write_json(latest_summary, summary)
    write_json(compatibility_summary, summary)

    print(
        json.dumps(
            {
                "success": not failed,
                "phases_run": [record["phase"] for record in run_records],
                "invalid_json_count": len(invalid_json),
                "quality_gate_violations": quality_gates["violations"],
                "source_guard_changed": source_guard.get("changed", False),
                "run_summary": str(timestamped_summary),
                "latest_run_summary": str(latest_summary),
            },
            indent=2,
        )
    )
    return 0 if not failed else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full application architecture extraction pipeline.")
    parser.add_argument("--repo-root", default=".", help="Legacy repository root. Defaults to current directory.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    parser.add_argument("--from-phase", default="inventory", choices=[phase["id"] for phase in PHASES])
    parser.add_argument("--to-phase", default=None, choices=[phase["id"] for phase in PHASES])
    parser.add_argument("--strict", action="store_true", help="Fail the pipeline when quality gates or source guard checks fail.")
    parser.add_argument("--max-fail", type=int, default=None, help="Maximum allowed quality-review FAIL count.")
    parser.add_argument("--max-partial", type=int, default=None, help="Maximum allowed quality-review PARTIAL count.")
    parser.add_argument("--max-invalid-graph-edges", type=int, default=None, help="Maximum allowed dependency edges whose endpoints are not nodes.")
    parser.add_argument("--max-unknown-components", type=int, default=None, help="Maximum allowed components with Unknown type/layer/module.")
    parser.add_argument("--run-runtime-tests", action="store_true", help="Run optional dotnet test evidence collection in --no-build --no-restore mode.")
    parser.add_argument("--source-guard", dest="source_guard", action="store_true", default=True, help="Compare legacy source file hashes before and after the run.")
    parser.add_argument("--no-source-guard", dest="source_guard", action="store_false", help="Disable source modification guard.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
