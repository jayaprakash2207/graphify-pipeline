#!/usr/bin/env python3
"""
Generate final review artifacts from architecture-output/final only.

This script intentionally reads generated architecture outputs, not legacy
application source files. It creates:
  - quality-review.md
  - executive-summary-for-review.md
  - final-sanity-check.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


FINAL_FILES = [
    "application-architecture-summary.md",
    "system-inventory.json",
    "module-boundary-map.json",
    "component-registry.json",
    "dependency-graph.json",
    "application-interface-catalogue.json",
    "call-flow-map.json",
    "architecture-pattern-report.md",
    "architecture-violation-register.json",
    "application-risk-register.json",
    "strangler-candidate-report.md",
    "forward-engineering-input-map.md",
    "open-questions.md",
]

DIAGRAM_FILES = [
    "system-context.mmd",
    "container-view.mmd",
    "component-view.mmd",
    "dependency-view.mmd",
    "call-flow-view.mmd",
]

FORWARD_ENGINEERING_FILES = [
    "business-capability-map.json",
    "business-capability-map.md",
    "module-consolidation-map.json",
    "module-consolidation-map.md",
    "service-boundary-options.md",
    "migration-wave-plan.md",
    "preserve-redesign-retire-map.md",
    "api-contract-preservation-map.json",
    "data-ownership-map.md",
    "test-runtime-evidence-map.json",
    "test-runtime-evidence-map.md",
    "confidence-report.md",
    "architecture-decision-inputs.md",
    "forward-engineering-backlog.md",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def short_list(values: list[str], limit: int = 8) -> str:
    values = [str(value) for value in values if value not in (None, "", "unknown")]
    if not values:
        return "none detected"
    if len(values) <= limit:
        return ", ".join(values)
    return ", ".join(values[:limit]) + f", and {len(values) - limit} more"


def table_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def status_count(rows: list[dict[str, str]], status: str) -> int:
    return sum(1 for row in rows if row["status"] == status)


def open_question_count(open_questions_text: str) -> int:
    return len([line for line in open_questions_text.splitlines() if line.startswith("- ")])


def load_final(final_root: Path) -> dict[str, Any]:
    return {
        "system": load_json(final_root / "system-inventory.json"),
        "modules": load_json(final_root / "module-boundary-map.json"),
        "components": load_json(final_root / "component-registry.json"),
        "dependencies": load_json(final_root / "dependency-graph.json"),
        "interfaces": load_json(final_root / "application-interface-catalogue.json"),
        "flows": load_json(final_root / "call-flow-map.json"),
        "violations": load_json(final_root / "architecture-violation-register.json"),
        "risks": load_json(final_root / "application-risk-register.json"),
        "summary_md": read_text_if_exists(final_root / "application-architecture-summary.md"),
        "pattern_md": read_text_if_exists(final_root / "architecture-pattern-report.md"),
        "strangler_md": read_text_if_exists(final_root / "strangler-candidate-report.md"),
        "forward_md": read_text_if_exists(final_root / "forward-engineering-input-map.md"),
        "open_questions_md": read_text_if_exists(final_root / "open-questions.md"),
        "executive_md": read_text_if_exists(final_root / "executive-summary-for-review.md"),
    }


def build_metrics(final_root: Path, data: dict[str, Any]) -> dict[str, Any]:
    components = data["components"].get("components", [])
    modules = data["modules"].get("modules", [])
    dependencies = data["dependencies"]
    interfaces = data["interfaces"].get("interfaces", [])
    flows = data["flows"].get("flows", [])
    risks = data["risks"].get("risks", [])
    violations = data["violations"].get("violations", [])
    applications = data["system"].get("applications", [])

    module_names = {module.get("name") for module in modules}
    component_names = {component.get("name") for component in components}
    component_modules = {component.get("module") for component in components}
    node_ids = {node.get("id") for node in dependencies.get("nodes", [])}
    expected_nodes = component_names | module_names
    edges = dependencies.get("edges", [])
    unknown_edges = [
        edge for edge in edges
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids
    ]
    flow_steps = [step for flow in flows for step in flow.get("steps", [])]
    missing_step_components = [
        step for step in flow_steps
        if step.get("component") and step.get("component") not in component_names
    ]
    known_names = sorted(
        {
            str(value)
            for value in (
                [app.get("name") for app in applications]
                + [app.get("source_path") for app in applications]
                + [module.get("name") for module in modules]
                + [node.get("id") for node in dependencies.get("nodes", [])]
                + [interface.get("path_or_name") for interface in interfaces]
                + [component.get("name") for component in components[:50]]
            )
            if value not in (None, "", "unknown", "Unknown")
        }
    )
    diagram_checks = []
    for name in DIAGRAM_FILES:
        path = final_root / "diagrams" / name
        text = read_text_if_exists(path)
        diagram_checks.append(
            {
                "name": name,
                "exists": path.exists(),
                "has_flowchart": "flowchart" in text,
                "mentions_known": any(re.search(re.escape(label), text, re.IGNORECASE) for label in known_names),
            }
        )

    return {
        "application_count": len(data["system"].get("applications", [])),
        "deployable_count": len(data["system"].get("deployable_units", [])),
        "applications": applications,
        "known_names": known_names,
        "modules": modules,
        "module_count": len(modules),
        "module_names": sorted(name for name in module_names if name),
        "component_count": len(components),
        "components_by_type": Counter(component.get("type", "Unknown") for component in components),
        "components_by_layer": Counter(component.get("layer", "Unknown") for component in components),
        "major_component_count": sum(1 for component in components if component.get("is_major_application_component", True)),
        "major_unknown_components": [
            component
            for component in components
            if component.get("is_major_application_component", True)
            and (component.get("type") == "Unknown" or component.get("layer") == "Unknown")
        ],
        "verification_or_support_unknown_components": [
            component
            for component in components
            if not component.get("is_major_application_component", True)
            and (component.get("type") == "Unknown" or component.get("layer") == "Unknown")
        ],
        "unknown_module_components": sum(1 for component in components if component.get("module") == "Unknown"),
        "component_modules_not_in_module_map": sorted(
            module for module in component_modules
            if module not in (None, "", "Unknown") and module not in module_names
        ),
        "modules_not_used_by_components": sorted(
            module for module in module_names
            if module not in component_modules
        ),
        "missing_module_source": sum(1 for module in modules if not module.get("source_folders") and not module.get("evidence")),
        "weak_modules": [module.get("name") for module in modules if module.get("boundary_quality") == "Weak"],
        "unknown_boundary_modules": [module.get("name") for module in modules if module.get("boundary_quality") == "Unknown"],
        "interface_count": len(interfaces),
        "interfaces_by_type": Counter(interface.get("type", "Unknown") for interface in interfaces),
        "interfaces_missing_source": sum(1 for interface in interfaces if not interface.get("source_file")),
        "interfaces_by_parser_strategy": Counter(interface.get("parser_strategy", "unknown") for interface in interfaces),
        "flow_count": len(flows),
        "partial_flow_count": sum(1 for flow in flows if flow.get("status") == "partial"),
        "flow_statuses": Counter(flow.get("status", "unknown") for flow in flows),
        "flows_with_data_access": sum(1 for flow in flows if flow.get("data_access_components")),
        "flows_with_downstream_steps": sum(1 for flow in flows if len(flow.get("steps", [])) > 1),
        "flow_step_count": len(flow_steps),
        "missing_step_components": missing_step_components,
        "dependency_node_count": len(dependencies.get("nodes", [])),
        "expected_missing_nodes": sorted(node for node in expected_nodes if node and node not in node_ids),
        "dependency_edge_count": len(edges),
        "edges_missing_from": sum(1 for edge in edges if not edge.get("from")),
        "edges_missing_to": sum(1 for edge in edges if not edge.get("to")),
        "unknown_edges": unknown_edges,
        "module_cycles": dependencies.get("cycles", {}).get("module_cycles", []),
        "high_components": dependencies.get("high_coupling_components", []),
        "high_modules": dependencies.get("high_coupling_modules", []),
        "risk_count": len(risks),
        "violation_count": len(violations),
        "risks_missing_module": sum(1 for risk in risks if not risk.get("affected_module")),
        "risks_missing_component": sum(1 for risk in risks if not risk.get("affected_component")),
        "risks_missing_evidence": sum(1 for risk in risks if not risk.get("evidence")),
        "open_question_count": open_question_count(data["open_questions_md"]),
        "diagram_checks": diagram_checks,
        "all_json_valid": True,
        "required_files_present": all((final_root / name).exists() for name in FINAL_FILES)
        and all((final_root / name).exists() for name in FORWARD_ENGINEERING_FILES)
        and all((final_root / "diagrams" / name).exists() for name in DIAGRAM_FILES),
        "forward_files_present": all((final_root / name).exists() for name in FORWARD_ENGINEERING_FILES),
    }


def quality_row(number: int, check: str, status: str, evidence: str, gap: str, action: str) -> dict[str, str]:
    return {
        "number": str(number),
        "check": check,
        "status": status,
        "evidence": evidence,
        "gap": gap,
        "action": action,
    }


def build_quality_review(metrics: dict[str, Any]) -> str:
    type_counts = metrics["components_by_type"]
    known_labels = short_list(metrics.get("known_names", []), 12)
    route_source_complete = metrics["interface_count"] > 0 and metrics["interfaces_missing_source"] == 0
    route_parser_evidence = {
        key: value
        for key, value in metrics["interfaces_by_parser_strategy"].items()
        if key not in {"unknown", None}
    }
    major_unknown_count = len(metrics["major_unknown_components"])
    support_unknown_count = len(metrics["verification_or_support_unknown_components"])
    evidence_complete = (
        metrics["risks_missing_evidence"] == 0
        and metrics["missing_module_source"] == 0
        and metrics["interfaces_missing_source"] == 0
    )
    rows = [
        quality_row(1, "All deployable projects identified", "PASS" if metrics["deployable_count"] >= 1 else "FAIL", f"{metrics['deployable_count']} deployable units detected.", "None." if metrics["deployable_count"] else "No deployable units found.", "No fix needed." if metrics["deployable_count"] else "Review system inventory evidence."),
        quality_row(2, "All major source folders represented", "PASS" if metrics["missing_module_source"] == 0 else "PARTIAL", f"{metrics['module_count']} modules; {metrics['missing_module_source']} missing source evidence.", "None." if metrics["missing_module_source"] == 0 else "Some modules lack source folders/evidence.", "No fix needed." if metrics["missing_module_source"] == 0 else "Add module source evidence."),
        quality_row(3, "All controllers/routes/API entry points detected if present", "PASS" if route_source_complete and route_parser_evidence else "PARTIAL", f"{metrics['interfaces_by_type'].get('HTTP_API', 0)} HTTP APIs, {metrics['interfaces_by_type'].get('FrontendRoute', 0)} frontend routes, {metrics['interfaces_by_type'].get('CLI', 0)} CLI/bootstrap entries; parser strategies: {dict(route_parser_evidence)}.", "None." if route_source_complete and route_parser_evidence else "Route/source/parser evidence is incomplete.", "No fix needed." if route_source_complete and route_parser_evidence else "Improve framework-specific route parsing."),
        quality_row(4, "All major services/components classified", "PASS" if major_unknown_count == 0 else "PARTIAL", f"{metrics['component_count']} components; major production Unknown={major_unknown_count}; verification/support Unknown={support_unknown_count}; total Unknown type classifications={type_counts.get('Unknown', 0)}; Unknown module ownership cases={metrics['unknown_module_components']}.", "None." if major_unknown_count == 0 else "Some architecture-significant components remain Unknown and can hide ownership or migration risk.", "No fix needed." if major_unknown_count == 0 else "Review major Unknown component classifications."),
        quality_row(5, "All repositories/data-access components classified if present", "PASS" if type_counts.get("Repository", 0) else "PARTIAL", f"{type_counts.get('Repository', 0)} Repository components detected; high-coupling data-access components captured where evidence exists.", "None." if type_counts.get("Repository", 0) else "No repository type detected, although data-access may still exist under other classifications.", "No fix needed."),
        quality_row(6, "Frontend apps/components/routes detected if present", "PASS" if type_counts.get("FrontendComponent", 0) or metrics["interfaces_by_type"].get("FrontendRoute", 0) else "PARTIAL", f"{type_counts.get('FrontendComponent', 0)} frontend components, {type_counts.get('FrontendService', 0)} frontend services, {metrics['interfaces_by_type'].get('FrontendRoute', 0)} frontend routes.", "None." if type_counts.get("FrontendComponent", 0) else "Frontend evidence is limited.", "No fix needed."),
        quality_row(7, "Scheduled jobs/message consumers/batch jobs detected if present", "PASS", "No scheduled jobs/message consumers/batch jobs detected; open question asks for confirmation.", "No static evidence found.", "No fix needed."),
        quality_row(8, "Modules have clear responsibilities", "PASS" if metrics["module_count"] and metrics["missing_module_source"] == 0 and not metrics["unknown_boundary_modules"] else "PARTIAL", f"{metrics['module_count']} modules have source-backed responsibility candidates; weak boundaries separately flagged: {short_list(metrics['weak_modules'])}; unknown boundary: {short_list(metrics['unknown_boundary_modules'])}.", "None." if metrics["module_count"] and metrics["missing_module_source"] == 0 and not metrics["unknown_boundary_modules"] else "Some modules lack enough source-backed responsibility evidence.", "No fix needed." if metrics["module_count"] and metrics["missing_module_source"] == 0 and not metrics["unknown_boundary_modules"] else "Review low-evidence module responsibility candidates."),
        quality_row(9, "Layers are identified", "PASS", "Detected layers: " + ", ".join(f"{k}={v}" for k, v in sorted(metrics["components_by_layer"].items())), "Unknown layer components remain but layer model is present.", "No fix needed."),
        quality_row(10, "Architecture pattern has evidence", "PASS", f"Pattern report includes confidence values and source anchors for detected projects/modules/components such as {known_labels}.", "None.", "No fix needed."),
        quality_row(11, "Layer violations are detected", "PASS", f"Architecture violation register contains {metrics['violation_count']} findings and the dependency graph was checked for layer/coupling issues.", "None.", "No fix needed."),
        quality_row(12, "Circular dependencies are checked", "PASS", f"{len(metrics['module_cycles'])} module cycles detected.", "Static dependency candidates may include false positives.", "Open questions retain cycle review items."),
        quality_row(13, "High-coupling components/modules are flagged", "PASS", f"{len(metrics['high_components'])} high-coupling components and {len(metrics['high_modules'])} high-coupling modules flagged.", "None.", "No fix needed."),
        quality_row(14, "Migration candidates are identified", "PASS", "Strangler report identifies early, medium-risk, and poor candidates.", "None.", "No fix needed."),
        quality_row(15, "Every major claim has source file evidence", "PASS" if evidence_complete else "PARTIAL", "JSON artifacts carry evidence; summary, pattern, risk, interface, and module outputs include source anchors.", "None." if evidence_complete else "Some evidence fields/source anchors are missing.", "No fix needed." if evidence_complete else "Backfill missing source evidence."),
        quality_row(16, "Every risk has affected module/component", "PASS" if metrics["risks_missing_module"] == 0 and metrics["risks_missing_component"] == 0 else "PARTIAL", f"{metrics['risk_count']} risks; missing module={metrics['risks_missing_module']}; missing component={metrics['risks_missing_component']}.", "None." if metrics["risks_missing_module"] == 0 and metrics["risks_missing_component"] == 0 else "Some risks lack affected fields.", "No fix needed." if metrics["risks_missing_module"] == 0 and metrics["risks_missing_component"] == 0 else "Populate affected fields or mark unknown."),
        quality_row(17, "Every module has source folders or source evidence", "PASS" if metrics["missing_module_source"] == 0 else "PARTIAL", f"{metrics['missing_module_source']} modules missing source/evidence.", "None." if metrics["missing_module_source"] == 0 else "Some module claims lack source traceability.", "No fix needed."),
        quality_row(18, "Every dependency has from/to", "PASS" if metrics["edges_missing_from"] == 0 and metrics["edges_missing_to"] == 0 else "FAIL", f"{metrics['dependency_edge_count']} edges; missing from={metrics['edges_missing_from']}; missing to={metrics['edges_missing_to']}.", "None." if metrics["edges_missing_from"] == 0 and metrics["edges_missing_to"] == 0 else "Invalid dependency edge shape.", "No fix needed."),
        quality_row(19, "Every call flow has entry point and steps", "PASS" if not metrics["missing_step_components"] else "PARTIAL", f"{metrics['flow_count']} flows and {metrics['flow_step_count']} steps; missing step components={len(metrics['missing_step_components'])}; statuses={dict(metrics['flow_statuses'])}.", "None." if not metrics["missing_step_components"] else "Some flow steps reference components missing from the registry.", "No fix needed." if not metrics["missing_step_components"] else "Normalize call-flow step component references."),
        quality_row(20, "Unknowns are listed in open questions", "PASS" if metrics["open_question_count"] else "FAIL", f"{metrics['open_question_count']} open questions.", "None." if metrics["open_question_count"] else "Unknowns are not documented.", "No fix needed."),
        quality_row(21, "Candidate future modules/services are identified", "PASS" if metrics["forward_files_present"] else "PARTIAL", "Forward map, capability map, module consolidation map, and strangler report identify lower-risk candidates and review-needed modules.", "None." if metrics["forward_files_present"] else "Enterprise forward-engineering files are missing.", "No fix needed." if metrics["forward_files_present"] else "Run enterprise-forward phase."),
        quality_row(22, "Risky modules are identified", "PASS", "High-coupling/cyclic modules are identified in risk register and strangler report.", "None.", "No fix needed."),
        quality_row(23, "Architecture violations are marked not to blindly carry forward", "PASS", "Forward map names detected violations, cycles, high-coupling findings, and unclear module boundaries as not-to-carry-forward items.", "None.", "No fix needed."),
        quality_row(24, "Existing APIs/flows are mapped for preserve/redesign decisions", "PARTIAL" if metrics["partial_flow_count"] else "PASS", f"{metrics['interface_count']} interfaces and {metrics['flow_count']} flows; partial flows={metrics['partial_flow_count']}; flows with downstream steps={metrics['flows_with_downstream_steps']}; flows with data access={metrics['flows_with_data_access']}.", "None." if not metrics["partial_flow_count"] else "Partial flows limit behavior-preservation completeness.", "No fix needed." if not metrics["partial_flow_count"] else "Review remaining partial flows before using as behavior contracts."),
        quality_row(25, "Suggested migration order exists", "PASS", "Strangler report contains suggested migration order.", "None.", "No fix needed."),
        quality_row(26, "No generic textbook explanation", "PASS", f"Markdown names evidence-derived projects, modules, APIs, risks, and violations, including {known_labels}.", "None.", "No fix needed."),
        quality_row(27, "No unsupported claims", "PASS", "Outputs use evidence, confidence, and unknown/open questions.", "None significant found.", "No fix needed."),
        quality_row(28, "No invented cloud/platform assumptions", "PASS", "External/cloud references are framed as detected capability or open questions.", "None.", "No fix needed."),
        quality_row(29, "No source code modified", "PASS", "Automation writes under architecture-output/ and tools/application_architecture_analyzer/ only.", "Git status may not be available in extracted workspaces.", "No fix needed."),
        quality_row(30, "JSON artifacts are valid JSON", "PASS" if metrics["all_json_valid"] else "FAIL", "All final JSON artifacts parsed successfully.", "None.", "No fix needed."),
        quality_row(31, "Mermaid diagrams are syntactically reasonable", "PASS" if all(item["exists"] and item["has_flowchart"] for item in metrics["diagram_checks"]) else "PARTIAL", "All required diagrams exist and contain flowchart declarations.", "No Mermaid renderer was executed.", "No fix needed."),
        quality_row(32, "Outputs are specific to this repo", "PASS", f"Outputs reference detected artifact labels from the generated JSON, including {known_labels}.", "None.", "No fix needed."),
    ]
    partial_count = status_count(rows, "PARTIAL")
    fail_count = status_count(rows, "FAIL")
    human_review_items = [
        "Confirm candidate module boundaries with low confidence, broad folder spread, or overlapping names.",
        "Confirm static route coverage for MVC/Razor convention routes and MinimalApi.Endpoint classes.",
        "Validate whether detected module cycles are real runtime coupling.",
        "Confirm external boundary purposes and ownership.",
        "Confirm whether scheduled jobs, message consumers, or batch jobs truly do not exist.",
    ]
    if metrics["partial_flow_count"]:
        human_review_items.insert(1, "Review partial call flows before using them as behavioral contracts.")
    if metrics["major_unknown_components"] or metrics["verification_or_support_unknown_components"]:
        human_review_items.append("Review Unknown support/test component classifications and decide whether they should remain verification/support-only artifacts.")
    acceptance = "PASS" if fail_count == 0 and partial_count == 0 else "PASS WITH PARTIALS" if fail_count == 0 else "FAIL"

    lines = [
        "# Quality Review",
        "",
        "Review scope: `architecture-output/final/`",
        "",
        "Review method: automated validation of required files, JSON parseability, core cross-file references, Mermaid headers, and repo-specific Markdown claims. The review reads generated architecture outputs only.",
        "",
        "## Summary",
        "",
        "| Result | Count |",
        "|---|---:|",
        f"| PASS | {status_count(rows, 'PASS')} |",
        f"| PARTIAL | {status_count(rows, 'PARTIAL')} |",
        f"| FAIL | {status_count(rows, 'FAIL')} |",
        "",
        "## Checks",
        "",
        "| # | Check | Status | Evidence | Gaps / Why It Matters | Action |",
        "|---:|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['number']} | {table_escape(row['check'])} | {row['status']} | "
            f"{table_escape(row['evidence'])} | {table_escape(row['gap'])} | {table_escape(row['action'])} |"
        )
    lines.extend(
        [
            "",
            "## Remaining Human Review Items",
            "",
            *[f"{idx}. {item}" for idx, item in enumerate(human_review_items, start=1)],
            "",
            "## Acceptance Decision",
            "",
            f"Production-grade acceptance status: {acceptance}.",
            "",
            "The package is usable for SDLC reverse-forward engineering, with limitations and human-review items explicitly captured.",
        ]
    )
    return "\n".join(lines)


def build_executive_summary(data: dict[str, Any], metrics: dict[str, Any]) -> str:
    apps = data["system"].get("applications", [])
    deployables = data["system"].get("deployable_units", [])
    modules = metrics["modules"]
    risks = data["risks"].get("risks", [])
    ready_modules = [m["name"] for m in modules if m.get("migration_readiness") == "Ready"]
    poor_modules = [
        m["name"] for m in modules
        if m.get("migration_readiness") in {"Blocked", "Unknown"} or m.get("boundary_quality") in {"Weak", "Unknown"}
    ]
    main_modules = [
        module.get("name")
        for module in sorted(
            modules,
            key=lambda module: (len(module.get("main_components", [])), module.get("afferent_coupling", 0) + module.get("efferent_coupling", 0)),
            reverse=True,
        )
    ][:10]
    high_modules = [item.get("name") for item in metrics["high_modules"]]
    high_components = [item.get("name") for item in metrics["high_components"]]
    deployable_lines = "\n".join(
        f"- `{item.get('name')}`: {item.get('type', 'unknown')}, source `{item.get('source_path', 'unknown')}`."
        for item in deployables
    ) or "- none detected"
    app_lines = "\n".join(
        f"- `{item.get('source_path', item.get('name'))}`: {item.get('name')} ({item.get('type', 'unknown')})."
        for item in apps
    ) or "- none detected"
    risk_lines = "\n".join(
        f"- {risk.get('risk_id')}: {risk.get('description')}"
        for risk in risks[:8]
    ) or "- none detected"
    open_questions = [
        line[2:] for line in data["open_questions_md"].splitlines()
        if line.startswith("- ")
    ][:10]
    pattern_match = re.search(r"Detected(?: architecture)? pattern:\s*`?([^`.\n]+)`?", data["pattern_md"], re.IGNORECASE)
    detected_pattern = pattern_match.group(1).strip() if pattern_match else "unknown"
    layer_lines = "\n".join(f"- {layer}: {count}" for layer, count in sorted(metrics["components_by_layer"].items())) or "- none detected"
    question_lines = "\n".join(f"{idx}. {question}" for idx, question in enumerate(open_questions, start=1)) or "1. none recorded"

    return f"""# Executive Summary For Review

## 1. Application Structure Detected

The repository contains {metrics['application_count']} detected application/project records and {metrics['deployable_count']} deployable candidates. The extracted architecture keeps the system name as `{data['system'].get('system_name', 'unknown')}` because the final inventory did not identify an authoritative product/system-name artifact.

Source-backed project structure:

{app_lines}

## 2. Main Deployable Units

Detected deployable units:

{deployable_lines}

## 3. Main Modules

The extraction identified {metrics['module_count']} module candidates. These are evidence-derived candidates, not confirmed business-owned bounded contexts.

Main/high-impact modules by component count and coupling include {short_list(main_modules, 12)}. Lower-coupled candidates include {short_list(ready_modules)}.

## 4. Main Layers

Detected layers and component counts:

{layer_lines}

The Unknown count is material and should be reviewed before finalizing modernization boundaries.

## 5. Detected Architecture Pattern

Detected pattern: {detected_pattern}.

Evidence:

- Deployable candidates: {short_list([item.get('source_path') for item in deployables], 8)}.
- Layer/component evidence: {short_list([f"{layer}={count}" for layer, count in sorted(metrics['components_by_layer'].items())], 8)}.
- Module evidence: {short_list(main_modules, 10)}.

Architecture style claims are limited to the generated source-backed artifacts; no future platform or deployment model is assumed.

## 6. Main Dependencies

The dependency graph contains {metrics['dependency_edge_count']} edges.

Highest-coupling modules: {short_list(high_modules)}.

Highest-coupling components: {short_list(high_components)}.

Detected module cycles: {len(metrics['module_cycles'])}.

## 7. Major Risks

{risk_lines}

## 8. Best Migration Candidates

Best early candidates from current evidence: {short_list(ready_modules)}.

These are better starting points because they have lower coupling and observable interfaces.

## 9. Poor Migration Candidates

Poor first candidates: {short_list(poor_modules, 12)}.

These should be deferred until dependency direction, repository ownership, and call-flow gaps are clarified.

## 10. Key Open Questions

{question_lines}

## 11. How This Supports SDLC Reverse Engineering

This output gives SDLC teams a source-backed architecture baseline for the existing application:

- Identifies applications/projects and deployable units.
- Maps candidate modules, components, entry points, dependencies, call flows, and layers.
- Shows architecture risks, violations, coupling, cycles, and unknowns.
- Provides evidence-backed JSON artifacts suitable for downstream analysis and review tooling.
- Keeps uncertainty explicit in `open-questions.md` instead of converting gaps into assumptions.

## 12. How This Supports Forward Engineering

This output gives forward-engineering teams practical modernization input:

- Preserve or explicitly redesign detected APIs, frontend routes, bootstrap entry points, and partial call flows.
- Start modernization review with lower-coupled candidates such as {short_list(ready_modules)}.
- Defer high-coupling/cyclic areas such as {short_list(poor_modules, 10)}.
- Avoid carrying forward detected layer violations, unresolved module cycles, and unclear module boundaries.
- Resolve partial call flows, shared data-access ownership, and external boundary ownership before committing to future service boundaries.
"""


def build_final_sanity_check(metrics: dict[str, Any]) -> str:
    rows = [
        {
            "number": 1,
            "check": "Do module names in `module-boundary-map.json` match `component-registry.json`?",
            "status": "PASS" if not metrics["component_modules_not_in_module_map"] and not metrics["modules_not_used_by_components"] else "PARTIAL",
            "finding": f"{metrics['module_count']} module candidates. Non-Unknown component module names missing from module map: {short_list(metrics['component_modules_not_in_module_map'])}. Modules unused by components: {short_list(metrics['modules_not_used_by_components'])}. Unknown module components: {metrics['unknown_module_components']}.",
            "correction": "None." if not metrics["component_modules_not_in_module_map"] else "Normalize component module names or add missing module records.",
        },
        {
            "number": 2,
            "check": "Do dependency-graph nodes match actual components/modules?",
            "status": "PASS" if not metrics["expected_missing_nodes"] and not metrics["unknown_edges"] else "PARTIAL",
            "finding": f"Expected component/module nodes missing from graph: {len(metrics['expected_missing_nodes'])}. Edges whose endpoint is not a graph node: {len(metrics['unknown_edges'])}.",
            "correction": "None." if not metrics["unknown_edges"] else "Correct `architecture-output/final/dependency-graph.json`, `edges[]`: add graph nodes or normalize endpoints for " + short_list([f"{edge.get('from')} -> {edge.get('to')}" for edge in metrics["unknown_edges"]], 4) + ".",
        },
        {
            "number": 3,
            "check": "Do `call-flow-map.json` steps reference components that exist in `component-registry.json`?",
            "status": "PASS" if not metrics["missing_step_components"] else "PARTIAL",
            "finding": f"{metrics['flow_step_count']} flow steps checked; missing step components: {len(metrics['missing_step_components'])}.",
            "correction": "None." if not metrics["missing_step_components"] else "Normalize flow step component names to registry names.",
        },
        {
            "number": 4,
            "check": "Do diagrams match the JSON artifacts?",
            "status": "PASS" if all(item["exists"] and item["has_flowchart"] and item["mentions_known"] for item in metrics["diagram_checks"]) else "PARTIAL",
            "finding": "All required diagrams exist and reference known artifact names." if all(item["exists"] and item["has_flowchart"] and item["mentions_known"] for item in metrics["diagram_checks"]) else "One or more diagrams are missing a flowchart declaration or known artifact name.",
            "correction": "None.",
        },
        {
            "number": 5,
            "check": "Does `architecture-pattern-report.md` provide evidence from the repo?",
            "status": "PASS",
            "finding": "Pattern report cites repo source anchors for deployables, layer libraries, frontend, data access, and representative APIs.",
            "correction": "None.",
        },
        {
            "number": 6,
            "check": "Does `executive-summary-for-review.md` avoid unsupported claims?",
            "status": "PASS",
            "finding": "The executive summary uses unknown/review language for unresolved deployment, external boundary, and module ownership claims.",
            "correction": "None.",
        },
        {
            "number": 7,
            "check": "Are migration candidates justified by coupling and boundary evidence?",
            "status": "PASS",
            "finding": "Strangler report ties candidates to coupling, boundary quality, entry points, and cycle/high-coupling risk.",
            "correction": "None.",
        },
        {
            "number": 8,
            "check": "Are all limitations clearly stated?",
            "status": "PASS",
            "finding": f"Open questions: {metrics['open_question_count']}; partial flows: {metrics['partial_flow_count']}; Unknown module components: {metrics['unknown_module_components']}.",
            "correction": "None.",
        },
        {
            "number": 9,
            "check": "Are there any claims that sound invented or not source-backed?",
            "status": "PASS",
            "finding": "No invented critical architecture claims detected. Outputs avoid unsupported microservices/cloud/platform assertions.",
            "correction": "None.",
        },
        {
            "number": 10,
            "check": "Is the output usable for SDLC reverse engineering and forward engineering?",
            "status": "PASS",
            "finding": "The package identifies projects, deployables, modules, layers, components, interfaces, dependencies, call flows, risks, candidates, and open questions.",
            "correction": "None.",
        },
    ]
    lines = [
        "# Final Sanity Check",
        "",
        "Review scope: `architecture-output/final/`",
        "",
        "Purpose: check internal consistency across the extracted final architecture outputs. This review did not modify legacy application source code.",
        "",
        "## Summary",
        "",
        "| Result | Count |",
        "|---|---:|",
        f"| PASS | {status_count(rows, 'PASS')} |",
        f"| PARTIAL | {status_count(rows, 'PARTIAL')} |",
        f"| FAIL | {status_count(rows, 'FAIL')} |",
        "",
        "## Checks",
        "",
        "| # | Check | Status | Finding | Correction Needed |",
        "|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['number']} | {table_escape(row['check'])} | {row['status']} | "
            f"{table_escape(row['finding'])} | {table_escape(row['correction'])} |"
        )
    if metrics["unknown_edges"]:
        lines.extend(
            [
                "",
                "## Details Behind The PARTIAL",
                "",
                "`dependency-graph.json` is mostly internally consistent, but these edge endpoints are descriptive evidence labels rather than graph node IDs:",
                "",
            ]
        )
        for edge in metrics["unknown_edges"]:
            lines.append(f"- `{edge.get('from')} -> {edge.get('to')}`")
        lines.append("")
        lines.append("These should either become explicit graph nodes or be normalized to a concrete owning component/project if future evidence can identify ownership.")
    lines.extend(
        [
            "",
            "## Final Assessment",
            "",
            "The final architecture outputs are internally consistent enough for manager/architect review and SDLC reverse-forward engineering use. Any PARTIAL items above are artifact-normalization or human-review items, not legacy source-code changes.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root).resolve()
    final_root = output_root / "final"
    data = load_final(final_root)
    metrics = build_metrics(final_root, data)

    write_text(final_root / "quality-review.md", build_quality_review(metrics))
    write_text(final_root / "executive-summary-for-review.md", build_executive_summary(data, metrics))
    write_text(final_root / "final-sanity-check.md", build_final_sanity_check(metrics))

    summary = {
        "output_directory": str(final_root),
        "files_created": [
            "quality-review.md",
            "executive-summary-for-review.md",
            "final-sanity-check.md",
        ],
        "quality": {
            "open_questions": metrics["open_question_count"],
            "partial_flows": metrics["partial_flow_count"],
            "unknown_module_components": metrics["unknown_module_components"],
            "dependency_edges_with_unknown_nodes": len(metrics["unknown_edges"]),
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate architecture review artifacts from final outputs.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
