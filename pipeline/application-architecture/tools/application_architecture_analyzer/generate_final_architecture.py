#!/usr/bin/env python3
"""
Generate final Application Architecture artifacts from evidence packs only.

Input is restricted to architecture-output/evidence-packs/*.json. The script
does not scan or read legacy application source files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FINAL_GENERATOR_VERSION = "0.1.0"

PACK_FILES = {
    "system": "system-inventory-pack.json",
    "modules": "module-boundary-pack.json",
    "components": "component-registry-pack.json",
    "dependencies": "dependency-pack.json",
    "entry_points": "entry-point-pack.json",
    "flows": "call-flow-pack.json",
    "layering": "layering-pattern-pack.json",
    "external": "external-boundary-pack.json",
    "frontend": "frontend-application-pack.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def evidence_ref(file: str | None, line: Any = None, reason: str | None = None) -> dict[str, Any]:
    return {"file": file or "unknown", "line": line, "reason": reason or "source evidence from evidence pack"}


def unique(values: list[Any]) -> list[Any]:
    seen = []
    for value in values:
        if value in (None, "", "unknown"):
            continue
        if value not in seen:
            seen.append(value)
    return seen


def sanitize_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not value or value[0].isdigit():
        value = "N_" + value
    return value[:80]


def mermaid_label(value: Any) -> str:
    return str(value or "unknown").replace('"', "'").replace("\n", " ")


def short_list(items: list[str], limit: int = 8) -> str:
    if not items:
        return "none detected"
    if len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f", and {len(items) - limit} more"


def md_list(items: list[str], empty: str = "- none detected") -> str:
    cleaned = [item for item in items if item not in (None, "", "unknown")]
    return "\n".join(f"- {item}" for item in cleaned) if cleaned else empty


def source_file_list(evidence: list[dict[str, Any]], limit: int = 5) -> list[str]:
    files = []
    for item in evidence:
        file = item.get("file") or item.get("source_file")
        if file and file != "unknown" and file not in files:
            files.append(file)
        if len(files) >= limit:
            break
    return files


def project_source_files(projects: list[dict[str, Any]], limit: int = 8) -> list[str]:
    files = []
    for project in projects:
        for item in project.get("evidence", []):
            file = item.get("file")
            if file and file not in files:
                files.append(file)
            if len(files) >= limit:
                return files
    return files


def infer_module_responsibility(module: dict[str, Any]) -> str:
    responsibility_guess = str(module.get("responsibility_guess") or "").strip()
    if responsibility_guess and responsibility_guess.lower() != "unknown" and not responsibility_guess.lower().startswith("unknown;"):
        return responsibility_guess
    types = Counter(component.get("type", "Unknown") for component in module.get("components", []))
    top_types = [name for name, _ in types.most_common(4) if name != "Unknown"]
    folders = module.get("source_folders", [])[:3]
    routes = [
        entry.get("path_or_name")
        for entry in module.get("entry_points", [])
        if entry.get("path_or_name") and entry.get("path_or_name") != "unknown"
    ][:4]
    parts = []
    if routes:
        parts.append("entry points " + ", ".join(routes))
    if top_types:
        parts.append("owns " + ", ".join(top_types).lower() + " components")
    if folders:
        parts.append("evidenced by " + ", ".join(folders))
    if not parts:
        return "unknown"
    return "Candidate boundary inferred from source-backed parsed evidence; " + "; ".join(parts) + "."


def best_pattern(packs: dict[str, Any]) -> dict[str, Any]:
    candidates = packs["layering"].get("candidate_patterns", [])
    if not candidates:
        return {"pattern": "Unknown", "confidence": 0.0, "evidence": "No pattern candidates detected."}
    return max(candidates, key=lambda item: float(item.get("confidence", 0.0)))


def secondary_patterns(packs: dict[str, Any], primary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in packs["layering"].get("candidate_patterns", [])
        if item.get("pattern") != primary.get("pattern")
    ]


def top_components_by_type(components: list[dict[str, Any]], component_type: str, limit: int = 3) -> list[str]:
    return [component["name"] for component in components if component.get("type") == component_type][:limit]


def risk_for_low_confidence_module_family(module_map: dict[str, Any]) -> dict[str, Any] | None:
    weak = [
        module for module in module_map.get("modules", [])
        if module.get("boundary_quality") in {"Weak", "Unknown"}
    ]
    if not weak:
        return None
    weak.sort(key=lambda item: int(item.get("afferent_coupling", 0)) + int(item.get("efferent_coupling", 0)), reverse=True)
    return weak[0]


def load_packs(output_root: Path) -> dict[str, Any]:
    pack_root = output_root / "evidence-packs"
    return {name: load_json(pack_root / filename) for name, filename in PACK_FILES.items()}


def build_indexes(packs: dict[str, Any]) -> dict[str, Any]:
    modules = packs["modules"].get("module_candidates", [])
    components = packs["components"].get("components", [])
    entry_points = packs["entry_points"].get("entry_points", [])
    flows = packs["flows"].get("flows", [])
    by_module = {module["name"]: module for module in modules}
    by_component = {component["name"]: component for component in components}
    return {
        "modules": modules,
        "components": components,
        "entry_points": entry_points,
        "flows": flows,
        "by_module": by_module,
        "by_component": by_component,
    }


def boundary_quality(module: dict[str, Any], cycle_modules: set[str]) -> str:
    total = int(module.get("afferent_coupling", 0)) + int(module.get("efferent_coupling", 0))
    folder_count = len(module.get("source_folders", []))
    confidence = float(module.get("confidence", 0.0))
    if confidence < 0.6:
        return "Unknown"
    if module["name"] in cycle_modules or total >= 6 or folder_count > 10:
        return "Weak"
    if total <= 1 and folder_count <= 4:
        return "Strong"
    return "Medium"


def migration_readiness(module: dict[str, Any], cycle_modules: set[str]) -> str:
    total = int(module.get("afferent_coupling", 0)) + int(module.get("efferent_coupling", 0))
    entry_count = len(module.get("entry_points", []))
    confidence = float(module.get("confidence", 0.0))
    if confidence < 0.6:
        return "Unknown"
    if module["name"] in cycle_modules or total >= 6:
        return "Blocked"
    if int(module.get("efferent_coupling", 0)) <= 1 and entry_count > 0:
        return "Ready"
    return "Needs Refactoring"


def cycle_module_set(dep_pack: dict[str, Any]) -> set[str]:
    modules: set[str] = set()
    for cycle in dep_pack.get("cycles", {}).get("module_cycles", []):
        for item in cycle.get("cycle", []):
            modules.add(item)
    return modules


def build_system_inventory(packs: dict[str, Any]) -> dict[str, Any]:
    system = packs["system"]
    applications = []

    def normalize_project_type(project_type: str | None) -> str:
        mapping = {
            "backend_web_api": "backend_web_api",
            "backend_web_app": "backend_web_api",
            "frontend_spa": "frontend_spa",
            "database_support_library": "database_project",
            "database_project": "database_project",
            "library": "library",
            "worker": "worker",
            "test_project": "library",
        }
        return mapping.get(project_type or "unknown", "unknown")

    seen_projects: set[tuple[str, str]] = set()
    for group in ("backend_projects", "frontend_projects", "database_support_projects", "supporting_projects"):
        for project in system.get(group, []):
            key = (project.get("name", "unknown"), project.get("source_path", "unknown"))
            if key in seen_projects:
                continue
            seen_projects.add(key)
            applications.append(
                {
                    "name": project.get("name"),
                    "type": normalize_project_type(project.get("type")),
                    "original_type": project.get("type", "unknown"),
                    "framework": project.get("framework", "unknown"),
                    "deployable": bool(project.get("deployable", False)),
                    "source_path": project.get("source_path", "unknown"),
                    "confidence": project.get("confidence", 0.0),
                    "evidence": project.get("evidence", []),
                }
            )
    open_questions = list(system.get("open_questions", []))
    open_questions.append("Confirm whether test projects should be included in enterprise system inventory views or tracked separately.")
    return {
        "system_name": "unknown",
        "generated_at": utc_now(),
        "source_evidence_pack": "architecture-output/evidence-packs/system-inventory-pack.json",
        "applications": applications,
        "deployable_units": [
            {
                "name": project.get("name"),
                "type": normalize_project_type(project.get("type")),
                "original_type": project.get("type"),
                "source_path": project.get("source_path"),
                "evidence": project.get("evidence", []),
                "confidence": project.get("confidence", 0.0),
            }
            for project in system.get("deployable_units", [])
        ],
        "supporting_projects": system.get("supporting_projects", []),
        "database_support_projects": system.get("database_support_projects", []),
        "frontend_projects": system.get("frontend_projects", []),
        "backend_projects": system.get("backend_projects", []),
        "test_projects": system.get("test_projects", []),
        "workers_or_jobs": system.get("workers_or_jobs", []),
        "build_files": system.get("build_files", []),
        "deployment_files": system.get("deployment_files", []),
        "docker_compose_services": system.get("docker_compose_services", []),
        "open_questions": open_questions,
    }


def build_module_boundary_map(packs: dict[str, Any]) -> dict[str, Any]:
    dep = packs["dependencies"]
    modules = packs["modules"].get("module_candidates", [])
    cycle_modules = cycle_module_set(dep)
    result = []
    for idx, module in enumerate(modules, start=1):
        evidence = [
            evidence_ref(file, None, "module candidate source file")
            for file in module.get("evidence_files", [])[:12]
        ]
        responsibility = infer_module_responsibility(module)
        result.append(
            {
                "module_id": f"MOD-{idx:03d}",
                "name": module["name"],
                "responsibility": responsibility,
                "source_folders": module.get("source_folders", []),
                "main_components": module.get("components", [])[:25],
                "entry_points": module.get("entry_points", []),
                "depends_on_modules": module.get("depends_on", []),
                "depended_on_by_modules": module.get("depended_on_by", []),
                "afferent_coupling": module.get("afferent_coupling", 0),
                "efferent_coupling": module.get("efferent_coupling", 0),
                "boundary_quality": boundary_quality(module, cycle_modules),
                "migration_readiness": migration_readiness(module, cycle_modules),
                "confidence": module.get("confidence", 0.0),
                "evidence": evidence,
                "open_questions": module.get("open_questions", []),
            }
        )
    return {
        "generated_at": utc_now(),
        "source_evidence_pack": "architecture-output/evidence-packs/module-boundary-pack.json",
        "modules": result,
        "open_questions": packs["modules"].get("open_questions", []),
    }


def risk_flags_for_component(component: dict[str, Any], high_names: set[str], violation_components: set[str]) -> list[str]:
    flags = []
    if component.get("name") in high_names:
        flags.append("high_coupling")
    if component.get("name") in violation_components:
        flags.append("architecture_violation")
    if component.get("module_guess") == "Unknown":
        flags.append("unknown_module")
    if component.get("type") == "Unknown" or component.get("layer") == "Unknown":
        flags.append("unknown_classification")
    return flags


def build_component_registry(packs: dict[str, Any]) -> dict[str, Any]:
    components = packs["components"].get("components", [])
    high_names = {item["name"] for item in packs["dependencies"].get("high_coupling_candidates", {}).get("components", [])}
    violation_components = set()
    for violation in packs["layering"].get("layer_violations", []):
        violation_components.update(violation.get("affected_components", []))
    records = []
    for component in components:
        records.append(
            {
                "component_id": component.get("component_id"),
                "name": component.get("name"),
                "type": component.get("type", component.get("component_type", "Unknown")),
                "layer": component.get("layer", component.get("layer_guess", "Unknown")),
                "module": component.get("module_guess", "Unknown"),
                "project": component.get("project", "unknown"),
                "parser_backend": component.get("parser_backend", "unknown"),
                "semantic_symbol_id": component.get("semantic_symbol_id"),
                "semantic_full_name": component.get("semantic_full_name"),
                "semantic_parser_backend": component.get("semantic_parser_backend"),
                "semantic_methods": component.get("semantic_methods", []),
                "semantic_constructor_dependencies": component.get("semantic_constructor_dependencies", []),
                "semantic_confidence": component.get("semantic_confidence"),
                "architecture_significance": component.get("architecture_significance", "UnclassifiedCandidate"),
                "is_major_application_component": component.get("is_major_application_component", True),
                "architecture_significance_reason": component.get("architecture_significance_reason"),
                "file": component.get("file"),
                "source_chunks": component.get("source_chunks", []),
                "public_methods": component.get("public_methods", []),
                "dependencies": component.get("dependencies", []),
                "risk_flags": risk_flags_for_component(component, high_names, violation_components),
                "confidence": component.get("confidence", 0.0),
                "evidence": component.get("evidence", []),
            }
        )
    return {
        "generated_at": utc_now(),
        "source_evidence_pack": "architecture-output/evidence-packs/component-registry-pack.json",
        "summary": packs["components"].get("extracted_facts", {}),
        "components": records,
        "open_questions": packs["components"].get("open_questions", []),
    }


def build_dependency_graph(packs: dict[str, Any]) -> dict[str, Any]:
    components = packs["components"].get("components", [])
    modules = packs["modules"].get("module_candidates", [])
    dep_pack = packs["dependencies"]
    external = packs["external"].get("external_dependencies", [])
    nodes = []
    for component in components:
        nodes.append(
            {
                "id": component.get("name"),
                "type": "component",
                "module": component.get("module_guess", "Unknown"),
                "layer": component.get("layer", component.get("layer_guess", "Unknown")),
                "file": component.get("file"),
            }
        )
    for module in modules:
        nodes.append({"id": module["name"], "type": "module", "module": module["name"], "layer": "Unknown"})
    for item in external:
        nodes.append({"id": item.get("target_system"), "type": "external_system", "module": item.get("module_guess", "unknown"), "layer": "External"})

    edges = []
    for edge in dep_pack.get("component_dependencies", []):
        edges.append(
            {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "relationship": edge.get("relationship", "uses"),
                "kind": edge.get("kind"),
                "dependency_id": edge.get("dependency_id"),
                "evidence": edge.get("evidence"),
                "source_file": edge.get("source_file"),
                "line": edge.get("line"),
                "confidence": edge.get("confidence", 0.0),
            }
        )
    for edge in dep_pack.get("module_dependencies", []):
        edges.append(
            {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "relationship": "uses",
                "evidence": edge.get("evidence"),
                "source_file": edge.get("source_file"),
                "line": edge.get("line"),
                "confidence": edge.get("confidence", 0.0),
            }
        )
    for item in external:
        for ev in item.get("evidence", [])[:1]:
            edges.append(
                {
                    "from": item.get("called_from", "unknown"),
                    "to": item.get("target_system", "unknown"),
                    "relationship": "calls" if item.get("protocol") == "HTTP" else "uses",
                    "evidence": ev.get("reason", "external boundary evidence"),
                    "source_file": ev.get("file"),
                    "line": ev.get("line"),
                    "confidence": item.get("confidence", 0.0),
                }
            )

    existing_node_ids = {node.get("id") for node in nodes}
    for edge in edges:
        for endpoint_key in ("from", "to"):
            endpoint = edge.get(endpoint_key)
            if endpoint in (None, "", "unknown") or endpoint in existing_node_ids:
                continue
            nodes.append(
                {
                    "id": endpoint,
                    "type": "external_system",
                    "module": "unknown",
                    "layer": "External",
                    "file": edge.get("source_file"),
                    "inferred_from": "dependency edge endpoint not resolved to a local component or module",
                }
            )
            existing_node_ids.add(endpoint)
    return {
        "generated_at": utc_now(),
        "source_evidence_pack": "architecture-output/evidence-packs/dependency-pack.json",
        "nodes": nodes,
        "edges": edges,
        "cycles": dep_pack.get("cycles", {}),
        "high_coupling_components": dep_pack.get("high_coupling_candidates", {}).get("components", []),
        "high_coupling_modules": dep_pack.get("high_coupling_candidates", {}).get("modules", []),
        "open_questions": dep_pack.get("open_questions", []),
    }


def interface_visibility(entry: dict[str, Any]) -> str:
    path = str(entry.get("path_or_name", "")).lower()
    kind = entry.get("type")
    if kind == "FrontendRoute":
        return "user_facing"
    if path.startswith("/api/"):
        return "external_system"
    if kind == "CLI":
        return "internal"
    return "user_facing" if path.startswith("/") else "unknown"


def build_interface_catalogue(packs: dict[str, Any]) -> dict[str, Any]:
    interfaces = []
    for idx, entry in enumerate(packs["entry_points"].get("entry_points", []), start=1):
        interfaces.append(
            {
                "interface_id": f"INT-{idx:03d}",
                "type": entry.get("type", "Unknown"),
                "method": entry.get("method", "unknown"),
                "path_or_name": entry.get("path_or_name", "unknown"),
                "owner_module": entry.get("owning_module_guess", "Unknown"),
                "entry_component": entry.get("owning_component", "unknown"),
                "called_service": entry.get("called_service_or_handler", []),
                "visibility": interface_visibility(entry),
                "source_file": entry.get("source_file"),
                "line": entry.get("line"),
                "source_chunks": entry.get("source_chunks", []),
                "parser_strategy": entry.get("parser_strategy", "unknown"),
                "route_action": entry.get("route_action", "unknown"),
                "confidence": entry.get("confidence", 0.0),
                "evidence": entry.get("evidence", []),
                "open_questions": entry.get("uncertainty", []),
            }
        )
    return {
        "generated_at": utc_now(),
        "source_evidence_pack": "architecture-output/evidence-packs/entry-point-pack.json",
        "summary": packs["entry_points"].get("extracted_facts", {}),
        "interfaces": interfaces,
        "open_questions": packs["entry_points"].get("open_questions", []),
    }


def build_call_flow_map(packs: dict[str, Any]) -> dict[str, Any]:
    flows = []
    for flow in packs["flows"].get("flows", []):
        risk_flags = []
        if flow.get("status") == "partial":
            risk_flags.append("partial_flow")
        if (
            not flow.get("data_access_components")
            and flow.get("entry_point_type") == "HTTP_API"
            and flow.get("status") not in {"framework_route_coverage_marker", "single_component_page_flow_mapped"}
        ):
            risk_flags.append("data_access_not_resolved")
        flows.append(
            {
                "flow_id": flow.get("flow_id"),
                "name": flow.get("entry_point"),
                "entry_point": flow.get("entry_point"),
                "entry_point_type": flow.get("entry_point_type"),
                "status": flow.get("status"),
                "steps": [
                    {
                        "step": step.get("step"),
                        "component": step.get("component"),
                        "layer": step.get("layer"),
                        "module": step.get("module"),
                        "action": step.get("operation", "unknown"),
                        "file": step.get("file"),
                        "source_chunks": step.get("source_chunks", []),
                        "evidence": step.get("evidence"),
                    }
                    for step in flow.get("steps", [])
                ],
                "modules_touched": flow.get("modules_touched", []),
                "external_systems_touched": flow.get("external_systems_touched", []),
                "data_access_components": flow.get("data_access_components", []),
                "semantic_step_count": flow.get("semantic_step_count", 0),
                "risk_flags": risk_flags,
                "confidence": flow.get("confidence", 0.0),
                "open_questions": flow.get("open_questions", []),
            }
        )
    return {
        "generated_at": utc_now(),
        "source_evidence_pack": "architecture-output/evidence-packs/call-flow-pack.json",
        "summary": packs["flows"].get("extracted_facts", {}),
        "flows": flows,
        "open_questions": packs["flows"].get("open_questions", []),
    }


def build_violations(packs: dict[str, Any]) -> list[dict[str, Any]]:
    violations = []
    layer_violations = packs["layering"].get("layer_violations", [])
    grouped_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in layer_violations:
        key = item.get("type", "layer_violation") + ":" + ",".join(item.get("affected_components", []))
        grouped_layer[key].append(item)
    for items in grouped_layer.values():
        first = items[0]
        violations.append(
            {
                "violation_id": f"ARCH-VIOL-{len(violations)+1:03d}",
                "type": "layer_violation",
                "description": first.get("description"),
                "file": first.get("source_file", "unknown"),
                "affected_components": first.get("affected_components", []),
                "affected_modules": modules_for_components(packs, first.get("affected_components", [])),
                "severity": first.get("severity", "Medium"),
                "migration_impact": "This dependency should be reviewed before extracting or rewriting the affected UI/API flow.",
                "recommendation": "Route the flow through an application service or query abstraction before forward engineering.",
                "confidence": first.get("confidence", 0.0),
                "evidence": [evidence_ref(item.get("source_file"), item.get("line"), item.get("evidence")) for item in items],
            }
        )
    for cycle in packs["dependencies"].get("cycles", {}).get("module_cycles", []):
        violations.append(
            {
                "violation_id": f"ARCH-VIOL-{len(violations)+1:03d}",
                "type": "circular_dependency",
                "description": "Module dependency cycle detected: " + " -> ".join(cycle.get("cycle", [])),
                "file": "unknown",
                "affected_components": [],
                "affected_modules": cycle.get("cycle", []),
                "severity": cycle.get("severity", "High"),
                "migration_impact": "Modules in the cycle are poor early extraction candidates until dependency direction is clarified.",
                "recommendation": "Review cycle edges and introduce clearer application/service contracts before extraction.",
                "confidence": cycle.get("confidence", 0.0),
                "evidence": [{"file": "architecture-output/evidence-packs/dependency-pack.json", "reason": "module cycle detected from dependency evidence pack"}],
            }
        )
    for item in packs["dependencies"].get("high_coupling_candidates", {}).get("components", [])[:2]:
        violations.append(
            {
                "violation_id": f"ARCH-VIOL-{len(violations)+1:03d}",
                "type": "high_coupling",
                "description": f"Component {item['name']} has high coupling score {item['total_coupling']}.",
                "file": "unknown",
                "affected_components": [item["name"]],
                "affected_modules": [],
                "severity": "Medium",
                "migration_impact": "Changing or extracting this component may affect multiple flows.",
                "recommendation": "Review inbound/outbound dependencies before redesign.",
                "confidence": item.get("confidence", 0.0),
                "evidence": [{"file": "architecture-output/evidence-packs/dependency-pack.json", "reason": "high coupling candidate"}],
            }
        )
    return violations


def modules_for_components(packs: dict[str, Any], component_names: list[str]) -> list[str]:
    modules = []
    for component in packs["components"].get("components", []):
        if component.get("name") in component_names:
            modules.append(component.get("module_guess", "Unknown"))
    return unique(modules)


def build_architecture_violation_register(packs: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "source_evidence_packs": [
            "architecture-output/evidence-packs/layering-pattern-pack.json",
            "architecture-output/evidence-packs/dependency-pack.json",
        ],
        "violations": build_violations(packs),
    }


def build_risk_register(packs: dict[str, Any], violations: list[dict[str, Any]]) -> dict[str, Any]:
    dep = packs["dependencies"]
    mod = packs["modules"]
    comp = packs["components"]
    flows = packs["flows"]
    risks = []

    def add(category: str, description: str, module: str, component: str, severity: str, impact: str, evidence: list[dict[str, Any]], recommendation: str, confidence: float) -> None:
        risks.append(
            {
                "risk_id": f"APP-RISK-{len(risks)+1:03d}",
                "category": category,
                "description": description,
                "affected_module": module,
                "affected_component": component,
                "severity": severity,
                "forward_engineering_impact": impact,
                "evidence": evidence,
                "recommendation": recommendation,
                "confidence": confidence,
            }
        )

    module_candidates = mod.get("module_candidates", [])
    weak_candidates = sorted(
        [
            item for item in module_candidates
            if item.get("confidence", 0.0) < 0.7
            or int(item.get("afferent_coupling", 0)) + int(item.get("efferent_coupling", 0)) >= 5
        ],
        key=lambda item: int(item.get("afferent_coupling", 0)) + int(item.get("efferent_coupling", 0)),
        reverse=True,
    )
    if weak_candidates:
        top = weak_candidates[0]
        add(
            "unclear_boundary",
            f"Module candidate {top.get('name', 'unknown')} has weak or uncertain boundary evidence with coupling score {int(top.get('afferent_coupling', 0)) + int(top.get('efferent_coupling', 0))}.",
            top.get("name", "unknown"),
            "unknown",
            "High",
            "Forward engineering could create artificial service boundaries or duplicate responsibilities if this candidate boundary is accepted without review.",
            [{"file": "architecture-output/evidence-packs/module-boundary-pack.json", "reason": "weak or high-coupling module candidate"}],
            "Confirm module ownership, public interfaces, and dependency direction before using this candidate as a modernization boundary.",
            float(top.get("confidence", 0.0)),
        )
    for cycle in dep.get("cycles", {}).get("module_cycles", []):
        add(
            "circular_dependency",
            "Module dependency cycle detected: " + " -> ".join(cycle.get("cycle", [])),
            ", ".join(cycle.get("cycle", [])),
            "unknown",
            "High",
            "Cycle participants are risky extraction candidates until dependency direction and ownership are clarified.",
            [{"file": "architecture-output/evidence-packs/dependency-pack.json", "reason": "module cycle evidence"}],
            "Review cycle edges and break the cycle with clearer contracts or orchestration boundaries.",
            cycle.get("confidence", 0.0),
        )
    high_modules = dep.get("high_coupling_candidates", {}).get("modules", [])[:5]
    if high_modules:
        add(
            "high_coupling",
            "High-coupling module candidates include " + short_list([item["name"] for item in high_modules], 5) + ".",
            "multiple",
            "unknown",
            "High",
            "High-coupling modules are poor first extraction candidates and need dependency review before rewrite.",
            [{"file": "architecture-output/evidence-packs/dependency-pack.json", "reason": "high coupling module candidates"}],
            "Start modernization with lower-coupled modules and treat these as later-stage candidates.",
            max(float(item.get("confidence", 0.0)) for item in high_modules),
        )
    high_components = dep.get("high_coupling_candidates", {}).get("components", [])
    if high_components:
        top_component = high_components[0]
        add(
            "shared_dependency",
            f"{top_component.get('name', 'unknown')} is a high-coupling component candidate with total coupling {top_component.get('total_coupling', 'unknown')}.",
            top_component.get("module_guess", "unknown"),
            top_component.get("name", "unknown"),
            "High",
            "Shared high-coupling components can make migration sequencing and replacement risky.",
            [{"file": "architecture-output/evidence-packs/dependency-pack.json", "reason": "high coupling component candidate"}],
            "Map consumers and ownership before extracting modules that depend on this component.",
            float(top_component.get("confidence", 0.0)),
        )
    partial_count = flows.get("extracted_facts", {}).get("partial_flow_count", 0)
    add(
        "unknown",
        f"{partial_count} call flows are partial because parsed evidence did not fully resolve runtime dispatch and downstream calls.",
        "multiple",
        "unknown",
        "Medium",
        "Forward engineering may miss behavior unless partial flows are reviewed against source/tests.",
        [{"file": "architecture-output/evidence-packs/call-flow-pack.json", "reason": "partial flow count"}],
        "Prioritize manual flow review for high-value user-facing and externally visible flows before implementation.",
        0.56,
    )
    frontend_apps = packs["frontend"].get("frontend_apps", [])
    api_call_count = sum(len(app.get("api_calls", [])) for app in frontend_apps)
    if api_call_count:
        app_names = [app.get("name", "unknown") for app in frontend_apps]
        add(
            "frontend_backend_coupling",
            f"Frontend application evidence contains {api_call_count} API call mappings from {short_list(app_names, 4)}.",
            "multiple",
            "unknown",
            "Medium",
            "Frontend/backend contract changes may break detected UI workflows.",
            [{"file": "architecture-output/evidence-packs/frontend-application-pack.json", "reason": "frontend API call mapping"}],
            "Preserve or explicitly redesign detected frontend/API contracts during forward engineering.",
            float(packs["frontend"].get("confidence", 0.0)),
        )
    for violation in violations:
        if violation["type"] == "layer_violation":
            add(
                "unknown",
                violation["description"],
                short_list(violation.get("affected_modules", []), 4),
                short_list(violation.get("affected_components", []), 4),
                "Medium",
                "This dependency should not be copied into the future design without review.",
                violation.get("evidence", []),
                violation["recommendation"],
                violation.get("confidence", 0.0),
            )
            break
    add(
        "unclear_boundary",
        f"{mod.get('extracted_facts', {}).get('components_with_unknown_module', 0)} components have unknown module ownership and {comp.get('extracted_facts', {}).get('components_by_type', {}).get('Unknown', 0)} components have unknown type classification.",
        "unknown",
        "unknown",
        "Medium",
        "Unknown ownership can hide shared responsibilities or dead code candidates.",
        [{"file": "architecture-output/evidence-packs/component-registry-pack.json", "reason": "unknown component/module classification counts"}],
        "Review Unknown components before finalizing service/module boundaries.",
        0.7,
    )
    external_dependencies = packs["external"].get("external_dependencies", [])
    if external_dependencies:
        targets = unique([item.get("target_system", "unknown") for item in external_dependencies])[:5]
        add(
            "integration_scatter",
            "External dependency candidates include " + short_list(targets, 5) + "; target purposes may require review.",
            "multiple",
            "unknown",
            "Medium",
            "Unclear integration purpose can block environment setup and contract preservation in forward engineering.",
            [{"file": "architecture-output/evidence-packs/external-boundary-pack.json", "reason": "external dependency open questions"}],
            "Confirm each external boundary purpose and runtime ownership before implementation planning.",
            float(packs["external"].get("confidence", 0.0)),
        )
    return {"generated_at": utc_now(), "risks": risks}


def candidate_score(module: dict[str, Any], cycle_modules: set[str], external_risk: bool = False) -> tuple[str, int, str]:
    total = int(module.get("afferent_coupling", 0)) + int(module.get("efferent_coupling", 0))
    has_entry = len(module.get("entry_points", [])) > 0
    if module["name"] in cycle_modules or total >= 6:
        return ("Poor Candidate", 20, "cycle or high coupling")
    if int(module.get("efferent_coupling", 0)) <= 1 and has_entry:
        return ("Good Early Candidate", 90, "clear public entry point with low efferent coupling")
    if total <= 2:
        return ("Possible Candidate With Refactoring", 70, "low coupling but public interface or ownership needs review")
    return ("Possible Candidate With Refactoring", 55, "moderate coupling")


def build_strangler_report(packs: dict[str, Any], module_map: dict[str, Any], risk_register: dict[str, Any]) -> str:
    cycle_modules = cycle_module_set(packs["dependencies"])
    rows = []
    for module in module_map["modules"]:
        ranking, score, reason = candidate_score(module, cycle_modules)
        rows.append((ranking, score, reason, module))
    rows.sort(key=lambda item: item[1], reverse=True)
    good = [item for item in rows if item[0] == "Good Early Candidate"]
    medium = [item for item in rows if item[0] == "Possible Candidate With Refactoring"]
    poor = [item for item in rows if item[0] == "Poor Candidate"]
    module_edges = packs["dependencies"].get("module_dependencies", [])
    risks = risk_register.get("risks", [])

    def dependency_refs(module_name: str) -> list[str]:
        refs = []
        for idx, edge in enumerate(module_edges, start=1):
            if module_name in {edge.get("from"), edge.get("to")}:
                refs.append(f"DEP-{idx:04d}")
            if len(refs) >= 4:
                break
        return refs

    def risk_refs(module_name: str) -> list[str]:
        refs = []
        for risk in risks:
            affected = str(risk.get("affected_module", ""))
            if module_name in affected or affected in {"multiple", "unknown"}:
                refs.append(risk.get("risk_id", "unknown"))
            if len(refs) >= 4:
                break
        return refs

    def evidence_summary(module: dict[str, Any]) -> str:
        files = source_file_list(module.get("evidence", []), 3)
        refs = [module.get("module_id", "unknown")]
        refs.extend(
            comp.get("component_id")
            for comp in module.get("main_components", [])[:4]
            if comp.get("component_id")
        )
        refs.extend(dependency_refs(module["name"]))
        refs.extend(risk_refs(module["name"]))
        if files:
            refs.append("files: " + short_list(files, 3))
        return "; ".join(refs)

    def table(items: list[tuple[str, int, str, dict[str, Any]]]) -> str:
        lines = ["| Module | Score | Coupling | Boundary | External Risk | Reason | Evidence refs |", "|---|---:|---:|---|---|---|---|"]
        for _, score, reason, module in items:
            coupling = int(module["afferent_coupling"]) + int(module["efferent_coupling"])
            external = "review" if risk_refs(module["name"]) else "low/unknown"
            lines.append(f"| {module['name']} | {score} | {coupling} | {module['boundary_quality']} | {external} | {reason} | {evidence_summary(module)} |")
        return "\n".join(lines)

    order = [item[3]["name"] for item in good[:4] + medium[:5]]
    good_names = [item[3]["name"] for item in good]
    poor_names = [item[3]["name"] for item in poor]
    return f"""# Strangler Candidate Report

Generated from source-backed evidence packs. This report ranks candidates for future extraction or modernization; it does not choose a future technology stack.

## 1. Best Early Extraction/Migration Candidates

{table(good) if good else "No module met the Good Early Candidate rule from current evidence."}

## 2. Medium-Risk Candidates

{table(medium)}

## 3. Poor Candidates

{table(poor)}

## 4. Reasoning

Best early candidates have low efferent coupling and observable interfaces. Current best candidates from evidence are: {short_list(good_names)}.

Poor candidates are riskier because dependency evidence reports high coupling, weak/unknown boundaries, and/or module-cycle participation. Current poor candidates from evidence are: {short_list(poor_names)}.

## 5. Coupling Score

Coupling score here is afferent plus efferent module coupling from `dependency-pack.json`. High values make first extraction riskier.

## 6. Boundary Clarity

Boundary quality is strongest where source folders, entry points, and dependency counts line up. Boundaries are weak where a module spans many folders, participates in cycles, or has high coupling.

## 7. External Dependency Risk

External dependency risk is derived from `external-boundary-pack.json`, module risk references, and dependency evidence. Modules marked `review` in the table have associated risk IDs or dependency evidence that should be checked before extraction.

## 8. Suggested Migration Order

1. {order[0] if len(order) > 0 else "unknown"}
2. {order[1] if len(order) > 1 else "unknown"}
3. {order[2] if len(order) > 2 else "unknown"}
4. {order[3] if len(order) > 3 else "unknown"}
5. Defer high-coupling/cyclic modules: {short_list([item[3]["name"] for item in poor], 8)}

Human review is required before final sequencing because some call flows are partial and some module boundaries are candidate-only.
"""


def build_forward_map(packs: dict[str, Any], module_map: dict[str, Any], risks: dict[str, Any]) -> str:
    interfaces = packs["entry_points"].get("entry_points", [])
    components = packs["components"].get("components", [])
    component_ids = {component.get("name"): component.get("component_id") for component in components}
    module_edges = packs["dependencies"].get("module_dependencies", [])
    module_ids = {module["name"]: module.get("module_id", "unknown") for module in module_map["modules"]}

    def component_ref(name: Any) -> str:
        if not name or str(name).lower() == "unknown":
            return "unknown"
        clean = str(name).split(".", 1)[0].strip()
        return f"{component_ids.get(clean, 'COMP-unknown')} {name}"

    def component_refs(value: Any) -> str:
        if isinstance(value, list):
            names = value
        else:
            names = [item.strip() for item in str(value or "").split(",")]
        refs = [component_ref(name) for name in names if name and str(name).lower() != "unknown"]
        return short_list(refs, 4) if refs else "unknown"

    def dependency_refs_for_modules(module_value: Any) -> str:
        modules = [item.strip() for item in str(module_value or "").split(",") if item.strip()]
        if not modules or modules[0] in {"unknown", "multiple"}:
            modules = [module["name"] for module in module_map["modules"][:5]]
        refs = []
        for idx, edge in enumerate(module_edges, start=1):
            if edge.get("from") in modules or edge.get("to") in modules:
                refs.append(f"DEP-{idx:04d}")
            if len(refs) >= 4:
                break
        return short_list(refs, 4)

    api_rows = [
        f"- {i.get('method')} {i.get('path_or_name')} (owner: {component_ref(i.get('owning_component', 'unknown'))}; module: {module_ids.get(i.get('owning_module_guess'), 'MOD-unknown')} {i.get('owning_module_guess', 'Unknown')}; file: {i.get('source_file', 'unknown')})"
        for i in interfaces
        if i.get("type") == "HTTP_API"
    ][:20]
    traced = [flow for flow in packs["flows"].get("flows", []) if flow.get("status") != "partial"]
    partial = packs["flows"].get("extracted_facts", {}).get("partial_flow_count", 0)
    ready = [m["name"] for m in module_map["modules"] if m["migration_readiness"] == "Ready"]
    review = [m["name"] for m in module_map["modules"] if m["migration_readiness"] in {"Blocked", "Unknown"}]
    ready_with_ids = [f"{module_ids.get(name, 'unknown')} {name}" for name in ready]
    review_with_ids = [f"{module_ids.get(name, 'unknown')} {name}" for name in review]
    traced_rows = [
        f"- {flow.get('entry_point')} (status: {flow.get('status', 'unknown')}; confidence: {flow.get('confidence', 0.0)})"
        for flow in traced[:10]
    ]
    risk_rows = [
        f"- {risk['risk_id']}: {risk['description']} (module: {risk.get('affected_module', 'unknown')}; components: {component_refs(risk.get('affected_component', 'unknown'))}; dependency refs: {dependency_refs_for_modules(risk.get('affected_module', 'unknown'))}; evidence: {short_list(source_file_list(risk.get('evidence', []), 3), 3)})"
        for risk in risks["risks"][:8]
    ]
    not_carry = [
        risk for risk in risks["risks"]
        if risk.get("category") in {"circular_dependency", "shared_dependency", "high_coupling", "unclear_boundary", "frontend_backend_coupling", "unknown"}
    ][:6]
    first_candidates = ready_with_ids[:5]
    return f"""# Forward Engineering Input Map

Generated from evidence packs only. This is application-architecture input for future design, not a future technology decision.

## 1. Candidate Future Modules/Services

Ready or lower-risk candidates from current evidence: {short_list(ready_with_ids, 10)}.

Modules needing refactoring or review before becoming separate services: {short_list(review_with_ids, 12)}.

## 2. Existing APIs To Preserve Or Redesign

Preserve behavior or explicitly redesign these detected interfaces:

{chr(10).join(api_rows) if api_rows else "- none detected"}

## 3. Call Flows To Preserve Behaviorally

Evidence contains {len(traced)} traced-from-dependency-candidate flows and {partial} partial flows.

Traced flows with evidence:

{chr(10).join(traced_rows) if traced_rows else "- No fully traced flows detected; use `call-flow-map.json` partial flows for review."}

## 4. Architecture Violations Not To Carry Forward

Do not blindly carry forward these risk-backed concerns:

{chr(10).join(f"- {risk['risk_id']}: {risk['description']}" for risk in not_carry) if not_carry else "- none detected"}

## 5. Risks To Resolve Before Implementation

{chr(10).join(risk_rows)}

## 6. Modules Needing Deeper Review

{short_list(review_with_ids, 16)}

## 7. Suggested First Modernization Candidates

Start with low-coupled, evidence-backed candidates: {short_list(first_candidates, 8)}. Defer blocked or unknown-readiness modules until cycles, shared dependencies, and call-flow gaps are reviewed.
"""


def build_open_questions(packs: dict[str, Any], module_map: dict[str, Any], call_flow_map: dict[str, Any]) -> list[str]:
    weak_modules = [
        module["name"] for module in module_map["modules"]
        if module.get("boundary_quality") in {"Weak", "Unknown"}
    ]
    cycle_descriptions = [
        " -> ".join(cycle.get("cycle", []))
        for cycle in packs["dependencies"].get("cycles", {}).get("module_cycles", [])
    ]
    frontend_apps = [app.get("name", "unknown") for app in packs["frontend"].get("frontend_apps", [])]
    external_targets = unique([item.get("target_system", "unknown") for item in packs["external"].get("external_dependencies", [])])[:5]
    unknown_modules = packs["modules"].get("extracted_facts", {}).get("components_with_unknown_module", 0)
    unknown_types = packs["components"].get("extracted_facts", {}).get("components_by_type", {}).get("Unknown", 0)
    entry_counts = packs["entry_points"].get("extracted_facts", {}).get("entry_points_by_type", {})
    questions = [
        "Confirm the authoritative system name; evidence packs leave system_name as unknown.",
        "Confirm ownership and boundaries for weak or unknown module candidates: " + short_list(weak_modules, 10) + ".",
        f"Review the {unknown_modules} components with unknown module ownership before finalizing module boundaries.",
        f"Review the {unknown_types} components with Unknown type/layer classification to decide whether they are architecture-significant.",
        f"Review {call_flow_map['summary'].get('partial_flow_count', 0)} partial call flows before using them as behavior-preservation contracts.",
        "Confirm whether detected module cycles are real architecture cycles or artifacts of static dependency resolution: " + short_list(cycle_descriptions, 3) + ".",
        "Confirm deployment ownership for detected frontend applications: " + short_list(frontend_apps, 5) + ".",
        "Confirm whether detected database/infrastructure services are development-only or production-relevant external boundaries.",
        "Confirm the target systems and purposes behind configured HTTP/API base URLs and health-check dependencies: " + short_list(external_targets, 5) + ".",
        "Confirm whether no scheduled jobs/message consumers exist; none were detected in parsed facts.",
        f"Confirm controller and route coverage for convention-based framework routes, because extraction found {entry_counts.get('HTTP_API', 0)} HTTP APIs, {entry_counts.get('FrontendRoute', 0)} frontend routes, and partial call flows but cannot prove complete runtime route coverage without framework execution.",
        "Review generated/migration source exclusions before relying on this package for database migration planning.",
        "Confirm whether test-project components should be retained in final architecture evidence or filtered from enterprise application views.",
    ]
    return questions


def build_markdown_summary(packs: dict[str, Any], system_inventory: dict[str, Any], module_map: dict[str, Any], dep_graph: dict[str, Any], risk_register: dict[str, Any], open_questions: list[str]) -> str:
    deployables = [unit["name"] for unit in system_inventory.get("deployable_units", [])]
    applications = system_inventory.get("applications", [])
    modules = module_map["modules"]
    top_modules = sorted(modules, key=lambda m: len(m["main_components"]), reverse=True)[:8]
    layer_counts = packs["components"].get("extracted_facts", {}).get("components_by_layer", {})
    entry_counts = packs["entry_points"].get("extracted_facts", {}).get("entry_points_by_type", {})
    high_modules = [m["name"] for m in dep_graph.get("high_coupling_modules", [])[:6]]
    primary_pattern = best_pattern(packs)
    secondary = secondary_patterns(packs, primary_pattern)
    source_anchors = project_source_files(
        system_inventory.get("deployable_units", [])
        + system_inventory.get("frontend_projects", [])
        + system_inventory.get("supporting_projects", [])
        + system_inventory.get("database_support_projects", []),
        8,
    )
    representative_modules = []
    for module in top_modules[:5]:
        files = source_file_list(module.get("evidence", []), 1)
        representative_modules.append(f"{module['name']} uses {files[0] if files else 'unknown source evidence'}")
    api_examples = [
        f"{entry.get('method')} {entry.get('path_or_name')}"
        for entry in packs["entry_points"].get("entry_points", [])
        if entry.get("type") == "HTTP_API"
    ][:8]
    frontend_routes = [
        str(entry.get("path_or_name"))
        for entry in packs["entry_points"].get("entry_points", [])
        if entry.get("type") == "FrontendRoute"
    ][:5]
    high_components = [c["name"] for c in dep_graph.get("high_coupling_components", [])[:5]]
    ready = [m["name"] for m in modules if m.get("migration_readiness") == "Ready"]
    blocked = [m["name"] for m in modules if m.get("migration_readiness") in {"Blocked", "Unknown"}]
    return f"""# Application Architecture Summary

## 1. System Overview

The repository contains {len(applications)} detected application/support project records and {len(deployables)} deployable unit candidates. The authoritative system name is unknown in the evidence, so final artifacts keep `system_name` as `unknown`.

Evidence: `system-inventory-pack.json` detects {len(system_inventory['applications'])} projects and deployable units {short_list(deployables)}.

Source anchors: {short_list(source_anchors, 8)}.

## 2. Detected Application Style

Detected style: {primary_pattern.get('pattern', 'Unknown')}. Secondary candidates: {short_list([item.get('pattern', 'Unknown') for item in secondary], 4)}. The pattern statement is based on project/deployable evidence and detected component layers.

## 3. Deployable Units

Deployable units detected: {short_list(deployables)}. Deployment/build clues are retained in `system-inventory.json` and `system-inventory-pack.json`.

## 4. Main Modules

Module candidates are evidence-derived, not final business-owned bounded contexts. Largest candidates by component count:

{chr(10).join(f"- {m['name']}: {len(m['main_components'])} components, {len(m['entry_points'])} entry points, boundary {m['boundary_quality']}" for m in top_modules)}

Representative module evidence: {short_list(representative_modules, 5)}.

## 5. Main Layers

Detected layer counts: {json.dumps(layer_counts, sort_keys=True)}.

## 6. Main Interfaces

Entry points detected: {json.dumps(entry_counts, sort_keys=True)}. Representative HTTP APIs: {short_list(api_examples, 8)}. Representative frontend routes: {short_list(frontend_routes, 5)}.

Representative interface evidence is retained in `application-interface-catalogue.json` and `entry-point-pack.json`.

## 7. Major Dependencies

Dependency evidence contains {len(dep_graph['edges'])} graph edges. High-coupling modules include {short_list(high_modules)}. High-coupling components include {short_list(high_components)}.

## 8. Architecture Pattern

Primary pattern: {primary_pattern.get('pattern', 'Unknown')} with confidence {primary_pattern.get('confidence', 0.0)}. Service separation is not claimed unless deployable and dependency evidence supports it.

Pattern evidence anchors: {short_list(source_anchors, 8)}.

## 9. Architecture Risks

Top risks:

{chr(10).join(f"- {risk['risk_id']}: {risk['description']}" for risk in risk_register['risks'][:6])}

## 10. Migration/Forward-Engineering Implications

Start with lower-coupled candidates: {short_list(ready, 8)}. Defer blocked or unknown-readiness candidates until module boundaries, dependency direction, and call-flow gaps are reviewed: {short_list(blocked, 10)}.

## 11. Open Questions Summary

There are {len(open_questions)} open questions. The most important are system name, candidate module boundaries, route/call-flow coverage, partial call flows, module cycles, and external boundary ownership.
"""


def build_pattern_report(packs: dict[str, Any], violations: dict[str, Any]) -> str:
    candidates = packs["layering"].get("candidate_patterns", [])
    layers = packs["layering"].get("detected_layers", [])
    primary = best_pattern(packs)
    source_files = packs["system"].get("source_files_used", [])[:10]
    violation_files = unique(
        [
            ev.get("file", "unknown")
            for violation in violations.get("violations", [])
            for ev in violation.get("evidence", [])
        ]
    )[:8]
    return f"""# Architecture Pattern Report

## 1. Detected Architecture Pattern

Detected pattern: {primary.get('pattern', 'Unknown')}.

## 2. Evidence

- Candidate pattern evidence from layering pack: {json.dumps(candidates, indent=2)}
- System inventory detects {packs['system'].get('extracted_facts', {}).get('deployable_unit_count', 0)} deployable unit candidates and {packs['system'].get('extracted_facts', {}).get('project_count', 0)} project records.
- Component evidence detects layers across Presentation/UI, API, Application, Domain, Infrastructure, DataAccess, Integration, CrossCutting, and Unknown.

Source file anchors:

{md_list(source_files[:8])}

## 3. Layer Structure

{chr(10).join(f"- {layer['layer']}: {layer['component_count']} components" for layer in layers)}

## 4. Pattern Confidence

Primary pattern confidence is {primary.get('confidence', 0.0)}. Competing pattern candidates and confidence scores are shown in the evidence block above, so this is an evidence-bounded observation rather than a pure pattern claim.

## 5. Pattern Violations

{chr(10).join(f"- {v['violation_id']}: {v['description']}" for v in violations['violations'])}

Violation source anchors: {short_list(violation_files, 8)}. Dependency-cycle and high-coupling claims are derived from `architecture-output/evidence-packs/dependency-pack.json`, which preserves source-file evidence for the underlying component and module dependency candidates.

## 6. What This Means For Reverse Engineering

Reverse engineering should preserve the project/layer split in the evidence model and treat module boundaries as candidates, not confirmed bounded contexts. Repository sharing and module cycles should be analyzed before deriving modernization slices.

## 7. What This Means For Forward Engineering

Forward engineering should preserve externally visible API behavior and important UI flows, but should not copy direct UI/API-to-data-access dependencies or unresolved module cycles. The future design should clarify candidate module boundaries and data-access ownership first.
"""


def build_diagrams(packs: dict[str, Any], module_map: dict[str, Any], call_flow_map: dict[str, Any]) -> dict[str, str]:
    deployables = packs["system"].get("deployable_units", [])
    frontend = packs["frontend"].get("frontend_apps", [])
    applications = (
        packs["system"].get("backend_projects", [])
        + packs["system"].get("frontend_projects", [])
        + packs["system"].get("supporting_projects", [])
        + packs["system"].get("database_support_projects", [])
    )
    external_targets = unique([item.get("target_system", "unknown") for item in packs["external"].get("external_dependencies", [])])[:6]
    modules = module_map["modules"]
    module_edges = packs["dependencies"].get("module_dependencies", [])[:25]
    flows = [flow for flow in call_flow_map["flows"] if flow.get("status") != "partial"][:3]

    diagrams = {}
    lines = ["%% Generated from source evidence. Unknown items are marked as unknown.", "flowchart LR", "  User[Users]", "  System[Legacy System: unknown]"]
    lines.append("  User --> System")
    for idx, target in enumerate(external_targets, start=1):
        tid = f"External{idx}"
        lines.append(f"  {tid}[\"{mermaid_label(target)}\"]")
        lines.append(f"  System --> {tid}")
    if not external_targets:
        lines.append("  UnknownExternal[External dependencies unknown]")
        lines.append("  System --> UnknownExternal")
    diagrams["system-context.mmd"] = "\n".join(lines) + "\n"

    lines = ["%% Generated from source evidence. Unknown items are marked as unknown.", "flowchart TB", "  subgraph Repo[Repository]"]
    for app in applications:
        aid = sanitize_id(app.get("name", "unknown"))
        label = f"{app.get('name', 'unknown')} ({app.get('type', 'unknown')})"
        lines.append(f"    {aid}[\"{mermaid_label(label)}\"]")
    lines.append("  end")
    for item in packs["system"].get("deployable_units", []):
        aid = sanitize_id(item.get("name", "unknown"))
        lines.append(f"  {aid}:::deployable")
    for idx, target in enumerate(external_targets, start=1):
        tid = f"External{idx}"
        lines.append(f"  {tid}[\"{mermaid_label(target)}\"]")
        for deployable in deployables[:2]:
            lines.append(f"  {sanitize_id(deployable.get('name', 'unknown'))} --> {tid}")
    lines.append("  classDef deployable stroke-width:3px")
    diagrams["container-view.mmd"] = "\n".join(lines) + "\n"
    top_modules = sorted(modules, key=lambda m: len(m["main_components"]), reverse=True)[:8]
    lines = ["%% Generated from source evidence. Unknown items are marked as unknown.", "flowchart TB"]
    for module in top_modules:
        mid = sanitize_id(module["name"])
        lines.append(f"  subgraph {mid}[\"{mermaid_label(module['name'])}\"]")
        for comp in module["main_components"][:5]:
            cid = sanitize_id(module["name"] + "_" + comp["name"])
            label = f"{comp['name']} ({comp.get('type','Unknown')})"
            lines.append(f"    {cid}[\"{mermaid_label(label)}\"]")
        lines.append("  end")
    diagrams["component-view.mmd"] = "\n".join(lines) + "\n"

    lines = ["%% Generated from source evidence. Unknown items are marked as unknown.", "flowchart LR"]
    for edge in module_edges:
        source = edge.get("from", "unknown")
        target = edge.get("to", "unknown")
        lines.append(f"  {sanitize_id(source)}[\"{mermaid_label(source)}\"] --> {sanitize_id(target)}[\"{mermaid_label(target)}\"]")
    diagrams["dependency-view.mmd"] = "\n".join(lines) + "\n"

    lines = ["%% Generated from source evidence. Unknown items are marked as unknown.", "flowchart TB"]
    if not flows:
        lines.append("  note[No fully traced flows detected; see call-flow-map.json partial flows]")
    for flow in flows:
        previous = None
        for step in flow.get("steps", []):
            sid = sanitize_id(flow["flow_id"] + "_" + str(step["step"]))
            label = f"{step['step']}. {step['component']}\\n{step['layer']} / {step['module']}"
            lines.append(f"  {sid}[\"{mermaid_label(label)}\"]")
            if previous:
                lines.append(f"  {previous} --> {sid}")
            previous = sid
    diagrams["call-flow-view.mmd"] = "\n".join(lines) + "\n"
    return diagrams


def build_open_questions_markdown(open_questions: list[str]) -> str:
    return "# Open Questions\n\n" + "\n".join(f"- {question}" for question in open_questions) + "\n"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root).resolve()
    final_root = output_root / "final"
    packs = load_packs(output_root)
    module_map = build_module_boundary_map(packs)
    system_inventory = build_system_inventory(packs)
    component_registry = build_component_registry(packs)
    dependency_graph = build_dependency_graph(packs)
    interface_catalogue = build_interface_catalogue(packs)
    call_flow_map = build_call_flow_map(packs)
    violations = build_architecture_violation_register(packs)
    risk_register = build_risk_register(packs, violations["violations"])
    open_questions = build_open_questions(packs, module_map, call_flow_map)

    write_json(final_root / "system-inventory.json", system_inventory)
    write_json(final_root / "module-boundary-map.json", module_map)
    write_json(final_root / "component-registry.json", component_registry)
    write_json(final_root / "dependency-graph.json", dependency_graph)
    write_json(final_root / "application-interface-catalogue.json", interface_catalogue)
    write_json(final_root / "call-flow-map.json", call_flow_map)
    write_json(final_root / "architecture-violation-register.json", violations)
    write_json(final_root / "application-risk-register.json", risk_register)

    write_text(final_root / "application-architecture-summary.md", build_markdown_summary(packs, system_inventory, module_map, dependency_graph, risk_register, open_questions))
    write_text(final_root / "architecture-pattern-report.md", build_pattern_report(packs, violations))
    write_text(final_root / "strangler-candidate-report.md", build_strangler_report(packs, module_map, risk_register))
    write_text(final_root / "forward-engineering-input-map.md", build_forward_map(packs, module_map, risk_register))
    write_text(final_root / "open-questions.md", build_open_questions_markdown(open_questions))

    for name, text in build_diagrams(packs, module_map, call_flow_map).items():
        write_text(final_root / "diagrams" / name, text)

    summary = {
        "output_directory": str(final_root),
        "files_created": [
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
            "diagrams/system-context.mmd",
            "diagrams/container-view.mmd",
            "diagrams/component-view.mmd",
            "diagrams/dependency-view.mmd",
            "diagrams/call-flow-view.mmd",
        ],
        "detected_architecture_pattern": best_pattern(packs).get("pattern", "Unknown"),
        "module_count": len(module_map["modules"]),
        "open_question_count": len(open_questions),
        "risk_count": len(risk_register["risks"]),
    }
    print(json.dumps(summary, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate final application architecture artifacts from evidence packs.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
