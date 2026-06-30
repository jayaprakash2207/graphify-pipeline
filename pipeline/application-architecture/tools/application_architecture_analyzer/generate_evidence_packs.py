#!/usr/bin/env python3
"""
Generate Application Architecture evidence packs from inventory + parsed facts.

This step intentionally reads only:
  - architecture-output/inventory/*.json
  - architecture-output/parsed/*.json

It does not read legacy source files and does not generate final architecture
artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


GENERATOR_VERSION = "0.1.0"

SOURCE_ARTIFACTS = [
    "architecture-output/inventory/file-inventory.json",
    "architecture-output/inventory/project-inventory.json",
    "architecture-output/inventory/language-summary.json",
    "architecture-output/inventory/ignored-files-report.json",
    "architecture-output/parsed/symbol-registry.json",
    "architecture-output/parsed/route-registry.json",
    "architecture-output/parsed/dependency-candidates.json",
    "architecture-output/parsed/entry-point-candidates.json",
    "architecture-output/parsed/roslyn-semantic-facts.json",
]

PRIMITIVE_TYPES = {
    "ActionResult",
    "bool",
    "byte",
    "char",
    "Dictionary",
    "decimal",
    "double",
    "float",
    "Guid",
    "IActionResult",
    "ICollection",
    "IEnumerable",
    "IList",
    "ILogger",
    "IReadOnlyCollection",
    "IReadOnlyList",
    "IResult",
    "IServiceCollection",
    "int",
    "List",
    "long",
    "object",
    "ReadOnlyCollection",
    "short",
    "string",
    "uint",
    "ulong",
    "void",
    "Task",
    "CancellationToken",
}

LAYER_ORDER = {
    "Presentation/UI": 1,
    "API": 1,
    "Application": 2,
    "Domain": 3,
    "Infrastructure": 4,
    "DataAccess": 4,
    "Integration": 4,
    "CrossCutting": 2,
    "Unknown": 0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def avg_confidence(items: list[dict[str, Any]], default: float = 0.0) -> float:
    values = [float(item.get("confidence", 0.0)) for item in items if item.get("confidence") is not None]
    if not values:
        return default
    return round(sum(values) / len(values), 3)


def unique_sorted(values: list[Any]) -> list[Any]:
    return sorted({value for value in values if value not in {None, "", "unknown"}})


def source_files_from_items(items: list[dict[str, Any]]) -> list[str]:
    files: list[str] = []
    for item in items:
        for key in ("file", "source_file", "path"):
            value = item.get(key)
            if value and isinstance(value, str) and not value.startswith("architecture-output/"):
                files.append(value)
        for evidence in item.get("evidence", []) or []:
            if isinstance(evidence, dict) and evidence.get("file"):
                files.append(evidence["file"])
    return unique_sorted(files)


def build_chunk_lookup(chunk_index: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not chunk_index:
        return lookup
    for chunk in chunk_index.get("chunks", []):
        lookup[chunk.get("file", "")].append(chunk)
    return lookup


def chunk_refs_for(
    chunk_lookup: dict[str, list[dict[str, Any]]],
    file: str | None,
    line: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not file:
        return []
    chunks = chunk_lookup.get(file.replace("\\", "/"), [])
    if line is not None:
        try:
            line_number = int(line)
        except (TypeError, ValueError):
            line_number = None
        if line_number is not None:
            chunks = [chunk for chunk in chunks if chunk.get("start_line", 0) <= line_number <= chunk.get("end_line", 0)]
    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "file": chunk.get("file"),
            "start_line": chunk.get("start_line"),
            "end_line": chunk.get("end_line"),
            "chunk_sha256": chunk.get("chunk_sha256"),
        }
        for chunk in chunks[:limit]
    ]


def semantic_component_key(file: str | None, name: str | None) -> str:
    safe_file = (file or "").replace("\\", "/")
    return f"{safe_file}::{name or ''}"


def merge_semantic_components(
    components: list[dict[str, Any]],
    semantic_facts: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not semantic_facts or semantic_facts.get("status") != "active":
        return components
    semantic_by_key = {
        semantic_component_key(item.get("file"), item.get("name")): item
        for item in semantic_facts.get("semantic_components", [])
    }
    enriched_components = []
    for component in components:
        enriched = dict(component)
        semantic = semantic_by_key.get(semantic_component_key(component.get("file"), component.get("name")))
        if semantic:
            enriched["semantic_symbol_id"] = semantic.get("semantic_symbol_id")
            enriched["semantic_full_name"] = semantic.get("full_name")
            enriched["semantic_parser_backend"] = semantic.get("parser_backend", "roslyn_semantic_model")
            enriched["semantic_methods"] = semantic.get("public_or_internal_methods", [])
            enriched["semantic_constructor_dependencies"] = semantic.get("constructor_dependencies", [])
            enriched["semantic_confidence"] = semantic.get("confidence", 0.0)
            existing_backend = enriched.get("parser_backend", "unknown")
            if "roslyn_semantic_model" not in str(existing_backend):
                enriched["parser_backend"] = f"{existing_backend}+roslyn_semantic_model"
            enriched["confidence"] = max(float(enriched.get("confidence", 0.0)), min(0.97, float(semantic.get("confidence", 0.0))))
            evidence = list(enriched.get("evidence", []))
            evidence.append(
                {
                    "file": semantic.get("file"),
                    "line": semantic.get("line"),
                    "reason": "Roslyn semantic model resolved component symbol and members",
                }
            )
            enriched["evidence"] = evidence
        enriched_components.append(enriched)
    return enriched_components


def merge_semantic_dependencies(
    dependencies: list[dict[str, Any]],
    semantic_facts: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not semantic_facts or semantic_facts.get("status") != "active":
        return dependencies
    merged = list(dependencies)
    for dependency in semantic_facts.get("dependency_candidates", []):
        enriched = dict(dependency)
        metadata = dict(enriched.get("metadata", {}) or {})
        metadata.setdefault("parser_backend", "roslyn_semantic_model")
        enriched["metadata"] = metadata
        enriched.setdefault("confidence", 0.94 if enriched.get("kind") == "roslyn_component_call" else 0.9)
        merged.append(enriched)
    return merged


def evidence_header(evidence_pack_type: str, source_files_used: list[str], confidence: float) -> dict[str, Any]:
    return {
        "evidence_pack_type": evidence_pack_type,
        "generated_at": utc_now(),
        "generator_version": GENERATOR_VERSION,
        "source_artifacts_used": SOURCE_ARTIFACTS,
        "source_files_used": source_files_used,
        "confidence": confidence,
    }


def normalize_type(value: str) -> str:
    value = (value or "").strip().replace("?", "")
    value = value.replace("global::", "")
    value = re.sub(r"\([^)]*\)", "", value)
    value = value.replace("typeof", "").strip("<> ")
    value = value.split(".", 1)[0] if value.startswith("System.") else value
    if "." in value and not value.startswith("Microsoft."):
        value = value.rsplit(".", 1)[-1]
    if "<" in value:
        value = value.split("<", 1)[0]
    return value.strip()


def folder_for_file(path: str, depth: int = 3) -> str:
    parts = list(PurePosixPath(path).parts)
    if len(parts) <= depth:
        return str(PurePosixPath(path).parent)
    return "/".join(parts[:depth])


def component_indexes(components: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_name: dict[str, dict[str, Any]] = {}
    type_to_component: dict[str, str] = {}
    for component in components:
        existing = by_name.get(component["name"])
        if not existing:
            by_name[component["name"]] = component
        else:
            existing_is_test = str(existing.get("file", "")).startswith("tests/")
            new_is_test = str(component.get("file", "")).startswith("tests/")
            if existing_is_test and not new_is_test:
                by_name[component["name"]] = component
            elif existing_is_test == new_is_test and component.get("confidence", 0.0) > existing.get("confidence", 0.0):
                by_name[component["name"]] = component
        type_to_component[component["name"]] = component["name"]
        name = component["name"]
        if name.startswith("I") and len(name) > 1:
            type_to_component[name[1:]] = name
        for iface in component.get("implemented_interfaces", []) or []:
            simple = normalize_type(iface)
            if simple:
                type_to_component[simple] = name
    return by_name, type_to_component


def build_di_resolution_map(dependencies: list[dict[str, Any]], type_to_component: dict[str, str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for dep in dependencies:
        if dep.get("kind") not in {"di_registration", "db_context_registration"}:
            continue
        metadata = dep.get("metadata") or {}
        service = normalize_type(metadata.get("service") or dep.get("from") or "")
        implementation = normalize_type(metadata.get("implementation") or dep.get("to") or "")
        if not service or not implementation:
            continue
        if implementation in type_to_component:
            mapping[service] = type_to_component[implementation]
        elif implementation.startswith("I") and implementation[1:] in type_to_component:
            mapping[service] = type_to_component[implementation[1:]]
    return mapping


def resolve_component_name(target: str, type_to_component: dict[str, str], di_resolution: dict[str, str] | None = None) -> str | None:
    if not target:
        return None
    base = target.split(".", 1)[0]
    simple = normalize_type(base)
    if simple in PRIMITIVE_TYPES or not simple:
        return None
    if di_resolution and simple in di_resolution:
        return di_resolution[simple]
    if simple in type_to_component:
        return type_to_component[simple]
    if di_resolution and simple.startswith("I") and simple[1:] in di_resolution:
        return di_resolution[simple[1:]]
    if simple.startswith("I") and simple[1:] in type_to_component:
        return type_to_component[simple[1:]]
    return None


def graph_sccs(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    result: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in indexes:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[neighbor])

        if lowlinks[node] == indexes[node]:
            scc = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                scc.append(member)
                if member == node:
                    break
            if len(scc) > 1:
                result.append(sorted(scc))

    for node in sorted(graph):
        if node not in indexes:
            strongconnect(node)
    return result


def resolved_component_edges(
    components: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name, type_to_component = component_indexes(components)
    di_resolution = build_di_resolution_map(dependencies, type_to_component)
    edges: list[dict[str, Any]] = []
    allowed_kinds = {
        "component_call",
        "roslyn_component_call",
        "constructor",
        "property_injection",
        "method_parameter",
        "mediatr_send",
        "mediatr_handler_candidate",
        "di_registration",
        "di_resolution_candidate",
        "db_context_registration",
        "razor_inject",
        "razor_inherits",
        "http_client_call",
        "frontend_api_call",
    }
    for dep in dependencies:
        source = dep.get("from")
        if source not in by_name or dep.get("kind") not in allowed_kinds:
            continue
        source_component = by_name.get(source)
        if source_component and source_component.get("architecture_significance") == "VerificationOnly":
            continue
        target_name = resolve_component_name(dep.get("to", ""), type_to_component, di_resolution)
        if not target_name or target_name == source:
            continue
        target_component = by_name.get(target_name)
        if target_component and target_component.get("architecture_significance") == "VerificationOnly":
            continue
        edges.append(
            {
                "from": source,
                "to": target_name,
                "relationship": dep.get("relationship", "uses"),
                "kind": dep.get("kind"),
                "source_file": dep.get("source_file"),
                "line": dep.get("line"),
                "evidence": dep.get("evidence"),
                "confidence": dep.get("confidence", 0.0),
                "dependency_id": dep.get("dependency_id"),
                "metadata": dep.get("metadata", {}),
            }
        )
    return dedupe_edges(edges)


def dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result = []
    for edge in edges:
        marker = (edge.get("from"), edge.get("to"), edge.get("relationship"), edge.get("kind"), edge.get("source_file"), edge.get("line"))
        if marker in seen:
            continue
        seen.add(marker)
        result.append(edge)
    return result


def module_dependencies_from_edges(
    components: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    component_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name, _ = component_indexes(components)
    module_edges: list[dict[str, Any]] = []
    for dep in dependencies:
        if dep.get("kind") == "module_dependency_candidate":
            if str(dep.get("source_file", "")).startswith("tests/"):
                continue
            if dep.get("from") == "Verification" or dep.get("to") == "Verification":
                continue
            module_edges.append(
                {
                    "from": dep.get("from"),
                    "to": dep.get("to"),
                    "relationship": dep.get("relationship", "uses"),
                    "source_file": dep.get("source_file"),
                    "line": dep.get("line"),
                    "evidence": dep.get("evidence"),
                    "confidence": dep.get("confidence", 0.0),
                }
            )
    for edge in component_edges:
        source_component = by_name.get(edge["from"])
        target_component = by_name.get(edge["to"])
        if not source_component or not target_component:
            continue
        source_module = source_component.get("module_guess") or "Unknown"
        target_module = target_component.get("module_guess") or "Unknown"
        if source_module == "Unknown" or target_module == "Unknown" or source_module == target_module:
            continue
        module_edges.append(
            {
                "from": source_module,
                "to": target_module,
                "relationship": "uses",
                "source_file": edge.get("source_file"),
                "line": edge.get("line"),
                "evidence": f"Resolved component dependency {edge['from']} -> {edge['to']}",
                "confidence": min(float(edge.get("confidence", 0.6)), 0.72),
            }
        )
    return dedupe_edges(module_edges)


def high_coupling(edges: list[dict[str, Any]], threshold: int) -> list[dict[str, Any]]:
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        outgoing[edge["from"]].add(edge["to"])
        incoming[edge["to"]].add(edge["from"])
    nodes = set(outgoing) | set(incoming)
    results = []
    for node in sorted(nodes):
        afferent = len(incoming[node])
        efferent = len(outgoing[node])
        total = afferent + efferent
        if total >= threshold:
            results.append(
                {
                    "name": node,
                    "afferent_coupling": afferent,
                    "efferent_coupling": efferent,
                    "total_coupling": total,
                    "confidence": 0.72,
                }
            )
    return sorted(results, key=lambda item: item["total_coupling"], reverse=True)


def build_system_inventory_pack(data: dict[str, Any]) -> dict[str, Any]:
    project_inventory = data["project_inventory"]
    components = data["components"]
    projects = project_inventory.get("projects", [])
    source_files = source_files_from_items(projects)
    workers = [
        component
        for component in components
        if component.get("component_type") in {"ScheduledJob", "MessageConsumer", "BatchJob"}
    ]
    unknowns = ["system_name is unknown because no authoritative system-name artifact exists in Step 1 or Step 2 outputs."]
    if not workers:
        unknowns.append("No worker, scheduled job, batch job, or message consumer component was detected in parsed facts.")
    open_questions = [
        "Confirm the repository-level system name because no authoritative system-name artifact was detected.",
        "Confirm whether Docker compose services represent the complete runtime deployment topology or local development only.",
    ]
    pack = {
        **evidence_header("system_inventory", source_files, avg_confidence(projects, 0.85)),
        "system_name": "unknown",
        "extracted_facts": {
            "solution_count": project_inventory.get("summary", {}).get("solution_count", 0),
            "project_count": project_inventory.get("summary", {}).get("project_count", 0),
            "deployable_unit_count": project_inventory.get("summary", {}).get("deployable_unit_count", 0),
            "docker_compose_service_count": len(project_inventory.get("docker_compose_services", [])),
        },
        "backend_projects": project_inventory.get("backend_projects", []),
        "frontend_projects": project_inventory.get("frontend_projects", []),
        "supporting_projects": project_inventory.get("supporting_projects", []),
        "database_support_projects": project_inventory.get("database_projects", []),
        "test_projects": project_inventory.get("test_projects", []),
        "workers_or_jobs": [
            {
                "name": component["name"],
                "type": component["component_type"],
                "file": component["file"],
                "evidence": component.get("evidence", []),
                "confidence": component.get("confidence", 0.0),
            }
            for component in workers
        ],
        "deployable_units": project_inventory.get("deployable_units", []),
        "build_files": project_inventory.get("build_files", []),
        "deployment_files": project_inventory.get("deployment_files", []),
        "docker_compose_services": project_inventory.get("docker_compose_services", []),
        "framework_indicators": project_inventory.get("framework_indicators", []),
        "unknowns": unknowns,
        "open_questions": open_questions,
    }
    return pack


def build_module_boundary_pack(data: dict[str, Any], module_edges: list[dict[str, Any]]) -> dict[str, Any]:
    components = data["components"]
    entry_points = data["entry_points"]
    chunk_lookup = data.get("chunk_lookup", {})
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    edge_evidence: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in module_edges:
        if edge.get("from") and edge.get("to") and edge["from"] != edge["to"]:
            outgoing[edge["from"]].add(edge["to"])
            incoming[edge["to"]].add(edge["from"])
            edge_evidence[(edge["from"], edge["to"])].append(edge)

    modules: dict[str, dict[str, Any]] = {}
    for component in components:
        module = component.get("module_guess") or "Unknown"
        if module == "Unknown":
            continue
        bucket = modules.setdefault(
            module,
            {
                "name": module,
                "responsibility_guess": f"unknown; candidate inferred from parsed components, routes, and dependency signals containing '{module}'.",
                "source_folders": set(),
                "namespaces_or_packages": set(),
                "components": [],
                "entry_points": [],
                "route_prefixes": set(),
                "depends_on": set(),
                "depended_on_by": set(),
                "evidence_files": set(),
                "evidence_signals": [],
                "component_confidences": [],
                "open_questions": [],
            },
        )
        bucket["source_folders"].add(folder_for_file(component["file"]))
        if component.get("namespace_or_package"):
            bucket["namespaces_or_packages"].add(component["namespace_or_package"])
        bucket["components"].append(
            {
                "component_id": component.get("component_id"),
                "name": component["name"],
                "type": component.get("component_type"),
                "layer": component.get("layer_guess"),
                "file": component["file"],
                "source_chunks": chunk_refs_for(chunk_lookup, component.get("file"), component.get("start_line")),
                "confidence": component.get("confidence", 0.0),
            }
        )
        bucket["evidence_files"].add(component["file"])
        bucket["component_confidences"].append(component.get("module_guess_confidence", component.get("confidence", 0.0)))
        bucket["evidence_signals"].append(component.get("module_guess_evidence", "parsed module_guess"))

    for entry in entry_points:
        module = entry.get("owning_module_guess") or "Unknown"
        if module == "Unknown":
            continue
        bucket = modules.setdefault(
            module,
            {
                "name": module,
                "responsibility_guess": f"unknown; candidate inferred from parsed entry points containing '{module}'.",
                "source_folders": set(),
                "namespaces_or_packages": set(),
                "components": [],
                "entry_points": [],
                "route_prefixes": set(),
                "depends_on": set(),
                "depended_on_by": set(),
                "evidence_files": set(),
                "evidence_signals": [],
                "component_confidences": [],
                "open_questions": [],
            },
        )
        bucket["entry_points"].append(
            {
                "entry_point_id": entry.get("entry_point_id"),
                "type": entry.get("type"),
                "method": entry.get("method"),
                "path_or_name": entry.get("path_or_name"),
                "owning_component": entry.get("owning_component"),
                "source_file": entry.get("source_file"),
                "source_chunks": chunk_refs_for(chunk_lookup, entry.get("source_file"), entry.get("line")),
                "confidence": entry.get("confidence", 0.0),
            }
        )
        path = entry.get("path_or_name") or ""
        if path.startswith("/"):
            bucket["route_prefixes"].add("/" + path.strip("/").split("/", 1)[0])
        if entry.get("source_file"):
            bucket["source_folders"].add(folder_for_file(entry["source_file"]))
            bucket["evidence_files"].add(entry["source_file"])
        bucket["component_confidences"].append(entry.get("confidence", 0.0))

    for module, deps in outgoing.items():
        if module in modules:
            modules[module]["depends_on"].update(deps)
    for module, users in incoming.items():
        if module in modules:
            modules[module]["depended_on_by"].update(users)

    module_candidates = []
    for name, bucket in sorted(modules.items()):
        confidence_values = bucket["component_confidences"]
        confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else 0.5
        open_questions = []
        if confidence < 0.7:
            open_questions.append(f"Confirm whether '{name}' is a true module boundary; evidence is mainly heuristic module_guess output.")
        if len(bucket["source_folders"]) > 5:
            open_questions.append(f"'{name}' spans multiple source folders; confirm whether this is one module or several feature areas.")
        module_candidates.append(
            {
                "name": name,
                "responsibility_guess": bucket["responsibility_guess"],
                "source_folders": sorted(bucket["source_folders"]),
                "namespaces_or_packages": sorted(bucket["namespaces_or_packages"]),
                "components": sorted(bucket["components"], key=lambda item: item["name"]),
                "entry_points": sorted(bucket["entry_points"], key=lambda item: (item.get("path_or_name") or "", item.get("owning_component") or "")),
                "route_prefixes": sorted(bucket["route_prefixes"]),
                "depends_on": sorted(bucket["depends_on"]),
                "depended_on_by": sorted(bucket["depended_on_by"]),
                "afferent_coupling": len(bucket["depended_on_by"]),
                "efferent_coupling": len(bucket["depends_on"]),
                "evidence_files": sorted(bucket["evidence_files"]),
                "evidence_signals": sorted(set(bucket["evidence_signals"])),
                "confidence": confidence,
                "open_questions": open_questions,
            }
        )

    unknown_components = [component for component in components if component.get("module_guess") == "Unknown"]
    source_files = source_files_from_items(components + entry_points)
    return {
        **evidence_header("module_boundary", source_files, avg_confidence(module_candidates, 0.65)),
        "extracted_facts": {
            "module_candidate_count": len(module_candidates),
            "components_with_unknown_module": len(unknown_components),
            "module_dependency_candidate_count": len(module_edges),
        },
        "module_candidates": module_candidates,
        "module_dependency_evidence": module_edges,
        "unknowns": [
            f"{len(unknown_components)} components have module_guess='Unknown'.",
            "Module responsibilities are not asserted as business truth; responsibility_guess values describe evidence grouping only.",
        ],
        "open_questions": [
            "Review modules with low confidence or broad folder spread to confirm true domain/module ownership.",
            "Review similarly named or overlapping module candidates to decide whether they are separate modules or one combined module.",
        ],
    }


def build_component_registry_pack(data: dict[str, Any]) -> dict[str, Any]:
    components = data["components"]
    chunk_lookup = data.get("chunk_lookup", {})
    grouped_by_type: dict[str, list[str]] = defaultdict(list)
    grouped_by_layer: dict[str, list[str]] = defaultdict(list)
    grouped_by_module: dict[str, list[str]] = defaultdict(list)
    for component in components:
        grouped_by_type[component.get("component_type", "Unknown")].append(component["name"])
        grouped_by_layer[component.get("layer_guess", "Unknown")].append(component["name"])
        grouped_by_module[component.get("module_guess", "Unknown")].append(component["name"])

    component_records = [
        {
            "component_id": component.get("component_id"),
            "name": component["name"],
            "type": component.get("component_type", "Unknown"),
            "layer": component.get("layer_guess", "Unknown"),
            "module_guess": component.get("module_guess", "Unknown"),
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
            "namespace_or_package": component.get("namespace_or_package"),
            "file": component["file"],
            "public_methods": component.get("public_methods", []),
            "dependencies": component.get("dependencies", []),
            "imports": component.get("imports", []),
            "annotations": component.get("annotations", []),
            "base_class": component.get("base_class"),
            "implemented_interfaces": component.get("implemented_interfaces", []),
            "source_chunks": chunk_refs_for(chunk_lookup, component.get("file"), component.get("start_line")),
            "evidence": component.get("evidence", []),
            "uncertainty": component.get("uncertainty", []),
            "confidence": component.get("confidence", 0.0),
        }
        for component in components
    ]
    unknown_type = [component for component in components if component.get("component_type") == "Unknown"]
    unknown_layer = [component for component in components if component.get("layer_guess") == "Unknown"]
    return {
        **evidence_header("component_registry", source_files_from_items(components), avg_confidence(components, 0.7)),
        "extracted_facts": {
            "component_count": len(components),
            "components_by_type": {key: len(value) for key, value in sorted(grouped_by_type.items())},
            "components_by_layer": {key: len(value) for key, value in sorted(grouped_by_layer.items())},
            "components_by_module_guess": {key: len(value) for key, value in sorted(grouped_by_module.items())},
            "roslyn_semantic_component_count": sum(1 for component in components if component.get("semantic_symbol_id")),
        },
        "groups": {
            "by_type": {key: sorted(value) for key, value in sorted(grouped_by_type.items())},
            "by_layer": {key: sorted(value) for key, value in sorted(grouped_by_layer.items())},
            "by_module_guess": {key: sorted(value) for key, value in sorted(grouped_by_module.items())},
        },
        "components": component_records,
        "unknowns": [
            f"{len(unknown_type)} components have component_type='Unknown'.",
            f"{len(unknown_layer)} components have layer_guess='Unknown'.",
        ],
        "open_questions": [
            "Review Unknown components to decide whether they are constants, options, test artifacts, or architecture-significant components.",
            "Confirm whether test-project components should be included in later final architecture views or separated as verification-only artifacts.",
        ],
    }


def build_dependency_pack(
    data: dict[str, Any],
    component_edges: list[dict[str, Any]],
    module_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    dependencies = data["dependencies"]
    components = data["components"]
    component_graph: dict[str, set[str]] = defaultdict(set)
    for edge in component_edges:
        component_graph[edge["from"]].add(edge["to"])
        component_graph.setdefault(edge["to"], set())
    module_graph: dict[str, set[str]] = defaultdict(set)
    for edge in module_edges:
        module_graph[edge["from"]].add(edge["to"])
        module_graph.setdefault(edge["to"], set())

    component_cycles = graph_sccs(component_graph)
    module_cycles = graph_sccs(module_graph)
    unresolved_count = len(dependencies) - len(component_edges)
    semantic_dependency_count = sum(
        1
        for dependency in dependencies
        if dependency.get("kind") == "roslyn_component_call"
        or (dependency.get("metadata") or {}).get("parser_backend") == "roslyn_semantic_model"
    )
    return {
        **evidence_header("dependency", source_files_from_items(dependencies), avg_confidence(dependencies, 0.65)),
        "extracted_facts": {
            "dependency_candidate_count": len(dependencies),
            "roslyn_semantic_dependency_candidate_count": semantic_dependency_count,
            "resolved_component_dependency_count": len(component_edges),
            "module_dependency_candidate_count": len(module_edges),
            "component_cycle_count": len(component_cycles),
            "module_cycle_count": len(module_cycles),
        },
        "component_dependencies": [
            {
                "from": edge["from"],
                "to": edge["to"],
                "relationship": edge["relationship"],
                "kind": edge["kind"],
                "source_file": edge["source_file"],
                "line": edge["line"],
                "evidence": edge["evidence"],
                "confidence": edge["confidence"],
                "dependency_id": edge.get("dependency_id"),
                "metadata": edge.get("metadata", {}),
            }
            for edge in component_edges
        ],
        "raw_dependency_candidates": dependencies,
        "module_dependencies": module_edges,
        "cycles": {
            "component_cycles": [{"cycle": cycle, "severity": "Medium", "confidence": 0.65} for cycle in component_cycles],
            "module_cycles": [{"cycle": cycle, "severity": "High", "confidence": 0.7} for cycle in module_cycles],
        },
        "high_coupling_candidates": {
            "components": high_coupling(component_edges, threshold=8),
            "modules": high_coupling(module_edges, threshold=3),
        },
        "unknowns": [
            f"{unresolved_count} raw dependency candidates are imports, primitives, framework/library references, or otherwise unresolved to local components.",
            "Dependency candidates are evidence for later review, not a fully compiled dependency graph.",
        ],
        "open_questions": [
            "Confirm whether import-only dependencies should be considered architecture dependencies in the final graph.",
            "Review any cycles for false positives from interface/base-class resolution before finalizing architecture violations.",
        ],
    }


def build_entry_point_pack(data: dict[str, Any]) -> dict[str, Any]:
    entry_points = data["entry_points"]
    chunk_lookup = data.get("chunk_lookup", {})
    grouped = defaultdict(list)
    for entry in entry_points:
        grouped[entry.get("type", "Unknown")].append(entry)
    enriched_entry_points = []
    for entry in entry_points:
        enriched = dict(entry)
        enriched["source_chunks"] = chunk_refs_for(chunk_lookup, entry.get("source_file"), entry.get("line"))
        enriched_entry_points.append(enriched)
    return {
        **evidence_header("entry_points", source_files_from_items(enriched_entry_points), avg_confidence(enriched_entry_points, 0.75)),
        "extracted_facts": {
            "entry_point_count": len(entry_points),
            "entry_points_by_type": {key: len(value) for key, value in sorted(grouped.items())},
            "graphql_endpoint_count": len(grouped.get("GraphQL", [])),
            "soap_endpoint_count": len(grouped.get("SOAP", [])),
            "scheduled_job_count": len(grouped.get("ScheduledJob", [])),
            "message_consumer_count": len(grouped.get("MessageConsumer", [])),
            "batch_job_count": len(grouped.get("BatchJob", [])),
        },
        "entry_points": enriched_entry_points,
        "unknowns": [
            "No GraphQL or SOAP endpoints were detected in parsed facts.",
            "No scheduled job, message consumer, or batch-job entry points were detected in parsed facts.",
        ],
        "open_questions": [
            "Confirm whether CLI Program.cs entries should be treated only as application bootstraps in final architecture.",
            "Review convention-based ASP.NET route registrations because exact runtime endpoints can depend on framework conventions.",
        ],
    }


def edge_relevance_score(edge: dict[str, Any], entry: dict[str, Any], by_name: dict[str, dict[str, Any]]) -> int:
    target = by_name.get(edge.get("to"), {})
    target_type = target.get("component_type") or target.get("type") or "Unknown"
    target_layer = target.get("layer_guess") or target.get("layer") or "Unknown"
    metadata = edge.get("metadata", {}) or {}
    source_method = metadata.get("source_method")
    route_action = entry.get("route_action") or "unknown"
    kind = edge.get("kind")
    score = 0
    if kind == "component_call":
        score += 40
    elif kind == "roslyn_component_call":
        score += 55
    elif kind == "mediatr_handler_candidate":
        score += 38
    elif kind == "mediatr_send":
        score += 34
    elif kind == "method_parameter":
        score += 30
    elif kind == "di_resolution_candidate":
        score += 24
    elif kind in {"constructor", "property_injection", "razor_inject"}:
        score += 12
    if source_method and source_method == route_action:
        score += 35
    elif route_action == "HandleAsync" and source_method == "HandleAsync":
        score += 35
    elif source_method and route_action in {"unknown", "AddRoute"}:
        score += 12
    if target_type == "Repository" or target_layer == "DataAccess":
        score += 45
    elif target_type in {"Service", "Handler"} or target_layer == "Application":
        score += 32
    elif target_type in {"ExternalClient", "Gateway"} or target_layer == "Integration":
        score += 30
    elif target_type in {"DTO", "Entity", "Configuration"}:
        score -= 8
    if edge.get("relationship") == "injects":
        score -= 4
    return score


def ordered_edges_for_entry(
    current: str,
    entry: dict[str, Any],
    edges_by_from: dict[str, list[dict[str, Any]]],
    by_name: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        edges_by_from.get(current, []),
        key=lambda edge: (
            -edge_relevance_score(edge, entry, by_name),
            edge.get("source_file") or "",
            edge.get("line") or 0,
            edge.get("to") or "",
        ),
    )


def is_framework_route_marker(entry: dict[str, Any]) -> bool:
    path = str(entry.get("path_or_name") or "")
    source = str(entry.get("source_file") or "")
    return source.endswith("/Program.cs") and path in {
        "ASP.NET Razor Pages route registration",
        "ASP.NET controller route registration",
        "MinimalApi.Endpoint route registration",
    }


def is_single_component_page_flow(entry: dict[str, Any], steps: list[dict[str, Any]]) -> bool:
    if len(steps) != 1 or entry.get("type") != "HTTP_API":
        return False
    path = str(entry.get("path_or_name") or "")
    source_file = str(entry.get("source_file") or "")
    first = steps[0]
    return (
        not path.startswith("/api/")
        and first.get("layer") == "Presentation/UI"
        and (source_file.endswith(".cshtml") or source_file.endswith(".cshtml.cs") or "/Pages/" in source_file or "/Views/" in source_file)
    )


def build_call_flow_pack(
    data: dict[str, Any],
    component_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    components = data["components"]
    entry_points = data["entry_points"]
    dependencies = data["dependencies"]
    chunk_lookup = data.get("chunk_lookup", {})
    by_name, type_to_component = component_indexes(components)
    by_file = {component.get("file"): component for component in components}
    di_resolution = build_di_resolution_map(dependencies, type_to_component)
    edges_by_from: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in component_edges:
        edges_by_from[edge["from"]].append(edge)

    external_by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dep in dependencies:
        if is_external_http_dependency(dep):
            external_by_component[dep.get("from", "unknown")].append(dep)

    flows = []
    for idx, entry in enumerate(entry_points, start=1):
        owner = resolve_entry_owner(entry, by_name, by_file)
        steps = []
        seen_components: set[str] = set()

        def add_step(component_name: str, operation: str, evidence: dict[str, Any] | None = None) -> None:
            component = by_name.get(component_name, {})
            step_evidence = evidence or {"file": entry.get("source_file"), "line": entry.get("line"), "reason": "entry point owner"}
            step_file = component.get("file", entry.get("source_file", "unknown"))
            step_line = step_evidence.get("line") if isinstance(step_evidence, dict) else None
            steps.append(
                {
                    "step": len(steps) + 1,
                    "component": component_name,
                    "layer": component.get("layer_guess", "Unknown"),
                    "module": component.get("module_guess", entry.get("owning_module_guess", "Unknown")),
                    "operation": operation or "unknown",
                    "file": step_file,
                    "source_chunks": chunk_refs_for(chunk_lookup, step_file, step_line),
                    "evidence": step_evidence,
                }
            )
            seen_components.add(component_name)

        if owner in by_name:
            add_step(owner, entry.get("path_or_name", "entry point"))
            queue = deque([(owner, 0)])
            while queue and len(steps) < 10:
                current, depth = queue.popleft()
                if depth >= 4:
                    continue
                for edge in ordered_edges_for_entry(current, entry, edges_by_from, by_name)[:6]:
                    if edge["to"] in seen_components:
                        continue
                    metadata = edge.get("metadata", {}) or {}
                    operation = metadata.get("target_method") or edge.get("relationship", "uses")
                    source_method = metadata.get("source_method")
                    add_step(
                        edge["to"],
                        operation,
                        {
                            "file": edge.get("source_file"),
                            "line": edge.get("line"),
                            "reason": edge.get("evidence"),
                            "dependency_id": edge.get("dependency_id"),
                            "source_method": source_method,
                            "resolution_quality": metadata.get("resolution_quality"),
                        },
                    )
                    queue.append((edge["to"], depth + 1))
                    if len(steps) >= 10:
                        break
        else:
            steps.append(
                {
                    "step": 1,
                    "component": owner,
                    "layer": "Unknown",
                    "module": entry.get("owning_module_guess", "Unknown"),
                    "operation": entry.get("path_or_name", "entry point"),
                    "file": entry.get("source_file", "unknown"),
                    "source_chunks": chunk_refs_for(chunk_lookup, entry.get("source_file"), entry.get("line")),
                    "evidence": {"file": entry.get("source_file"), "line": entry.get("line"), "reason": "entry point owner not resolved to component"},
                }
            )

        # Add explicit called services if route parser provided them and they were not already reached.
        for called in entry.get("called_service_or_handler", []) or []:
            target = resolve_component_name(called, type_to_component, di_resolution)
            if target and target not in seen_components and len(steps) < 10:
                add_step(target, called, {"file": entry.get("source_file"), "line": entry.get("line"), "reason": f"entry point parser reported called service {called}"})

        components_touched = [step["component"] for step in steps]
        external_systems = []
        for component_name in components_touched:
            for dep in external_by_component.get(component_name, []):
                external_systems.append(
                    {
                        "target": dep.get("to"),
                        "relationship": dep.get("relationship"),
                        "source_file": dep.get("source_file"),
                        "line": dep.get("line"),
                        "confidence": dep.get("confidence", 0.0),
                    }
                )
        data_access = [
            step["component"]
            for step in steps
            if step.get("layer") == "DataAccess" or by_name.get(step["component"], {}).get("component_type") == "Repository"
        ]
        entry_type = entry.get("type")
        has_external = bool(external_systems)
        has_application_step = any(step.get("layer") in {"Application", "Integration"} for step in steps)
        semantic_step_count = sum(
            1
            for step in steps
            if "roslyn" in str((step.get("evidence") or {}).get("resolution_quality", "")).lower()
            or str((step.get("evidence") or {}).get("dependency_id", "")).startswith("RDEP-")
        )
        has_semantic_trace = semantic_step_count > 0
        framework_marker = is_framework_route_marker(entry)
        if framework_marker:
            status = "framework_route_coverage_marker"
            partial = False
            confidence = 0.7
        elif is_single_component_page_flow(entry, steps):
            status = "single_component_page_flow_mapped"
            partial = False
            confidence = 0.68
        elif entry_type == "FrontendRoute":
            partial = len(steps) <= 1 and not has_external
            status = "frontend_route_mapped" if not partial else "partial"
            confidence = 0.66 if not partial else 0.55
        elif entry_type == "CLI":
            partial = len(steps) <= 1
            status = "bootstrap_flow_mapped" if not partial else "partial"
            confidence = 0.64 if not partial else 0.55
        else:
            partial = len(steps) <= 1 or not (data_access or has_external or has_application_step)
            status = "traced_from_dependency_candidates" if not partial else "partial"
            confidence = 0.74 if data_access else 0.66 if not partial else 0.55
        if has_semantic_trace:
            confidence = min(0.88 if not partial else 0.65, confidence + (0.08 if not partial else 0.04))
        flow_open_questions = []
        if partial:
            flow_open_questions.append("Call flow is partial because parsed facts did not resolve this entry point to downstream data access or integration steps.")
        elif framework_marker:
            flow_open_questions.append("Framework route registration is a coverage marker; individual runtime routes are represented by controller/Razor/endpoint artifacts where detected.")
        elif status == "single_component_page_flow_mapped":
            flow_open_questions.append("Single-component page flow is mapped to its PageModel/view component; no downstream dependency was detected in parsed facts.")
        flows.append(
            {
                "flow_id": f"FLOW-{idx:04d}",
                "entry_point": f"{entry.get('method', 'unknown')} {entry.get('path_or_name', 'unknown')}",
                "entry_point_type": entry.get("type"),
                "status": status,
                "steps": steps,
                "modules_touched": unique_sorted([step.get("module") for step in steps]),
                "external_systems_touched": external_systems,
                "data_access_components": sorted(set(data_access)),
                "semantic_step_count": semantic_step_count,
                "confidence": confidence,
                "open_questions": flow_open_questions,
            }
        )

    return {
        **evidence_header("call_flow", source_files_from_items(entry_points + dependencies), avg_confidence(flows, 0.58)),
        "extracted_facts": {
            "flow_count": len(flows),
            "partial_flow_count": sum(1 for flow in flows if flow["status"] == "partial"),
            "semantic_trace_flow_count": sum(1 for flow in flows if flow.get("semantic_step_count", 0) > 0),
            "flows_with_data_access_count": sum(1 for flow in flows if flow["data_access_components"]),
            "flows_with_external_system_count": sum(1 for flow in flows if flow["external_systems_touched"]),
        },
        "flows": flows,
        "unknowns": [
            "Full runtime call flows are unknown where parsed dependency candidates do not resolve method calls or framework dispatch.",
        ],
        "open_questions": [
            "Review partial flows manually before using them as behavior-preservation contracts.",
            "Confirm whether frontend-to-API calls should be merged with backend API flows in the final call-flow map.",
        ],
    }


def resolve_entry_owner(entry: dict[str, Any], by_name: dict[str, dict[str, Any]], by_file: dict[str, dict[str, Any]]) -> str:
    owner = entry.get("owning_component") or "unknown"
    source_file = entry.get("source_file", "")
    if source_file.endswith(".cshtml"):
        code_behind = by_file.get(f"{source_file}.cs")
        if code_behind:
            return code_behind["name"]
        if f"{owner}Model" in by_name:
            return f"{owner}Model"
    if owner in by_name:
        return owner
    if owner == "Program" and "Program" in by_name:
        return "Program"
    return owner


def is_external_http_dependency(dep: dict[str, Any]) -> bool:
    if dep.get("kind") == "frontend_api_call":
        return True
    if dep.get("kind") != "http_client_call":
        return False
    target = str((dep.get("metadata") or {}).get("target") or "").lower()
    source = str(dep.get("from") or "").lower()
    return "httpclient" in target or target in {"client", "_httpclient"} or source in {"httpservice", "apihealthcheck", "homepagehealthcheck"}


def build_layering_pattern_pack(
    data: dict[str, Any],
    component_edges: list[dict[str, Any]],
    module_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    components = data["components"]
    by_name = {component["name"]: component for component in components}
    layer_edges = Counter()
    violations = []
    for edge in component_edges:
        source = by_name.get(edge["from"], {})
        target = by_name.get(edge["to"], {})
        source_layer = source.get("layer_guess", "Unknown")
        target_layer = target.get("layer_guess", "Unknown")
        layer_edges[(source_layer, target_layer)] += 1
        if (
            str(edge.get("source_file", "")).startswith("tests/")
            or source.get("architecture_significance") == "VerificationOnly"
            or target.get("architecture_significance") == "VerificationOnly"
        ):
            continue
        violation_type = None
        description = None
        if source_layer == "Domain" and target_layer in {"Infrastructure", "DataAccess", "Integration", "API", "Presentation/UI"}:
            violation_type = "domain_depends_on_outer_layer"
            description = f"Domain component {edge['from']} depends on {target_layer} component {edge['to']}."
        elif source.get("component_type") == "Controller" and target.get("component_type") == "Repository":
            violation_type = "controller_direct_repository_dependency"
            description = f"Controller-like component {edge['from']} depends directly on repository {edge['to']}."
        elif source_layer == "Application" and target_layer == "Presentation/UI":
            violation_type = "application_depends_on_ui"
            description = f"Application component {edge['from']} depends on UI component {edge['to']}."
        elif source_layer == "Presentation/UI" and target_layer == "DataAccess":
            violation_type = "ui_depends_on_data_access"
            description = f"UI component {edge['from']} depends on data access component {edge['to']}."
        if violation_type:
            violations.append(
                {
                    "type": violation_type,
                    "description": description,
                    "affected_components": [edge["from"], edge["to"]],
                    "source_file": edge.get("source_file"),
                    "line": edge.get("line"),
                    "evidence": edge.get("evidence"),
                    "severity": "Medium",
                    "confidence": min(float(edge.get("confidence", 0.6)), 0.72),
                }
            )

    detected_layer_names = {component.get("layer_guess") for component in components}
    project_categories = {project.get("category") for project in data["project_inventory"].get("projects", [])}
    has_layered_shape = len(detected_layer_names & {"Presentation/UI", "API", "Application", "Domain", "Infrastructure", "DataAccess"}) >= 3
    has_clean_shape = {"Application", "Domain", "Infrastructure"}.issubset(detected_layer_names) and (
        "backend" in project_categories or "frontend" in project_categories
    )
    pattern_candidates = [
        {
            "pattern": "Layered Monolith",
            "evidence": "Multiple projects/layers detected within one solution/repository and shared deployable units.",
            "confidence": 0.78 if has_layered_shape else 0.52,
        },
        {
            "pattern": "Clean Architecture",
            "evidence": "Parsed layers include application/domain/infrastructure-style components; project names are used only as supporting evidence.",
            "confidence": 0.66 if has_clean_shape else 0.42,
        },
        {
            "pattern": "Modular Monolith",
            "evidence": "Multiple module candidates exist inside shared backend/frontend projects; service separation is not established by evidence packs.",
            "confidence": 0.52,
        },
    ]
    detected_layers = [
        {
            "layer": layer,
            "component_count": count,
            "evidence_files": source_files_from_items([component for component in components if component.get("layer_guess") == layer])[:50],
        }
        for layer, count in sorted(Counter(component.get("layer_guess", "Unknown") for component in components).items())
    ]
    return {
        **evidence_header("layering_pattern", source_files_from_items(components), 0.68),
        "extracted_facts": {
            "detected_layer_count": len(detected_layers),
            "layer_dependency_direction_count": len(layer_edges),
            "potential_layer_violation_count": len(violations),
            "candidate_pattern_count": len(pattern_candidates),
        },
        "detected_layers": detected_layers,
        "dependency_direction": [
            {"from_layer": source, "to_layer": target, "dependency_count": count}
            for (source, target), count in sorted(layer_edges.items())
        ],
        "layer_violations": violations,
        "candidate_patterns": pattern_candidates,
        "unknowns": [
            "Architecture pattern is not finalized in Step 3; candidates are evidence for later final architecture review.",
            "Layer violation detection uses parsed dependency candidates and may include false positives from interface/base-class resolution.",
        ],
        "open_questions": [
            "Review potential layer violations before finalizing the architecture-violation register.",
            "Confirm whether the detected application/domain/infrastructure split is intentional architecture or incidental project organization.",
        ],
    }


def build_external_boundary_pack(data: dict[str, Any]) -> dict[str, Any]:
    project_inventory = data["project_inventory"]
    dependencies = data["dependencies"]
    components = data["components"]
    external_dependencies = []

    for service in project_inventory.get("docker_compose_services", []):
        if service.get("name", "").lower() in {"sqlserver", "postgres", "mysql", "redis"}:
            external_dependencies.append(
                {
                    "target_system": service["name"],
                    "type": "database_or_infrastructure_service",
                    "protocol": "unknown",
                    "called_from": "deployable units in docker-compose",
                    "module_guess": "Infrastructure",
                    "evidence": [{"file": service.get("file"), "reason": "docker compose service detected in inventory"}],
                    "confidence": 0.82,
                    "unknowns": ["Runtime connection details are not resolved in evidence-pack generation."],
                }
            )

    for dep in dependencies:
        if is_external_http_dependency(dep):
            external_dependencies.append(
                {
                    "target_system": dep.get("to"),
                    "type": "HTTP_endpoint_or_configured_base_url",
                    "protocol": "HTTP",
                    "called_from": dep.get("from"),
                    "module_guess": "unknown",
                    "evidence": [{"file": dep.get("source_file"), "line": dep.get("line"), "reason": dep.get("evidence")}],
                    "confidence": dep.get("confidence", 0.0),
                    "unknowns": ["Target system purpose/base URL is not fully known from parsed facts alone."],
                }
            )

    packages = {package for project in project_inventory.get("projects", []) for package in project.get("package_references", [])}
    if {"Azure.Identity", "Azure.Extensions.AspNetCore.Configuration.Secrets"} & packages:
        files = [
            project["path"]
            for project in project_inventory.get("projects", [])
            if {"Azure.Identity", "Azure.Extensions.AspNetCore.Configuration.Secrets"} & set(project.get("package_references", []))
        ]
        external_dependencies.append(
            {
                "target_system": "Azure configuration/identity service",
                "type": "possible_external_cloud_dependency",
                "protocol": "SDK",
                "called_from": "project package references",
                "module_guess": "CrossCutting",
                "evidence": [{"file": file, "reason": "Azure package reference detected"} for file in files],
                "confidence": 0.55,
                "unknowns": ["Package references indicate capability, but actual runtime usage/purpose must be confirmed."],
            }
        )

    return {
        **evidence_header("external_boundary", source_files_from_items(dependencies) + project_inventory.get("deployment_files", []), avg_confidence(external_dependencies, 0.6)),
        "extracted_facts": {
            "external_dependency_count": len(external_dependencies),
            "http_call_candidate_count": sum(1 for dep in dependencies if is_external_http_dependency(dep)),
            "docker_compose_service_count": len(project_inventory.get("docker_compose_services", [])),
        },
        "external_dependencies": external_dependencies,
        "unknowns": [
            "External system names/purposes are unknown where evidence only shows configured HTTP paths or package references.",
        ],
        "open_questions": [
            "Confirm the real target system behind configured API base URLs used by frontend HTTP calls.",
            "Confirm whether database or infrastructure services found in deployment files are development-only or production-relevant boundaries.",
        ],
    }


def build_frontend_application_pack(data: dict[str, Any]) -> dict[str, Any]:
    project_inventory = data["project_inventory"]
    components = data["components"]
    entry_points = data["entry_points"]
    dependencies = data["dependencies"]
    frontend_projects = project_inventory.get("frontend_projects", [])
    if not frontend_projects:
        return {
            **evidence_header("frontend_application", [], 0.9),
            "frontend_apps": [],
            "status": "no_frontend_detected",
            "extracted_facts": {"frontend_app_count": 0},
            "unknowns": [],
            "open_questions": [],
        }

    frontend_apps = []
    for project in frontend_projects:
        name = project["name"]
        source_path = project["source_path"]
        project_components = [
            component
            for component in components
            if component.get("project") == name
            or component.get("file", "").startswith(source_path.rstrip("/") + "/")
            or component.get("component_type") in {"FrontendComponent", "FrontendService", "RouteGuard", "StateStore"}
        ]
        routes = [
            entry
            for entry in entry_points
            if entry.get("type") == "FrontendRoute"
            and (entry.get("source_file", "").startswith(source_path.rstrip("/") + "/") or entry.get("owning_component") in {c["name"] for c in project_components})
        ]
        api_calls = [
            dep
            for dep in dependencies
            if is_external_http_dependency(dep)
            and dep.get("source_file", "").startswith(source_path.rstrip("/") + "/")
        ]
        state_clues = [
            {
                "component": component["name"],
                "file": component["file"],
                "reason": "component name/base class suggests state or authentication-state handling",
                "confidence": component.get("confidence", 0.0),
            }
            for component in project_components
            if "State" in component.get("name", "") or "StateProvider" in (component.get("base_class") or "") or component.get("component_type") == "StateStore"
        ]
        frontend_apps.append(
            {
                "name": name,
                "framework": project.get("framework", "unknown"),
                "source_path": source_path,
                "routes": routes,
                "components": [
                    {
                        "component_id": component.get("component_id"),
                        "name": component["name"],
                        "type": component.get("component_type"),
                        "layer": component.get("layer_guess"),
                        "module_guess": component.get("module_guess"),
                        "file": component["file"],
                        "confidence": component.get("confidence", 0.0),
                    }
                    for component in project_components
                ],
                "api_calls": api_calls,
                "state_management_clues": state_clues,
                "confidence": project.get("confidence", 0.0),
                "evidence": project.get("evidence", []),
            }
        )
    return {
        **evidence_header("frontend_application", source_files_from_items(components + entry_points + dependencies), avg_confidence(frontend_projects, 0.8)),
        "status": "frontend_detected",
        "extracted_facts": {
            "frontend_app_count": len(frontend_apps),
            "frontend_route_count": sum(len(app["routes"]) for app in frontend_apps),
            "frontend_component_count": sum(len(app["components"]) for app in frontend_apps),
            "frontend_api_call_count": sum(len(app["api_calls"]) for app in frontend_apps),
            "state_management_clue_count": sum(len(app["state_management_clues"]) for app in frontend_apps),
        },
        "frontend_apps": frontend_apps,
        "unknowns": [
            "Frontend API base URL and target system purpose are not fully resolved from parsed facts alone.",
        ],
        "open_questions": [
            "Confirm whether each detected frontend project is deployed independently or hosted by another application project.",
            "Confirm whether frontend route coverage is complete for components without @page directives.",
        ],
    }


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root).resolve()
    inventory_root = output_root / "inventory"
    parsed_root = output_root / "parsed"
    evidence_root = output_root / "evidence-packs"

    data = {
        "file_inventory": load_json(inventory_root / "file-inventory.json"),
        "project_inventory": load_json(inventory_root / "project-inventory.json"),
        "language_summary": load_json(inventory_root / "language-summary.json"),
        "ignored_report": load_json(inventory_root / "ignored-files-report.json"),
        "source_chunk_index": load_json(parsed_root / "source-chunk-index.json") if (parsed_root / "source-chunk-index.json").exists() else {},
        "symbol_registry": load_json(parsed_root / "symbol-registry.json"),
        "route_registry": load_json(parsed_root / "route-registry.json"),
        "dependency_candidates": load_json(parsed_root / "dependency-candidates.json"),
        "entry_point_candidates": load_json(parsed_root / "entry-point-candidates.json"),
        "roslyn_semantic_facts": load_json(parsed_root / "roslyn-semantic-facts.json") if (parsed_root / "roslyn-semantic-facts.json").exists() else {},
    }
    data["components"] = merge_semantic_components(
        data["symbol_registry"].get("components", []),
        data.get("roslyn_semantic_facts"),
    )
    data["routes"] = data["route_registry"].get("routes", [])
    data["dependencies"] = merge_semantic_dependencies(
        data["dependency_candidates"].get("dependencies", []),
        data.get("roslyn_semantic_facts"),
    )
    data["entry_points"] = data["entry_point_candidates"].get("entry_points", [])
    data["chunk_lookup"] = build_chunk_lookup(data.get("source_chunk_index"))

    component_edges = resolved_component_edges(data["components"], data["dependencies"])
    module_edges = module_dependencies_from_edges(data["components"], data["dependencies"], component_edges)

    packs = {
        "system-inventory-pack.json": build_system_inventory_pack(data),
        "module-boundary-pack.json": build_module_boundary_pack(data, module_edges),
        "component-registry-pack.json": build_component_registry_pack(data),
        "dependency-pack.json": build_dependency_pack(data, component_edges, module_edges),
        "entry-point-pack.json": build_entry_point_pack(data),
        "call-flow-pack.json": build_call_flow_pack(data, component_edges),
        "layering-pattern-pack.json": build_layering_pattern_pack(data, component_edges, module_edges),
        "external-boundary-pack.json": build_external_boundary_pack(data),
        "frontend-application-pack.json": build_frontend_application_pack(data),
    }
    for filename, payload in packs.items():
        write_json(evidence_root / filename, payload)

    summary = {
        "output_directory": str(evidence_root),
        "files_generated": sorted(packs),
        "system_apps_detected": data["project_inventory"].get("summary", {}).get("project_count", 0),
        "module_candidates": len(packs["module-boundary-pack.json"].get("module_candidates", [])),
        "components_grouped": len(data["components"]),
        "dependencies": len(data["dependencies"]),
        "entry_points": len(data["entry_points"]),
        "call_flows": len(packs["call-flow-pack.json"].get("flows", [])),
        "potential_architecture_violations": packs["layering-pattern-pack.json"].get("extracted_facts", {}).get("potential_layer_violation_count", 0),
    }
    print(json.dumps(summary, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate evidence packs from inventory and parsed facts.")
    parser.add_argument(
        "--output-root",
        default="architecture-output",
        help="Architecture output root. Defaults to ./architecture-output.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
