#!/usr/bin/env python3
"""
Generate enterprise forward-engineering artifacts from final architecture outputs.

This phase does not read or modify legacy application source code. It consumes
the source-backed final JSON/Markdown artifacts and turns them into planning
inputs for modernization, migration sequencing, API preservation, data ownership
review, confidence review, architecture decisions, and backlog creation.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_FILES = [
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

GENERIC_TOKENS = {
    "api",
    "app",
    "base",
    "blazor",
    "client",
    "component",
    "config",
    "configuration",
    "controller",
    "create",
    "custom",
    "delete",
    "default",
    "details",
    "dto",
    "edit",
    "endpoint",
    "endpoints",
    "external",
    "functional",
    "generate",
    "get",
    "handler",
    "helper",
    "helpers",
    "id",
    "imports",
    "index",
    "item",
    "items",
    "layout",
    "list",
    "model",
    "models",
    "page",
    "pages",
    "public",
    "query",
    "request",
    "response",
    "src",
    "start",
    "service",
    "services",
    "shared",
    "test",
    "tests",
    "type",
    "types",
    "update",
    "view",
    "views",
    "web",
}

TECHNICAL_CAPABILITY_NAMES = {
    "Application",
    "Cache",
    "Cached",
    "Configure",
    "Constants",
    "Custom",
    "Email",
    "File",
    "Imports",
    "Program",
    "Read",
    "Token",
    "Uri",
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def unique(values: list[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        marker = json.dumps(value, sort_keys=True, default=str)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def short_list(values: list[Any], limit: int = 8) -> str:
    cleaned = [str(value) for value in values if value not in (None, "", "unknown", "Unknown")]
    if not cleaned:
        return "none detected"
    if len(cleaned) <= limit:
        return ", ".join(cleaned)
    return ", ".join(cleaned[:limit]) + f", and {len(cleaned) - limit} more"


def source_files_from_evidence(items: list[dict[str, Any]], limit: int = 8) -> list[str]:
    files: list[str] = []
    for item in items:
        file = item.get("file") or item.get("source_file")
        if file:
            files.append(file)
    return unique(files)[:limit]


def split_tokens(value: str) -> list[str]:
    value = re.sub(r"[_\-/\.]+", " ", str(value or ""))
    raw = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", value)
    tokens = []
    for token in raw:
        lower = token.lower()
        if len(lower) < 3:
            continue
        if lower in GENERIC_TOKENS:
            continue
        tokens.append(token[0].upper() + token[1:])
    return tokens


def capability_name_for_module(module: dict[str, Any]) -> str:
    name_tokens = split_tokens(module.get("name", ""))
    if name_tokens:
        return name_tokens[0]
    folder_tokens: list[str] = []
    for folder in module.get("source_folders", []):
        folder_tokens.extend(split_tokens(folder))
    if folder_tokens:
        return Counter(folder_tokens).most_common(1)[0][0]
    component_tokens: list[str] = []
    for component in module.get("main_components", []):
        component_tokens.extend(split_tokens(component.get("name", "")))
    if component_tokens:
        return Counter(component_tokens).most_common(1)[0][0]
    return "Unclassified"


def component_lookup(components: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup = {}
    for component in components:
        lookup[component.get("name")] = component
    return lookup


def module_lookup(modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {module.get("name"): module for module in modules}


def risk_matches_module(risk: dict[str, Any], module_name: str) -> bool:
    affected = str(risk.get("affected_module", ""))
    return module_name == affected or module_name in [item.strip() for item in affected.split(",")]


def risk_matches_component(risk: dict[str, Any], component_name: str) -> bool:
    affected = str(risk.get("affected_component", ""))
    return component_name == affected or component_name in [item.strip() for item in affected.split(",")]


def decision_for_interface(interface: dict[str, Any]) -> str:
    if interface.get("type") != "HTTP_API":
        return "review"
    if interface.get("method") == "unknown" or interface.get("confidence", 0) < 0.7:
        return "review"
    if "{" in str(interface.get("path_or_name", "")) and interface.get("confidence", 0) < 0.85:
        return "review"
    return "preserve"


def decision_for_capability(capability: dict[str, Any]) -> str:
    if capability.get("classification") in {"TechnicalSupport", "TestVerification"}:
        return "review"
    if capability["risk_count"] >= 3 or capability["weak_module_count"] > 0:
        return "review_before_extraction"
    if capability["interface_count"] > 0 and capability["efferent_coupling"] <= 2:
        return "candidate_for_early_modernization"
    if capability["data_access_component_count"] > 0 and capability["interface_count"] == 0:
        return "preserve_as_internal_until_ownership_confirmed"
    return "review"


def classify_capability(bucket: dict[str, Any]) -> str:
    sources = [str(file) for file in bucket.get("source_files", [])]
    if sources and all(file.startswith("tests/") for file in sources):
        return "TestVerification"
    if bucket["name"] in TECHNICAL_CAPABILITY_NAMES:
        return "TechnicalSupport"
    if bucket.get("data_access_components") or bucket.get("repositories"):
        return "DataInfrastructure"
    if bucket.get("entities"):
        return "DomainCapabilityCandidate"
    if bucket.get("interfaces"):
        return "InterfaceCapabilityCandidate"
    if any(component.get("layer") == "Presentation/UI" for component in bucket.get("components", [])):
        return "UICapabilityCandidate"
    return "ApplicationCapabilityCandidate"


def load_final(output_root: Path) -> dict[str, Any]:
    final_root = output_root / "final"
    return {
        "system": load_json(final_root / "system-inventory.json"),
        "modules": load_json(final_root / "module-boundary-map.json"),
        "components": load_json(final_root / "component-registry.json"),
        "dependencies": load_json(final_root / "dependency-graph.json"),
        "interfaces": load_json(final_root / "application-interface-catalogue.json"),
        "flows": load_json(final_root / "call-flow-map.json"),
        "violations": load_json(final_root / "architecture-violation-register.json"),
        "risks": load_json(final_root / "application-risk-register.json"),
        "open_questions_md": read_text(final_root / "open-questions.md"),
        "quality_review_md": read_text(final_root / "quality-review.md"),
        "pattern_md": read_text(final_root / "architecture-pattern-report.md"),
    }


def build_business_capability_map(data: dict[str, Any]) -> dict[str, Any]:
    modules = data["modules"].get("modules", [])
    components = data["components"].get("components", [])
    interfaces = data["interfaces"].get("interfaces", [])
    risks = data["risks"].get("risks", [])
    comp_by_name = component_lookup(components)

    buckets: dict[str, dict[str, Any]] = {}
    module_to_capability: dict[str, str] = {}
    for module in modules:
        name = capability_name_for_module(module)
        module_to_capability[module["name"]] = name
        bucket = buckets.setdefault(
            name,
            {
                "name": name,
                "modules": [],
                "components": [],
                "interfaces": [],
                "entities": [],
                "services": [],
                "repositories": [],
                "data_access_components": [],
                "risks": [],
                "source_files": [],
                "afferent_coupling": 0,
                "efferent_coupling": 0,
                "weak_module_count": 0,
                "confidence_values": [],
            },
        )
        bucket["modules"].append(
            {
                "module_id": module.get("module_id"),
                "name": module.get("name"),
                "boundary_quality": module.get("boundary_quality"),
                "migration_readiness": module.get("migration_readiness"),
                "afferent_coupling": module.get("afferent_coupling", 0),
                "efferent_coupling": module.get("efferent_coupling", 0),
                "confidence": module.get("confidence", 0.0),
            }
        )
        bucket["afferent_coupling"] += int(module.get("afferent_coupling", 0))
        bucket["efferent_coupling"] += int(module.get("efferent_coupling", 0))
        if module.get("boundary_quality") in {"Weak", "Unknown"}:
            bucket["weak_module_count"] += 1
        bucket["confidence_values"].append(float(module.get("confidence", 0.0)))
        bucket["source_files"].extend(source_files_from_evidence(module.get("evidence", []), 20))
        for item in module.get("main_components", []):
            comp = comp_by_name.get(item.get("name"), item)
            component_record = {
                "component_id": item.get("component_id") or comp.get("component_id"),
                "name": item.get("name"),
                "type": item.get("type") or comp.get("type"),
                "layer": item.get("layer") or comp.get("layer"),
                "file": item.get("file") or comp.get("file"),
            }
            bucket["components"].append(component_record)
            bucket["source_files"].append(component_record.get("file"))
            if component_record["type"] == "Entity":
                bucket["entities"].append(component_record)
            if component_record["type"] == "Service":
                bucket["services"].append(component_record)
            if component_record["type"] == "Repository":
                bucket["repositories"].append(component_record)
            if component_record["layer"] in {"DataAccess", "Infrastructure"}:
                bucket["data_access_components"].append(component_record)

    for interface in interfaces:
        cap_name = module_to_capability.get(interface.get("owner_module"), capability_name_for_module({"name": interface.get("owner_module", "")}))
        bucket = buckets.setdefault(
            cap_name,
            {
                "name": cap_name,
                "modules": [],
                "components": [],
                "interfaces": [],
                "entities": [],
                "services": [],
                "repositories": [],
                "data_access_components": [],
                "risks": [],
                "source_files": [],
                "afferent_coupling": 0,
                "efferent_coupling": 0,
                "weak_module_count": 0,
                "confidence_values": [],
            },
        )
        bucket["interfaces"].append(
            {
                "interface_id": interface.get("interface_id"),
                "type": interface.get("type"),
                "method": interface.get("method"),
                "path_or_name": interface.get("path_or_name"),
                "entry_component": interface.get("entry_component"),
                "source_file": interface.get("source_file"),
                "confidence": interface.get("confidence", 0.0),
            }
        )
        bucket["source_files"].append(interface.get("source_file"))
        bucket["confidence_values"].append(float(interface.get("confidence", 0.0)))

    for risk in risks:
        matched = set()
        for module in modules:
            if risk_matches_module(risk, module["name"]):
                matched.add(module_to_capability.get(module["name"], "Unclassified"))
        for component_name in str(risk.get("affected_component", "")).split(","):
            comp = comp_by_name.get(component_name.strip())
            if comp:
                matched.add(module_to_capability.get(comp.get("module"), capability_name_for_module({"name": comp.get("module", "")})))
        if not matched and risk.get("affected_module") in {"multiple", "unknown"}:
            continue
        for cap_name in matched:
            if cap_name in buckets:
                buckets[cap_name]["risks"].append(
                    {
                        "risk_id": risk.get("risk_id"),
                        "category": risk.get("category"),
                        "description": risk.get("description"),
                        "severity": risk.get("severity"),
                        "evidence": risk.get("evidence", []),
                    }
                )

    capabilities = []
    for idx, bucket in enumerate(sorted(buckets.values(), key=lambda item: (-len(item["components"]), item["name"])), start=1):
        confidence_values = bucket.pop("confidence_values")
        confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else 0.45
        bucket["components"] = unique(bucket["components"])
        bucket["interfaces"] = unique(bucket["interfaces"])
        bucket["entities"] = unique(bucket["entities"])
        bucket["services"] = unique(bucket["services"])
        bucket["repositories"] = unique(bucket["repositories"])
        bucket["data_access_components"] = unique(bucket["data_access_components"])
        bucket["risks"] = unique(bucket["risks"])
        bucket["source_files"] = unique([file for file in bucket["source_files"] if file])[:20]
        bucket["capability_id"] = f"CAP-{idx:03d}"
        bucket["module_count"] = len(bucket["modules"])
        bucket["component_count"] = len(bucket["components"])
        bucket["interface_count"] = len(bucket["interfaces"])
        bucket["risk_count"] = len(bucket["risks"])
        bucket["entity_count"] = len(bucket["entities"])
        bucket["data_access_component_count"] = len(bucket["data_access_components"])
        bucket["classification"] = classify_capability(bucket)
        bucket["forward_engineering_decision"] = decision_for_capability(bucket)
        bucket["confidence"] = confidence
        capabilities.append(bucket)

    return {
        "generated_at": utc_now(),
        "source_final_artifacts": [
            "architecture-output/final/module-boundary-map.json",
            "architecture-output/final/component-registry.json",
            "architecture-output/final/application-interface-catalogue.json",
            "architecture-output/final/application-risk-register.json",
        ],
        "summary": {
            "capability_count": len(capabilities),
            "module_count": len(modules),
            "component_count": len(components),
            "interface_count": len(interfaces),
            "risk_count": len(risks),
        },
        "capabilities": capabilities,
        "open_questions": [
            "Capability grouping is evidence-derived from module/component names and source folders; confirm with business/product owners before using as final bounded contexts.",
            "Capabilities with weak modules, partial flows, or shared data access need architecture review before service extraction.",
        ],
    }


def build_capability_markdown(capability_map: dict[str, Any]) -> str:
    lines = [
        "# Business Capability Map",
        "",
        "This file groups evidence-derived module candidates into higher-level forward-engineering capability candidates. These are not final bounded contexts until reviewed by architects and product/domain owners.",
        "",
        "## Summary",
        "",
        f"- Capability candidates: {capability_map['summary']['capability_count']}",
        f"- Module candidates grouped: {capability_map['summary']['module_count']}",
        f"- Components considered: {capability_map['summary']['component_count']}",
        f"- Interfaces considered: {capability_map['summary']['interface_count']}",
        "",
        "## Capability Candidates",
        "",
        "| Capability | Class | Modules | Components | Interfaces | Data Components | Risks | Coupling | Forward Decision | Confidence | Evidence |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for cap in capability_map["capabilities"][:40]:
        coupling = cap["afferent_coupling"] + cap["efferent_coupling"]
        evidence = short_list(cap["source_files"], 3)
        lines.append(
            f"| {cap['capability_id']} {cap['name']} | {cap['classification']} | {cap['module_count']} | {cap['component_count']} | "
            f"{cap['interface_count']} | {cap['data_access_component_count']} | {cap['risk_count']} | {coupling} | "
            f"{cap['forward_engineering_decision']} | {cap['confidence']} | {evidence} |"
        )
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- Use this map to discuss future module/service boundaries.",
            "- Prefer capabilities with low coupling, clear interfaces, and few risks as earlier modernization candidates.",
            "- Do not split capabilities with shared data ownership or weak evidence until open questions are resolved.",
        ]
    )
    return "\n".join(lines)


def build_api_contract_map(data: dict[str, Any], capability_map: dict[str, Any]) -> dict[str, Any]:
    components = data["components"].get("components", [])
    modules = data["modules"].get("modules", [])
    interfaces = data["interfaces"].get("interfaces", [])
    comp_ids = {component.get("name"): component.get("component_id") for component in components}
    module_ids = {module.get("name"): module.get("module_id") for module in modules}
    capability_by_module = {}
    for cap in capability_map["capabilities"]:
        for module in cap["modules"]:
            capability_by_module[module["name"]] = {"capability_id": cap["capability_id"], "name": cap["name"]}

    contracts = []
    for idx, interface in enumerate(interfaces, start=1):
        owner_module = interface.get("owner_module", "Unknown")
        cap = capability_by_module.get(owner_module, {"capability_id": "CAP-unknown", "name": "unknown"})
        decision = decision_for_interface(interface)
        contracts.append(
            {
                "contract_id": f"API-CONTRACT-{idx:03d}",
                "interface_id": interface.get("interface_id"),
                "type": interface.get("type"),
                "method": interface.get("method"),
                "path_or_name": interface.get("path_or_name"),
                "owner_module_id": module_ids.get(owner_module, "MOD-unknown"),
                "owner_module": owner_module,
                "owner_capability_id": cap["capability_id"],
                "owner_capability": cap["name"],
                "entry_component_id": comp_ids.get(interface.get("entry_component"), "COMP-unknown"),
                "entry_component": interface.get("entry_component"),
                "called_service": interface.get("called_service", []),
                "source_file": interface.get("source_file"),
                "line": interface.get("line"),
                "preserve_redesign_review": decision,
                "forward_engineering_note": (
                    "Preserve behavior contract or provide an explicit compatibility plan."
                    if decision == "preserve"
                    else "Review before treating as a stable future contract."
                ),
                "confidence": interface.get("confidence", 0.0),
                "evidence": interface.get("evidence", []),
                "open_questions": interface.get("open_questions", []),
            }
        )
    return {
        "generated_at": utc_now(),
        "source_final_artifacts": [
            "architecture-output/final/application-interface-catalogue.json",
            "architecture-output/final/component-registry.json",
            "architecture-output/final/module-boundary-map.json",
            "architecture-output/final/business-capability-map.json",
        ],
        "summary": {
            "contract_count": len(contracts),
            "preserve_count": sum(1 for item in contracts if item["preserve_redesign_review"] == "preserve"),
            "review_count": sum(1 for item in contracts if item["preserve_redesign_review"] == "review"),
        },
        "api_contracts": contracts,
    }


def build_module_consolidation_map(capability_map: dict[str, Any]) -> dict[str, Any]:
    consolidated = []
    for idx, cap in enumerate(capability_map["capabilities"], start=1):
        module_names = [module["name"] for module in cap.get("modules", [])]
        readiness = Counter(module.get("migration_readiness", "Unknown") for module in cap.get("modules", []))
        boundary = Counter(module.get("boundary_quality", "Unknown") for module in cap.get("modules", []))
        if cap["module_count"] <= 1 and cap["component_count"] <= 2 and cap["classification"] not in {"DataInfrastructure", "InterfaceCapabilityCandidate"}:
            consolidation_action = "keep_as_component_or_submodule_candidate"
        elif cap["weak_module_count"] or cap["risk_count"] or cap["efferent_coupling"] > 5:
            consolidation_action = "review_before_consolidating"
        else:
            consolidation_action = "consolidate_as_candidate_module"
        consolidated.append(
            {
                "consolidated_module_id": f"CMOD-{idx:03d}",
                "name": cap["name"],
                "capability_id": cap["capability_id"],
                "classification": cap["classification"],
                "consolidation_action": consolidation_action,
                "source_module_count": cap["module_count"],
                "source_modules": cap.get("modules", []),
                "source_module_names": module_names,
                "component_count": cap["component_count"],
                "interface_count": cap["interface_count"],
                "data_access_component_count": cap["data_access_component_count"],
                "risk_count": cap["risk_count"],
                "afferent_coupling": cap["afferent_coupling"],
                "efferent_coupling": cap["efferent_coupling"],
                "boundary_quality_distribution": dict(boundary),
                "migration_readiness_distribution": dict(readiness),
                "evidence_files": cap.get("source_files", []),
                "confidence": cap["confidence"],
                "open_questions": [
                    "Confirm whether these source module candidates represent one future module/service boundary."
                ]
                if consolidation_action != "keep_as_component_or_submodule_candidate"
                else [],
            }
        )
    return {
        "generated_at": utc_now(),
        "source_final_artifacts": [
            "architecture-output/final/business-capability-map.json",
            "architecture-output/final/module-boundary-map.json",
        ],
        "summary": {
            "consolidated_module_candidate_count": len(consolidated),
            "consolidate_count": sum(1 for item in consolidated if item["consolidation_action"] == "consolidate_as_candidate_module"),
            "review_count": sum(1 for item in consolidated if item["consolidation_action"] == "review_before_consolidating"),
            "keep_submodule_count": sum(1 for item in consolidated if item["consolidation_action"] == "keep_as_component_or_submodule_candidate"),
        },
        "consolidated_modules": consolidated,
    }


def build_module_consolidation_markdown(consolidation_map: dict[str, Any]) -> str:
    lines = [
        "# Module Consolidation Map",
        "",
        "This file consolidates fine-grained static module candidates into higher-level module candidates for enterprise architecture review.",
        "",
        "## Summary",
        "",
        f"- Consolidated candidates: {consolidation_map['summary']['consolidated_module_candidate_count']}",
        f"- Consolidate now candidates: {consolidation_map['summary']['consolidate_count']}",
        f"- Review before consolidation: {consolidation_map['summary']['review_count']}",
        f"- Keep as component/submodule candidates: {consolidation_map['summary']['keep_submodule_count']}",
        "",
        "## Consolidation Candidates",
        "",
        "| Consolidated Module | Action | Class | Source Modules | Components | Interfaces | Data | Risks | Coupling | Confidence | Evidence |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in consolidation_map["consolidated_modules"][:60]:
        coupling = item["afferent_coupling"] + item["efferent_coupling"]
        lines.append(
            f"| {item['consolidated_module_id']} {item['name']} | {item['consolidation_action']} | {item['classification']} | "
            f"{item['source_module_count']} | {item['component_count']} | {item['interface_count']} | "
            f"{item['data_access_component_count']} | {item['risk_count']} | {coupling} | {item['confidence']} | "
            f"{short_list(item['evidence_files'], 3)} |"
        )
    lines.extend(
        [
            "",
            "## How To Use",
            "",
            "- Use `consolidate_as_candidate_module` items as starting points for future modular boundaries.",
            "- Use `review_before_consolidating` items for architecture workshops because they have coupling, risk, weak boundary, or data ownership concerns.",
            "- Use `keep_as_component_or_submodule_candidate` items as internal implementation details unless business ownership says otherwise.",
        ]
    )
    return "\n".join(lines)


def build_service_boundary_options(data: dict[str, Any], capability_map: dict[str, Any]) -> str:
    caps = capability_map["capabilities"]
    early = [cap for cap in caps if cap["forward_engineering_decision"] == "candidate_for_early_modernization"][:8]
    review = [cap for cap in caps if cap["forward_engineering_decision"] == "review_before_extraction"][:8]
    internal = [cap for cap in caps if cap["forward_engineering_decision"] == "preserve_as_internal_until_ownership_confirmed"][:8]
    pattern = "unknown"
    match = re.search(r"Detected pattern:\s*([^.\n]+)", data.get("pattern_md", ""))
    if match:
        pattern = match.group(1)
    return f"""# Service Boundary Options

Generated from final architecture artifacts. This file provides forward-engineering options; it does not choose a future technology stack.

## Current Architecture Baseline

Detected architecture pattern: {pattern}.

The current evidence shows shared deployables, shared dependencies, and candidate module boundaries. Therefore service boundaries should be selected only after confirming ownership, data access, and call-flow behavior.

## Option A - Preserve As Modular Monolith First

Use when the team needs modernization without immediate service extraction.

Recommended when:

- module boundaries are still candidate-level
- data ownership is shared or unclear
- call flows are partial
- release risk must be minimized

Useful candidates to modularize internally first: {short_list([cap['capability_id'] + ' ' + cap['name'] for cap in early + internal], 10)}.

## Option B - Extract Low-Coupling Interface-Backed Capabilities

Use when a capability has clear interfaces, low coupling, and limited risk evidence.

Candidate capabilities:

{chr(10).join(f"- {cap['capability_id']} {cap['name']}: {cap['interface_count']} interfaces, coupling {cap['afferent_coupling'] + cap['efferent_coupling']}, confidence {cap['confidence']}" for cap in early) if early else "- none detected"}

## Option C - Stabilize Shared Data/Infrastructure Before Extraction

Use when data access or infrastructure components are shared across capabilities.

Capabilities to keep internal until ownership is confirmed:

{chr(10).join(f"- {cap['capability_id']} {cap['name']}: data components {cap['data_access_component_count']}, risks {cap['risk_count']}" for cap in internal) if internal else "- none detected"}

## Option D - Defer High-Risk / Weak Boundary Candidates

Poor first extraction candidates:

{chr(10).join(f"- {cap['capability_id']} {cap['name']}: weak modules {cap['weak_module_count']}, risks {cap['risk_count']}, coupling {cap['afferent_coupling'] + cap['efferent_coupling']}" for cap in review) if review else "- none detected"}

## Recommended Enterprise Use

Start with Option A as a stabilization path, use Option B only for low-coupling candidates, and defer Option D candidates until open questions and partial flows are resolved.
"""


def build_migration_wave_plan(capability_map: dict[str, Any], api_contract_map: dict[str, Any], data: dict[str, Any]) -> str:
    caps = capability_map["capabilities"]
    early = [cap for cap in caps if cap["forward_engineering_decision"] == "candidate_for_early_modernization"][:8]
    review = [cap for cap in caps if cap["forward_engineering_decision"] == "review_before_extraction"][:8]
    preserve_contracts = [item for item in api_contract_map["api_contracts"] if item["preserve_redesign_review"] == "preserve"][:12]
    partial_count = data["flows"].get("summary", {}).get("partial_flow_count", 0)
    return f"""# Migration Wave Plan

This is a planning sequence derived from architecture evidence. It is not an implementation schedule.

## Wave 0 - Architecture Stabilization

Goals:

- confirm open questions
- review {partial_count} partial call flows
- confirm external boundary ownership
- decide whether test-project components remain in final architecture views
- add contract tests for preserved APIs

API contracts to stabilize first:

{chr(10).join(f"- {item['method']} {item['path_or_name']} ({item['contract_id']}, owner {item['entry_component_id']} {item['entry_component']})" for item in preserve_contracts) if preserve_contracts else "- none detected"}

## Wave 1 - Low-Coupling Capability Modernization

Candidate capabilities:

{chr(10).join(f"- {cap['capability_id']} {cap['name']}: interfaces {cap['interface_count']}, coupling {cap['afferent_coupling'] + cap['efferent_coupling']}, evidence {short_list(cap['source_files'], 2)}" for cap in early[:5]) if early else "- none detected"}

## Wave 2 - Shared Contract And UI/API Alignment

Goals:

- preserve or explicitly redesign frontend/API contracts
- map UI flows to preserved API contracts
- review all `review` API contracts before implementation

Review contracts:

{short_list([item['contract_id'] + ' ' + str(item['path_or_name']) for item in api_contract_map['api_contracts'] if item['preserve_redesign_review'] == 'review'], 12)}

## Wave 3 - Data Ownership And Infrastructure Refactoring

Goals:

- identify entities and repositories shared across capabilities
- avoid extracting services with unresolved data ownership
- clarify persistence ownership before choosing service boundaries

## Wave 4 - High-Risk Capability Extraction Or Redesign

Defer until after earlier waves:

{chr(10).join(f"- {cap['capability_id']} {cap['name']}: risks {cap['risk_count']}, weak modules {cap['weak_module_count']}, coupling {cap['afferent_coupling'] + cap['efferent_coupling']}" for cap in review[:8]) if review else "- none detected"}
"""


def build_preserve_redesign_retire_map(data: dict[str, Any], capability_map: dict[str, Any], api_contract_map: dict[str, Any]) -> str:
    risks = data["risks"].get("risks", [])
    violations = data["violations"].get("violations", [])
    preserve_contracts = [item for item in api_contract_map["api_contracts"] if item["preserve_redesign_review"] == "preserve"][:15]
    review_contracts = [item for item in api_contract_map["api_contracts"] if item["preserve_redesign_review"] == "review"][:15]
    review_caps = [cap for cap in capability_map["capabilities"] if cap["forward_engineering_decision"] == "review_before_extraction"][:12]
    return f"""# Preserve / Redesign / Retire Map

## Preserve

Preserve behavior or provide explicit compatibility plans for these detected interfaces:

{chr(10).join(f"- {item['contract_id']}: {item['method']} {item['path_or_name']} owned by {item['entry_component_id']} {item['entry_component']} in {item['owner_capability_id']} {item['owner_capability']}" for item in preserve_contracts) if preserve_contracts else "- none detected"}

## Redesign

Do not blindly carry these issues forward:

{chr(10).join(f"- {risk.get('risk_id')}: {risk.get('description')}" for risk in risks[:10]) if risks else "- none detected"}

Architecture violations:

{chr(10).join(f"- {item.get('violation_id')}: {item.get('description')}" for item in violations[:10]) if violations else "- none detected"}

## Review

Review these before treating them as stable future design inputs:

{chr(10).join(f"- {item['contract_id']}: {item['method']} {item['path_or_name']} ({item['forward_engineering_note']})" for item in review_contracts) if review_contracts else "- no API contracts require review"}

Capability boundaries needing review:

{chr(10).join(f"- {cap['capability_id']} {cap['name']}: decision {cap['forward_engineering_decision']}, risks {cap['risk_count']}, weak modules {cap['weak_module_count']}" for cap in review_caps) if review_caps else "- none detected"}

## Retire

No component or API is marked for retirement from static architecture evidence alone. Retirement requires usage, telemetry, production logs, or explicit product-owner confirmation.
"""


def build_data_ownership_map(data: dict[str, Any], capability_map: dict[str, Any]) -> str:
    components = data["components"].get("components", [])
    module_to_cap = {}
    for cap in capability_map["capabilities"]:
        for module in cap["modules"]:
            module_to_cap[module["name"]] = cap
    entities = [component for component in components if component.get("type") == "Entity"]
    repositories = [component for component in components if component.get("type") == "Repository"]
    data_components = [component for component in components if component.get("layer") in {"DataAccess", "Infrastructure"}]

    lines = [
        "# Data Ownership Map",
        "",
        "This is application-architecture ownership evidence, not a database design document.",
        "",
        "## Entity Ownership Candidates",
        "",
        "| Entity | Component ID | Module | Capability | File | Confidence |",
        "|---|---|---|---|---|---:|",
    ]
    for entity in entities:
        cap = module_to_cap.get(entity.get("module"), {})
        lines.append(
            f"| {entity.get('name')} | {entity.get('component_id')} | {entity.get('module')} | "
            f"{cap.get('capability_id', 'CAP-unknown')} {cap.get('name', 'unknown')} | {entity.get('file')} | {entity.get('confidence', 0.0)} |"
        )
    lines.extend(
        [
            "",
            "## Repository / Data Access Candidates",
            "",
            "| Component | Component ID | Type | Layer | Module | Capability | File | Risk Note |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for component in unique(repositories + data_components):
        cap = module_to_cap.get(component.get("module"), {})
        risk_note = "review shared ownership" if component.get("type") == "Repository" or component.get("layer") == "DataAccess" else "review"
        lines.append(
            f"| {component.get('name')} | {component.get('component_id')} | {component.get('type')} | {component.get('layer')} | "
            f"{component.get('module')} | {cap.get('capability_id', 'CAP-unknown')} {cap.get('name', 'unknown')} | {component.get('file')} | {risk_note} |"
        )
    lines.extend(
        [
            "",
            "## Forward Engineering Guidance",
            "",
            "- Do not extract a capability as a separate service until entity and repository ownership are confirmed.",
            "- Shared repositories or data-access abstractions should be wrapped, split, or explicitly owned before service extraction.",
            "- Use this map with `dependency-graph.json` and `application-risk-register.json` before choosing persistence boundaries.",
        ]
    )
    return "\n".join(lines)


def load_optional_runtime_execution(output_root: Path) -> dict[str, Any] | None:
    path = output_root / "test-runtime" / "dotnet-test-execution.json"
    if not path.exists():
        return None
    try:
        return load_json(path)
    except Exception:  # noqa: BLE001 - invalid optional evidence is reported as unavailable.
        return None


def build_test_runtime_evidence_map(data: dict[str, Any], capability_map: dict[str, Any], output_root: Path) -> dict[str, Any]:
    components = data["components"].get("components", [])
    runtime_execution = load_optional_runtime_execution(output_root)
    module_to_cap = {}
    for cap in capability_map["capabilities"]:
        for module in cap["modules"]:
            module_to_cap[module["name"]] = cap

    test_components = [component for component in components if str(component.get("file", "")).startswith("tests/")]
    by_capability: dict[str, dict[str, Any]] = {}
    for component in test_components:
        cap = module_to_cap.get(component.get("module"), {"capability_id": "CAP-unknown", "name": "unknown"})
        key = cap.get("capability_id", "CAP-unknown")
        bucket = by_capability.setdefault(
            key,
            {
                "capability_id": cap.get("capability_id", "CAP-unknown"),
                "capability": cap.get("name", "unknown"),
                "test_components": [],
                "source_files": [],
            },
        )
        bucket["test_components"].append(
            {
                "component_id": component.get("component_id"),
                "name": component.get("name"),
                "type": component.get("type"),
                "module": component.get("module"),
                "file": component.get("file"),
                "confidence": component.get("confidence", 0.0),
            }
        )
        bucket["source_files"].append(component.get("file"))

    capabilities = []
    for bucket in by_capability.values():
        bucket["test_component_count"] = len(bucket["test_components"])
        bucket["source_files"] = unique([file for file in bucket["source_files"] if file])
        bucket["forward_engineering_use"] = "candidate_contract_or_regression_test_source"
        capabilities.append(bucket)

    capabilities.sort(key=lambda item: item["test_component_count"], reverse=True)
    runtime_summary = runtime_execution.get("summary", {}) if runtime_execution else {}
    runtime_executed = bool(runtime_execution and runtime_summary.get("executed_project_count", 0) > 0)
    return {
        "generated_at": utc_now(),
        "runtime_execution_status": "captured_no_build_no_restore" if runtime_executed else "not_run",
        "runtime_execution_reason": (
            "Optional runtime evidence phase executed dotnet test in --no-build --no-restore mode; command results are captured under architecture-output/test-runtime/."
            if runtime_executed
            else "Runtime/test execution was not enabled for this run; static test-source evidence was captured instead."
        ),
        "runtime_execution_evidence": runtime_execution,
        "source_final_artifacts": [
            "architecture-output/final/component-registry.json",
            "architecture-output/final/business-capability-map.json",
            "architecture-output/test-runtime/dotnet-test-execution.json",
        ],
        "summary": {
            "test_component_count": len(test_components),
            "capabilities_with_test_source_evidence": len(capabilities),
            "runtime_executed": runtime_executed,
            "runtime_test_projects": runtime_summary.get("test_project_count", 0),
            "runtime_completed_successfully": runtime_summary.get("completed_successfully", 0),
            "runtime_failed_or_not_available": runtime_summary.get("failed_or_not_available", 0),
        },
        "capability_test_evidence": capabilities,
        "open_questions": [
            (
                "Review no-build/no-restore test failures and rerun in a controlled build environment if needed."
                if runtime_executed and runtime_summary.get("failed_or_not_available", 0)
                else "Confirm whether tests should also be executed in a controlled full-build environment."
            ),
            "Confirm which test components map to behavior contracts that must be preserved in forward engineering.",
        ],
    }


def build_test_runtime_evidence_markdown(test_map: dict[str, Any]) -> str:
    lines = [
        "# Test / Runtime Evidence Map",
        "",
        "This file captures safe test-source evidence for forward engineering and optional no-build/no-restore runtime test evidence when enabled.",
        "",
        "## Summary",
        "",
        f"- Test components detected from source: {test_map['summary']['test_component_count']}",
        f"- Capabilities with test-source evidence: {test_map['summary']['capabilities_with_test_source_evidence']}",
        f"- Runtime executed: {test_map['summary']['runtime_executed']}",
        f"- Runtime test projects: {test_map['summary'].get('runtime_test_projects', 0)}",
        f"- Runtime completed successfully: {test_map['summary'].get('runtime_completed_successfully', 0)}",
        f"- Runtime failed/not available: {test_map['summary'].get('runtime_failed_or_not_available', 0)}",
        "",
        "## Capability Test Evidence",
        "",
        "| Capability | Test Components | Forward Use | Evidence |",
        "|---|---:|---|---|",
    ]
    for item in test_map["capability_test_evidence"][:40]:
        lines.append(
            f"| {item['capability_id']} {item['capability']} | {item['test_component_count']} | "
            f"{item['forward_engineering_use']} | {short_list(item['source_files'], 4)} |"
        )
    lines.extend(
        [
            "",
            "## Runtime Evidence Guidance",
            "",
            "- Run tests only in a controlled workspace where generated outputs are allowed.",
            "- Use test-source evidence to identify candidate regression and API contract tests.",
            "- Treat runtime behavior as unconfirmed until tests or application execution are explicitly run and captured.",
        ]
    )
    return "\n".join(lines)


def build_confidence_report(data: dict[str, Any], capability_map: dict[str, Any], api_contract_map: dict[str, Any], test_runtime_map: dict[str, Any]) -> str:
    components = data["components"].get("components", [])
    interfaces = data["interfaces"].get("interfaces", [])
    flows = data["flows"].get("flows", [])
    dependencies = data["dependencies"]
    unknown_components = sum(1 for component in components if component.get("type") == "Unknown" or component.get("layer") == "Unknown")
    major_unknown_components = sum(
        1
        for component in components
        if component.get("is_major_application_component", True)
        and (component.get("type") == "Unknown" or component.get("layer") == "Unknown")
    )
    partial_flows = sum(1 for flow in flows if flow.get("status") == "partial")
    traced_flows = len(flows) - partial_flows
    invalid_edges = [
        edge for edge in dependencies.get("edges", [])
        if edge.get("from") not in {node.get("id") for node in dependencies.get("nodes", [])}
        or edge.get("to") not in {node.get("id") for node in dependencies.get("nodes", [])}
    ]
    high_conf_contracts = sum(1 for item in api_contract_map["api_contracts"] if item.get("confidence", 0) >= 0.85)
    cap_conf = [cap["confidence"] for cap in capability_map["capabilities"]]
    avg_cap_conf = round(sum(cap_conf) / len(cap_conf), 3) if cap_conf else 0
    return f"""# Confidence Report

## Confidence Summary

| Area | Confidence | Evidence |
|---|---|---|
| Project/deployable inventory | High | `system-inventory.json` and inventory outputs identify project files and deployable candidates. |
| Component detection | Medium/High | {len(components)} components detected; {major_unknown_components} major production components have Unknown type/layer; {unknown_components} total Unknown including support/test artifacts. |
| API/interface detection | Medium/High | {len(interfaces)} interfaces detected; {high_conf_contracts} API contracts have confidence >= 0.85. |
| Dependency graph shape | High | {len(dependencies.get('edges', []))} edges; invalid graph endpoints after normalization: {len(invalid_edges)}. |
| Capability grouping | Medium | {len(capability_map['capabilities'])} capability candidates; average capability confidence {avg_cap_conf}. |
| Call flows | Medium | {len(flows)} flows detected; {traced_flows} traced/coverage-marker flows and {partial_flows} partial flows. |
| Test/runtime evidence | Medium/High | Static test-source evidence is captured; runtime status: {test_runtime_map.get('runtime_execution_status')}; runtime projects: {test_runtime_map.get('summary', {}).get('runtime_test_projects', 0)}. |
| External boundary purpose | Medium/Low | External targets are detected as candidates; purpose/ownership still needs confirmation. |

## Why Confidence Is Lower In Some Areas

- Static parsing cannot prove complete runtime route coverage where framework conventions expand routes dynamically.
- Dynamic dispatch and framework conventions can still limit call-flow completeness.
- Capability grouping is inferred from names, folders, modules, routes, components, and dependencies.
- Unknown component classifications may hide support classes or architecture-significant pieces.

## How To Increase Confidence

1. Confirm open questions with application owners.
2. Add contract tests for preserved API contracts.
3. Add parser support for language/framework-specific call graphs.
4. Review any remaining major Unknown components and test-project inclusion policy.
5. Validate external dependency purpose from runtime config and deployment knowledge.
"""


def open_question_lines(text: str) -> list[str]:
    return [line[2:] for line in text.splitlines() if line.startswith("- ")]


def build_architecture_decision_inputs(data: dict[str, Any], capability_map: dict[str, Any]) -> str:
    questions = open_question_lines(data.get("open_questions_md", ""))
    review_caps = [cap for cap in capability_map["capabilities"] if cap["forward_engineering_decision"] == "review_before_extraction"][:8]
    lines = [
        "# Architecture Decision Inputs",
        "",
        "These are decision prompts for architects. They are derived from extracted evidence and should be resolved before committing to future boundaries.",
        "",
    ]
    idx = 1
    for cap in review_caps:
        lines.extend(
            [
                f"## ADR-INPUT-{idx:03d}: Confirm `{cap['name']}` Boundary",
                "",
                f"Decision needed: Should `{cap['name']}` be a separate future module/service boundary, remain internal, or merge with another capability?",
                "",
                f"Evidence: {cap['capability_id']}; modules {short_list([m['module_id'] + ' ' + m['name'] for m in cap['modules']], 8)}; source files {short_list(cap['source_files'], 4)}.",
                "",
                f"Risk signal: risks {cap['risk_count']}, weak modules {cap['weak_module_count']}, coupling {cap['afferent_coupling'] + cap['efferent_coupling']}.",
                "",
                "Recommended review: confirm ownership, public interfaces, data ownership, and call flows before extraction.",
                "",
            ]
        )
        idx += 1
    for question in questions[:10]:
        lines.extend(
            [
                f"## ADR-INPUT-{idx:03d}: Resolve Open Question",
                "",
                f"Decision needed: {question}",
                "",
                "Evidence: `open-questions.md` and related final JSON artifacts.",
                "",
                "Recommended review: assign to architecture/product/application owner and record preserve/redesign/review decision.",
                "",
            ]
        )
        idx += 1
    return "\n".join(lines)


def build_forward_engineering_backlog(data: dict[str, Any], capability_map: dict[str, Any], api_contract_map: dict[str, Any]) -> str:
    risks = data["risks"].get("risks", [])
    review_contracts = [item for item in api_contract_map["api_contracts"] if item["preserve_redesign_review"] == "review"]
    preserve_contracts = [item for item in api_contract_map["api_contracts"] if item["preserve_redesign_review"] == "preserve"]
    review_caps = [cap for cap in capability_map["capabilities"] if cap["forward_engineering_decision"] == "review_before_extraction"]
    questions = open_question_lines(data.get("open_questions_md", ""))
    items = []

    def add(title: str, source: str, priority: str, acceptance: str) -> None:
        items.append(
            {
                "id": f"FE-{len(items) + 1:03d}",
                "title": title,
                "source": source,
                "priority": priority,
                "acceptance": acceptance,
            }
        )

    add(
        "Confirm authoritative system name and deployment ownership",
        "open-questions.md",
        "High",
        "System name and deployable ownership are confirmed or intentionally kept unknown.",
    )
    for cap in review_caps[:8]:
        add(
            f"Review future boundary for {cap['capability_id']} {cap['name']}",
            "business-capability-map.json",
            "High" if cap["risk_count"] else "Medium",
            "Architect records preserve/merge/extract decision with data ownership and API impact.",
        )
    for risk in risks[:8]:
        add(
            f"Resolve architecture risk {risk.get('risk_id')}",
            "application-risk-register.json",
            "High" if risk.get("severity") in {"Critical", "High"} else "Medium",
            "Risk is accepted, mitigated, or converted into implementation constraints.",
        )
    for contract in preserve_contracts[:8]:
        add(
            f"Create contract test for {contract['contract_id']} {contract['method']} {contract['path_or_name']}",
            "api-contract-preservation-map.json",
            "Medium",
            "Forward implementation can prove behavioral compatibility or intentional redesign.",
        )
    for contract in review_contracts[:8]:
        add(
            f"Review API contract {contract['contract_id']} {contract['method']} {contract['path_or_name']}",
            "api-contract-preservation-map.json",
            "Medium",
            "Contract is classified as preserve, redesign, or retire with owner approval.",
        )
    for question in questions[:6]:
        add(
            "Resolve open architecture question",
            "open-questions.md",
            "Medium",
            question,
        )

    lines = [
        "# Forward Engineering Backlog",
        "",
        "This backlog converts architecture evidence into planning tasks. It is not an implementation task list yet.",
        "",
        "| ID | Priority | Title | Source | Acceptance / Done When |",
        "|---|---|---|---|---|",
    ]
    for item in items:
        lines.append(f"| {item['id']} | {item['priority']} | {item['title']} | {item['source']} | {item['acceptance']} |")
    return "\n".join(lines)


def generate(output_root: Path) -> dict[str, Any]:
    final_root = output_root / "final"
    data = load_final(output_root)
    capability_map = build_business_capability_map(data)
    api_contract_map = build_api_contract_map(data, capability_map)
    consolidation_map = build_module_consolidation_map(capability_map)
    test_runtime_map = build_test_runtime_evidence_map(data, capability_map, output_root)

    write_json(final_root / "business-capability-map.json", capability_map)
    write_text(final_root / "business-capability-map.md", build_capability_markdown(capability_map))
    write_json(final_root / "module-consolidation-map.json", consolidation_map)
    write_text(final_root / "module-consolidation-map.md", build_module_consolidation_markdown(consolidation_map))
    write_json(final_root / "api-contract-preservation-map.json", api_contract_map)
    write_text(final_root / "service-boundary-options.md", build_service_boundary_options(data, capability_map))
    write_text(final_root / "migration-wave-plan.md", build_migration_wave_plan(capability_map, api_contract_map, data))
    write_text(final_root / "preserve-redesign-retire-map.md", build_preserve_redesign_retire_map(data, capability_map, api_contract_map))
    write_text(final_root / "data-ownership-map.md", build_data_ownership_map(data, capability_map))
    write_json(final_root / "test-runtime-evidence-map.json", test_runtime_map)
    write_text(final_root / "test-runtime-evidence-map.md", build_test_runtime_evidence_markdown(test_runtime_map))
    write_text(final_root / "confidence-report.md", build_confidence_report(data, capability_map, api_contract_map, test_runtime_map))
    write_text(final_root / "architecture-decision-inputs.md", build_architecture_decision_inputs(data, capability_map))
    write_text(final_root / "forward-engineering-backlog.md", build_forward_engineering_backlog(data, capability_map, api_contract_map))

    return {
        "output_directory": str(final_root),
        "files_created": OUTPUT_FILES,
        "summary": {
            "capability_count": capability_map["summary"]["capability_count"],
            "consolidated_module_candidate_count": consolidation_map["summary"]["consolidated_module_candidate_count"],
            "api_contract_count": api_contract_map["summary"]["contract_count"],
            "preserve_contract_count": api_contract_map["summary"]["preserve_count"],
            "review_contract_count": api_contract_map["summary"]["review_count"],
            "test_component_count": test_runtime_map["summary"]["test_component_count"],
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate enterprise forward-engineering artifacts from final architecture outputs.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root).resolve()
    summary = generate(output_root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
