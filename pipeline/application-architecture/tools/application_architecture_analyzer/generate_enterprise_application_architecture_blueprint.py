#!/usr/bin/env python3
"""
Generate an enterprise Application Architecture blueprint for forward engineering.

This stage reads generated architecture artifacts only. It does not inspect or
modify legacy source code. The intent is to turn reverse-engineered evidence
into the kind of implementation architecture document a team would need if it
were rebuilding the application from scratch.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENERATOR_VERSION = "0.1.0"

SOURCE_ARTIFACTS = [
    "architecture-output/inventory/project-inventory.json",
    "architecture-output/final/system-inventory.json",
    "architecture-output/final/module-boundary-map.json",
    "architecture-output/final/component-registry.json",
    "architecture-output/final/dependency-graph.json",
    "architecture-output/final/application-interface-catalogue.json",
    "architecture-output/final/call-flow-map.json",
    "architecture-output/final/architecture-violation-register.json",
    "architecture-output/final/application-risk-register.json",
    "architecture-output/final/business-capability-map.json",
    "architecture-output/final/module-consolidation-map.json",
    "architecture-output/final/api-contract-preservation-map.json",
    "architecture-output/final/test-runtime-evidence-map.json",
    "architecture-output/evidence-packs/layering-pattern-pack.json",
    "architecture-output/evidence-packs/external-boundary-pack.json",
    "architecture-output/evidence-packs/frontend-application-pack.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def unique(values: list[Any]) -> list[Any]:
    result = []
    for value in values:
        if value in {None, "", "unknown"}:
            continue
        if value not in result:
            result.append(value)
    return result


def short_list(values: list[Any], limit: int = 8) -> str:
    cleaned = [str(value) for value in values if value not in {None, "", "unknown"}]
    if not cleaned:
        return "none detected"
    if len(cleaned) <= limit:
        return ", ".join(cleaned)
    return ", ".join(cleaned[:limit]) + f", and {len(cleaned) - limit} more"


def md_list(values: list[str], empty: str = "- none detected") -> str:
    cleaned = [value for value in values if value not in {None, "", "unknown"}]
    return "\n".join(f"- {value}" for value in cleaned) if cleaned else empty


def evidence_files(items: list[dict[str, Any]], limit: int = 8) -> list[str]:
    files = []
    for item in items:
        for key in ("file", "source_file"):
            file = item.get(key)
            if file and file != "unknown" and file not in files:
                files.append(file)
        for evidence in item.get("evidence", []) or []:
            if isinstance(evidence, dict):
                file = evidence.get("file")
                if file and file != "unknown" and file not in files:
                    files.append(file)
        if len(files) >= limit:
            break
    return files


def package_references(project_inventory: dict[str, Any]) -> set[str]:
    return {
        package
        for project in project_inventory.get("projects", [])
        for package in project.get("package_references", []) or []
    }


def project_names(projects: list[dict[str, Any]]) -> list[str]:
    return unique([project.get("name", "unknown") for project in projects if project.get("name")])


def source_ref(item: dict[str, Any]) -> str:
    file = item.get("file") or item.get("source_file") or "unknown"
    line = item.get("line")
    return f"{file}:{line}" if line else str(file)


def sample_component_refs(components: list[dict[str, Any]], limit: int = 5) -> list[str]:
    return [
        f"{component.get('name')} ({component.get('type', 'Unknown')}) [{source_ref(component)}]"
        for component in components[:limit]
    ]


def module_indexes(modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {module.get("name", "unknown"): module for module in modules}


def components_by_module(components: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for component in components:
        grouped[component.get("module", component.get("module_guess", "Unknown"))].append(component)
    return grouped


def interfaces_by_module(interfaces: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for interface in interfaces:
        grouped[interface.get("owner_module", "Unknown")].append(interface)
    return grouped


def dependency_edges_by_module(graph: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    component_module = {
        node.get("id"): node.get("module")
        for node in graph.get("nodes", [])
        if node.get("type") == "component"
    }
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    module_names = {
        node.get("id")
        for node in graph.get("nodes", [])
        if node.get("type") == "module"
    }
    for edge in graph.get("edges", []):
        source = edge.get("from")
        target = edge.get("to")
        source_module = source if source in module_names else component_module.get(source)
        target_module = target if target in module_names else component_module.get(target)
        if not source_module or not target_module or source_module == target_module:
            continue
        outgoing[source_module].add(target_module)
        incoming[target_module].add(source_module)
    return outgoing, incoming


def primary_pattern(layering_pack: dict[str, Any]) -> dict[str, Any]:
    candidates = layering_pack.get("candidate_patterns", [])
    if not candidates:
        return {"pattern": "Unknown", "confidence": 0.0, "evidence": "No pattern evidence generated."}
    return max(candidates, key=lambda item: float(item.get("confidence", 0.0)))


def layer_model(layering_pack: dict[str, Any], violations: dict[str, Any]) -> dict[str, Any]:
    detected = layering_pack.get("detected_layers", [])
    return {
        "detected_layers": [
            {
                "layer": layer.get("layer"),
                "component_count": layer.get("component_count", 0),
                "evidence_files": layer.get("evidence_files", [])[:8],
            }
            for layer in detected
        ],
        "dependency_direction": layering_pack.get("dependency_direction", []),
        "layer_rules_for_forward_engineering": [
            "Presentation/UI and API components should invoke application/use-case services, handlers, or gateways instead of directly owning persistence logic.",
            "Domain components should remain independent of Presentation/UI, API, Integration, Infrastructure, and DataAccess concerns unless an explicit reviewed exception exists.",
            "Infrastructure and DataAccess should implement persistence/integration abstractions and must not become the owner of user-facing workflow orchestration.",
            "CrossCutting concerns should be shared through explicit configuration, middleware, policies, or adapters rather than hidden module-to-module dependencies.",
        ],
        "violations_not_to_carry_forward": [
            {
                "violation_id": violation.get("violation_id"),
                "description": violation.get("description"),
                "affected_components": violation.get("affected_components", []),
                "affected_modules": violation.get("affected_modules", []),
                "evidence": violation.get("evidence", []),
            }
            for violation in violations.get("violations", [])
        ],
    }


def module_blueprints(data: dict[str, Any]) -> list[dict[str, Any]]:
    modules = data["modules"].get("modules", [])
    components_grouped = components_by_module(data["components"].get("components", []))
    interfaces_grouped = interfaces_by_module(data["interfaces"].get("interfaces", []))
    outgoing, incoming = dependency_edges_by_module(data["dependencies"])
    risks = data["risks"].get("risks", [])
    violations = data["violations"].get("violations", [])
    result = []
    for module in modules:
        name = module.get("name", "Unknown")
        components = components_grouped.get(name, [])
        interfaces = interfaces_grouped.get(name, [])
        types = Counter(component.get("type", "Unknown") for component in components)
        layers = Counter(component.get("layer", "Unknown") for component in components)
        module_risks = [
            risk for risk in risks
            if name in risk.get("affected_modules", [])
            or name in str(risk.get("description", ""))
        ][:8]
        module_violations = [
            violation for violation in violations
            if name in violation.get("affected_modules", [])
        ][:8]
        result.append(
            {
                "module_id": module.get("module_id"),
                "name": name,
                "design_role": module_design_role(name, types, layers, interfaces),
                "target_implementation_contract": target_implementation_contract_for_module(name, types, layers, interfaces),
                "pattern_signals": pattern_signals_for_module(types, layers, components),
                "responsibility_to_implement": module.get("responsibility", "unknown"),
                "source_folders": module.get("source_folders", []),
                "component_count": len(components),
                "component_types": dict(types),
                "layers_present": dict(layers),
                "primary_components": [
                    {
                        "component_id": component.get("component_id"),
                        "name": component.get("name"),
                        "type": component.get("type"),
                        "layer": component.get("layer"),
                        "file": component.get("file"),
                        "semantic_symbol_id": component.get("semantic_symbol_id"),
                        "confidence": component.get("confidence", 0.0),
                    }
                    for component in components[:12]
                ],
                "entry_points_to_preserve_or_review": [
                    {
                        "interface_id": interface.get("interface_id"),
                        "type": interface.get("type"),
                        "method": interface.get("method"),
                        "path_or_name": interface.get("path_or_name"),
                        "entry_component": interface.get("entry_component"),
                        "source_file": interface.get("source_file"),
                        "line": interface.get("line"),
                        "confidence": interface.get("confidence", 0.0),
                    }
                    for interface in interfaces[:20]
                ],
                "depends_on_modules": sorted(outgoing.get(name, set()) | set(module.get("depends_on_modules", []))),
                "depended_on_by_modules": sorted(incoming.get(name, set()) | set(module.get("depended_on_by_modules", []))),
                "implementation_guidance": implementation_guidance_for_module(module, types, module_risks, module_violations),
                "migration_readiness": module.get("migration_readiness", "Unknown"),
                "boundary_quality": module.get("boundary_quality", "Unknown"),
                "risks_to_resolve": [
                    {
                        "risk_id": risk.get("risk_id"),
                        "description": risk.get("description"),
                        "severity": risk.get("severity"),
                        "evidence": risk.get("evidence", []),
                    }
                    for risk in module_risks
                ],
                "violations_to_redesign": [
                    {
                        "violation_id": violation.get("violation_id"),
                        "description": violation.get("description"),
                        "evidence": violation.get("evidence", []),
                    }
                    for violation in module_violations
                ],
                "confidence": module.get("confidence", 0.0),
                "evidence": module.get("evidence", []),
            }
        )
    return result


def module_design_role(
    name: str,
    types: Counter,
    layers: Counter,
    interfaces: list[dict[str, Any]],
) -> str:
    if (types.get("Controller") or interfaces) and (types.get("Entity") or types.get("Repository") or types.get("Service")):
        return "Business capability module spanning invocation, workflow, domain/data evidence, or shared UI/API behavior."
    if types.get("FrontendComponent") or name.lower() == "admin":
        return "User-interface or frontend-facing module that adapts user actions to API/application calls."
    if types.get("Controller") or interfaces:
        return "Invocation/API module that owns externally visible routes and maps requests into application behavior."
    if types.get("Entity") and types.get("Repository"):
        return "Domain and persistence-adjacent module with entity ownership and data-access concerns that need separation in the target design."
    if types.get("Entity"):
        return "Domain model module that owns business entities/value objects and should remain independent of infrastructure details."
    if types.get("Repository") or layers.get("DataAccess"):
        return "Data-access adapter module that should implement persistence contracts rather than own business workflow."
    if layers.get("CrossCutting"):
        return "Shared/cross-cutting support module for configuration, constants, shared contracts, or platform concerns."
    return "Supporting module candidate whose target role requires human boundary review."


def target_implementation_contract_for_module(
    name: str,
    types: Counter,
    layers: Counter,
    interfaces: list[dict[str, Any]],
) -> str:
    contracts = []
    if interfaces:
        contracts.append("preserve or explicitly redesign the listed route/API contracts")
    if types.get("Service") or types.get("Handler"):
        contracts.append("expose use-case operations through application services or handlers")
    if types.get("Entity"):
        contracts.append("preserve domain invariants and entity relationships during redesign")
    if types.get("Repository") or layers.get("DataAccess"):
        contracts.append("hide persistence behind repository/query abstractions")
    if types.get("FrontendComponent"):
        contracts.append("map UI routes and components to stable API/client-service calls")
    if not contracts:
        contracts.append("confirm whether this candidate remains a separate target module")
    return f"{name} should " + "; ".join(contracts) + "."


def pattern_signals_for_module(
    types: Counter,
    layers: Counter,
    components: list[dict[str, Any]],
) -> list[str]:
    signals = []
    names = " ".join(component.get("name", "") for component in components)
    files = " ".join(component.get("file", "") for component in components)
    if types.get("Controller"):
        signals.append("Controller/API endpoint pattern")
    if types.get("FrontendComponent"):
        signals.append("Frontend component pattern")
    if types.get("Repository"):
        signals.append("Repository pattern")
    if "Specification" in names:
        signals.append("Specification pattern")
    if types.get("Entity"):
        signals.append("Domain entity/aggregate style")
    if types.get("Handler"):
        signals.append("Handler/CQRS-style component")
    if "Context" in names or "Data/Config" in files:
        signals.append("EF Core context/configuration style")
    if layers.get("CrossCutting"):
        signals.append("Shared configuration/cross-cutting style")
    return signals


def implementation_guidance_for_module(
    module: dict[str, Any],
    types: Counter,
    risks: list[dict[str, Any]],
    violations: list[dict[str, Any]],
) -> list[str]:
    guidance = [
        "Preserve externally visible interfaces and behavior where this module owns APIs or frontend routes.",
        "Keep module ownership aligned to the listed source folders and component evidence until a human architect confirms revised boundaries.",
    ]
    if types.get("Controller") or types.get("FrontendComponent"):
        guidance.append("Implement entry-point components as thin orchestration/adaptation layers.")
    if types.get("Service") or types.get("Handler"):
        guidance.append("Place workflow/use-case coordination in application services or handlers.")
    if types.get("Repository") or types.get("Entity"):
        guidance.append("Separate persistence access from API/UI entry points and keep entity ownership explicit.")
    if module.get("boundary_quality") in {"Weak", "Unknown"}:
        guidance.append("Do not freeze this as a future bounded context until coupling and ownership questions are reviewed.")
    if risks or violations:
        guidance.append("Redesign listed risks and violations before carrying this module into a target implementation.")
    return guidance


def invocation_model(interfaces: dict[str, Any], flows: dict[str, Any]) -> dict[str, Any]:
    interface_rows = interfaces.get("interfaces", [])
    flow_rows = flows.get("flows", [])
    by_type = Counter(item.get("type", "Unknown") for item in interface_rows)
    by_method = Counter(item.get("method", "unknown") for item in interface_rows)
    by_module = Counter(item.get("owner_module", "Unknown") for item in interface_rows)
    return {
        "summary": {
            "entry_point_count": len(interface_rows),
            "entry_points_by_type": dict(by_type),
            "http_methods": dict(by_method),
            "entry_points_by_module": dict(by_module),
            "call_flow_count": len(flow_rows),
            "semantic_trace_flow_count": sum(1 for flow in flow_rows if flow.get("semantic_step_count", 0) > 0),
        },
        "bootstrap_and_runtime_entry_points": [
            item for item in interface_rows
            if item.get("type") == "CLI"
        ],
        "http_api_contracts": [
            item for item in interface_rows
            if item.get("type") == "HTTP_API"
        ],
        "frontend_route_contracts": [
            item for item in interface_rows
            if item.get("type") == "FrontendRoute"
        ],
        "implementation_rules": [
            "Every HTTP_API interface listed here must either be preserved, explicitly versioned, or retired with product-owner approval.",
            "Every FrontendRoute must be mapped to a frontend route/component responsibility or marked for redesign.",
            "Program.cs/CLI bootstrap entries represent executable startup surfaces, not user-facing business commands unless human review confirms otherwise.",
            "Call-flow steps with Roslyn semantic evidence can be used as stronger behavior-preservation anchors than heuristic-only steps.",
        ],
    }


def pick_scenario(
    flows: list[dict[str, Any]],
    predicate: Any,
    fallback_name: str,
    scenario_type: str,
) -> dict[str, Any]:
    for flow in flows:
        if predicate(flow):
            return scenario_from_flow(flow, scenario_type)
    return {
        "scenario_id": f"SC-{scenario_type}",
        "name": fallback_name,
        "type": scenario_type,
        "status": "unknown",
        "entry_point": "unknown",
        "implementation_contract": "No direct flow evidence was detected; preserve as an open architecture review question.",
        "layers_traced": [],
        "evidence": [],
        "confidence": 0.0,
        "open_questions": ["Human review required because no source-backed flow matched this required enterprise scenario type."],
    }


def scenario_from_flow(flow: dict[str, Any], scenario_type: str) -> dict[str, Any]:
    steps = flow.get("steps", [])
    flow_narrative = scenario_flow_narrative(flow, steps)
    return {
        "scenario_id": f"SC-{scenario_type}",
        "name": flow.get("name") or flow.get("entry_point"),
        "type": scenario_type,
        "status": flow.get("status"),
        "entry_point": flow.get("entry_point"),
        "implementation_contract": (
            "Implement this scenario so the entry point invokes the listed components in the observed layer/module order, "
            "or document an intentional redesign with equivalent behavior."
        ),
        "flow_narrative": flow_narrative,
        "layers_traced": [
            {
                "step": step.get("step"),
                "component": step.get("component"),
                "layer": step.get("layer"),
                "module": step.get("module"),
                "action": step.get("action"),
                "file": step.get("file"),
                "evidence": step.get("evidence"),
            }
            for step in steps
        ],
        "modules_touched": flow.get("modules_touched", []),
        "data_access_components": flow.get("data_access_components", []),
        "external_systems_touched": flow.get("external_systems_touched", []),
        "semantic_step_count": flow.get("semantic_step_count", 0),
        "confidence": flow.get("confidence", 0.0),
        "open_questions": flow.get("open_questions", []),
    }


def scenario_flow_narrative(flow: dict[str, Any], steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "No source-backed steps were resolved for this scenario."
    entry = flow.get("entry_point", "unknown entry point")
    first = steps[0]
    rest = steps[1:]
    if not rest:
        return f"The flow starts at {entry} in {first.get('component')} and no downstream component was resolved from static/semantic evidence."
    chain = " -> ".join(
        f"{step.get('component')} ({step.get('layer')}/{step.get('module')})"
        for step in steps
    )
    semantic = flow.get("semantic_step_count", 0)
    data_access = short_list(flow.get("data_access_components", []), 4)
    external = short_list([item.get("target") for item in flow.get("external_systems_touched", [])], 4)
    return (
        f"The flow starts at {entry}. The observed implementation chain is {chain}. "
        f"Semantic evidence is present on {semantic} step(s). "
        f"Data-access components touched: {data_access}. External systems touched: {external}."
    )


def business_scenarios(flows: dict[str, Any]) -> list[dict[str, Any]]:
    flow_rows = flows.get("flows", [])
    return [
        pick_scenario(
            flow_rows,
            lambda flow: flow.get("entry_point_type") == "HTTP_API"
            and str(flow.get("entry_point", "")).startswith("GET")
            and any(module in {"Catalog", "Basket", "Order"} for module in flow.get("modules_touched", [])),
            "Read/browse flow",
            "READ_PATH",
        ),
        pick_scenario(
            flow_rows,
            lambda flow: flow.get("entry_point_type") == "HTTP_API"
            and str(flow.get("entry_point", "")).split(" ", 1)[0] in {"POST", "PUT", "DELETE"}
            and not any("authenticate" in str(flow.get("entry_point", "")).lower() for _ in [0]),
            "Write/mutation flow",
            "WRITE_PATH",
        ),
        pick_scenario(
            flow_rows,
            lambda flow: "auth" in str(flow.get("entry_point", "")).lower()
            or "Identity" in flow.get("modules_touched", []),
            "Authentication/identity flow",
            "AUTH_PATH",
        ),
        pick_scenario(
            flow_rows,
            lambda flow: "admin" in str(flow.get("entry_point", "")).lower()
            or "Admin" in flow.get("modules_touched", []),
            "Admin/privileged flow",
            "ADMIN_PATH",
        ),
        pick_scenario(
            flow_rows,
            lambda flow: "health" in str(flow.get("entry_point", "")).lower(),
            "Reliability/health-check flow",
            "ERROR_OR_RESILIENCE_PATH",
        ),
    ]


def data_access_model(components: dict[str, Any], external_pack: dict[str, Any]) -> dict[str, Any]:
    component_rows = components.get("components", [])
    repositories = [item for item in component_rows if item.get("type") == "Repository"]
    entities = [item for item in component_rows if item.get("type") == "Entity"]
    db_contexts = [
        item for item in component_rows
        if "context" in str(item.get("name", "")).lower()
        or "dbcontext" in json.dumps(item.get("dependencies", [])).lower()
    ]
    database_boundaries = [
        item for item in external_pack.get("external_dependencies", [])
        if "database" in str(item.get("type", "")).lower()
        or str(item.get("target_system", "")).lower() in {"sqlserver", "postgres", "mysql", "redis"}
    ]
    return {
        "repositories": repositories[:30],
        "entities": entities[:30],
        "database_context_or_session_candidates": db_contexts[:20],
        "database_or_infrastructure_boundaries": database_boundaries,
        "implementation_rules": [
            "Treat repository/data-access components as infrastructure adapters behind application/domain-facing abstractions.",
            "Do not let API/UI entry points call shared repositories directly in the target design unless explicitly accepted as an architecture exception.",
            "Confirm true data ownership with database/schema review before splitting modules or services.",
        ],
    }


def frontend_model(frontend_pack: dict[str, Any]) -> dict[str, Any]:
    apps = frontend_pack.get("frontend_apps", [])
    return {
        "status": frontend_pack.get("status", "unknown"),
        "frontend_apps": apps,
        "implementation_rules": [
            "Preserve detected frontend routes or map them to equivalent navigation routes in the target UI.",
            "Keep frontend API call contracts aligned with the API contract preservation map.",
            "State management and authentication-state clues require human review before target UI design is finalized.",
        ] if apps else ["No frontend application was detected by evidence packs."],
    }


def architecture_design_overview(data: dict[str, Any]) -> dict[str, Any]:
    system = data["system"]
    project_inventory = data.get("project_inventory", {})
    projects = system.get("applications", [])
    deployables = system.get("deployable_units", [])
    supporting = system.get("supporting_projects", [])
    frontend = system.get("frontend_projects", [])
    database_support = system.get("database_support_projects", [])
    packages = package_references(project_inventory)
    architecture_style_packages = [
        package for package in sorted(packages)
        if any(
            token in package.lower()
            for token in (
                "api",
                "auth",
                "blazor",
                "component",
                "entityframework",
                "identity",
                "mediatr",
                "minimalapi",
                "specification",
                "swagger",
                "validation",
            )
        )
    ]
    return {
        "design_narrative": [
            (
                "The application is organized as a layered .NET solution with web-facing deployables and supporting libraries. "
                f"Detected deployable candidates are {short_list(project_names(deployables))}; supporting project candidates include {short_list(project_names(supporting + database_support + frontend), 10)}."
            ),
            (
                "Invocation enters through HTTP APIs, MVC/Razor-style web routes, frontend routes, and executable bootstrap Program.cs files. "
                "The target build should keep these invocation adapters thin and move workflow orchestration into application services, handlers, or explicitly reviewed module APIs."
            ),
            (
                "Domain and application concerns are primarily represented through entity, service, handler, specification, repository-interface, and shared-contract components. "
                "Infrastructure concerns are represented through EF Core/data configuration, repository implementation, identity/token services, and external or frontend API clients."
            ),
            (
                "The legacy evidence shows useful patterns that should influence the target design, but weak boundaries, direct endpoint-to-repository dependencies, and module cycles should be redesigned rather than copied."
            ),
        ],
        "technology_style_clues": architecture_style_packages,
        "target_design_posture": [
            "Preserve public contracts and behavior before changing implementation internals.",
            "Use the detected layered architecture as the first target decomposition model.",
            "Treat modules as candidate boundaries until data ownership and coupling questions are reviewed.",
            "Keep UI/API adapters thin; place business workflow in application/domain services or handlers.",
            "Isolate persistence and integrations behind interfaces/adapters.",
        ],
    }


def architecture_pattern_catalogue(data: dict[str, Any]) -> list[dict[str, Any]]:
    components = data["components"].get("components", [])
    interfaces = data["interfaces"].get("interfaces", [])
    project_inventory = data.get("project_inventory", {})
    packages = package_references(project_inventory)
    pattern = primary_pattern(data["layering_pack"])
    frontend_pack = data["frontend_pack"]
    patterns: list[dict[str, Any]] = []

    def add(name: str, detected: bool, evidence: list[str], implementation_meaning: str, target_guidance: str, confidence: float) -> None:
        if detected:
            patterns.append(
                {
                    "pattern_or_style": name,
                    "detected": True,
                    "evidence": evidence,
                    "implementation_meaning": implementation_meaning,
                    "target_guidance": target_guidance,
                    "confidence": confidence,
                }
            )

    repositories = [component for component in components if component.get("type") == "Repository"]
    specifications = [
        component for component in components
        if "Specification" in str(component.get("name", "")) or "Specifications/" in str(component.get("file", ""))
    ]
    endpoints = [
        component for component in components
        if component.get("type") == "Controller" and (
            str(component.get("name", "")).endswith("Endpoint") or "Endpoints/" in str(component.get("file", ""))
        )
    ]
    controllers = [component for component in components if component.get("type") == "Controller"]
    entities = [component for component in components if component.get("type") == "Entity"]
    handlers = [component for component in components if component.get("type") == "Handler"]
    configs = [component for component in components if component.get("type") == "Configuration"]
    db_contexts = [
        component for component in components
        if "Context" in str(component.get("name", "")) or "Data/Config" in str(component.get("file", ""))
    ]
    frontend_components = [component for component in components if component.get("type") == "FrontendComponent"]
    constructor_injected = [
        component for component in components
        if component.get("semantic_constructor_dependencies") or component.get("dependencies")
    ]
    health_interfaces = [
        interface for interface in interfaces
        if "health" in str(interface.get("path_or_name", "")).lower()
    ]

    add(
        "Layered Monolith / Layered Application",
        pattern.get("pattern") != "Unknown",
        [pattern.get("evidence", "architecture pattern evidence")],
        "The application is organized into API/UI, Application, Domain, Infrastructure/DataAccess, Integration, and CrossCutting concerns inside one repository/solution.",
        "Use layered boundaries as the implementation baseline, then remove direct API/UI-to-data access dependencies before target sign-off.",
        float(pattern.get("confidence", 0.0)),
    )
    add(
        "Clean Architecture influence",
        {"ApplicationCore", "Infrastructure"} & set(project_names(project_inventory.get("projects", []))) != set(),
        ["Projects/layers include ApplicationCore, Infrastructure, Domain, Application, DataAccess, and Integration evidence."],
        "Core/domain abstractions are separated from infrastructure implementations, although evidence shows some boundary weakness.",
        "Keep domain/application contracts inward-facing and make infrastructure implement adapters; review violations before copying structure.",
        0.72,
    )
    add(
        "Repository Pattern",
        bool(repositories),
        sample_component_refs(repositories),
        "Persistence access is represented through repository components/interfaces and shared repository implementations.",
        "Preserve repository/query abstractions, but avoid direct endpoint-to-repository coupling in the target design.",
        0.86,
    )
    add(
        "Specification Pattern",
        bool(specifications) or "Ardalis.Specification" in packages,
        sample_component_refs(specifications) or ["PackageReference: Ardalis.Specification"],
        "Query/filter rules are expressed as reusable specification components or supported by the Ardalis.Specification package.",
        "Use specifications for reusable query intent, but keep them owned by the module/data model they describe.",
        0.84,
    )
    add(
        "Endpoint / Handler-style API",
        bool(endpoints) or {"Ardalis.ApiEndpoints", "MinimalApi.Endpoint"} & packages,
        sample_component_refs(endpoints) or ["PackageReference: Ardalis.ApiEndpoints or MinimalApi.Endpoint"],
        "Some API routes are implemented as endpoint classes with HandleAsync/AddRoute-style behavior instead of only conventional MVC controllers.",
        "Model target APIs as explicit request handlers/endpoints with thin mapping and application-service delegation.",
        0.86,
    )
    add(
        "MVC / Razor Pages Web UI",
        any("/Controllers/" in str(component.get("file", "")) or "/Pages/" in str(component.get("file", "")) for component in controllers),
        sample_component_refs(controllers),
        "Web-facing routes include controller/page-style components, especially around account/manage and web storefront behavior.",
        "Preserve user-visible routes or intentionally remap them; keep controllers/page models thin.",
        0.78,
    )
    add(
        "Blazor frontend component/service style",
        bool(frontend_components) or frontend_pack.get("status") == "frontend_detected",
        sample_component_refs(frontend_components),
        "Frontend behavior is represented through Blazor/Razor components and frontend services that call backend APIs.",
        "Preserve route/API contracts and rebuild frontend state/API service patterns explicitly.",
        0.82,
    )
    add(
        "Dependency Injection and Constructor Injection",
        bool(constructor_injected),
        sample_component_refs(constructor_injected),
        "Components express dependencies through constructors, DI registrations, and injected Razor/frontend services.",
        "Use DI as the composition mechanism, but keep dependency direction aligned with target layers.",
        0.9,
    )
    add(
        "EF Core Data Access / ORM Configuration",
        bool(db_contexts) or any("EntityFrameworkCore" in package for package in packages),
        sample_component_refs(db_contexts) or ["PackageReference: Microsoft.EntityFrameworkCore.*"],
        "Persistence is implemented through EF Core-style contexts, entity configurations, repositories, and database support.",
        "Keep EF Core in infrastructure/data-access adapters and confirm data ownership before service/module extraction.",
        0.86,
    )
    add(
        "Configuration / Options / Cross-cutting constants",
        bool(configs),
        sample_component_refs(configs),
        "Configuration and constants are explicit components that support authentication, catalog behavior, routing, options, and shared behavior.",
        "Move cross-cutting configuration into explicit options/policies and avoid hidden module coupling through shared constants.",
        0.77,
    )
    add(
        "MediatR / CQRS-style handlers",
        bool(handlers) or "MediatR" in packages,
        sample_component_refs(handlers) or ["PackageReference: MediatR"],
        "Handler components and MediatR clues indicate command/query or request-handler style behavior in parts of the application.",
        "Use handlers for use-case isolation where they already exist; do not force CQRS everywhere unless justified by module complexity.",
        0.68,
    )
    add(
        "Health Check / Operational Endpoint style",
        bool(health_interfaces),
        [f"{item.get('method')} {item.get('path_or_name')} [{item.get('source_file')}:{item.get('line')}]" for item in health_interfaces],
        "Runtime health endpoints are exposed as operational entry points.",
        "Preserve health/readiness endpoints or provide target equivalents in the deployment platform.",
        0.8,
    )
    return patterns


def implementation_architecture_by_concern(data: dict[str, Any]) -> list[dict[str, Any]]:
    components = data["components"].get("components", [])
    interfaces = data["interfaces"].get("interfaces", [])
    modules = data["modules"].get("modules", [])
    by_type = defaultdict(list)
    for component in components:
        by_type[component.get("type", "Unknown")].append(component)
    return [
        {
            "concern": "API and Invocation",
            "legacy_design": "HTTP routes are owned by endpoint/controller/page components and executable Program.cs bootstrap files.",
            "implementation_design": "Create thin route adapters that validate/map requests, invoke application services or handlers, and return stable response contracts.",
            "evidence": [f"{item.get('method')} {item.get('path_or_name')} [{item.get('source_file')}:{item.get('line')}]" for item in interfaces[:8]],
        },
        {
            "concern": "Application Workflow",
            "legacy_design": "Services, handlers, DTOs, specifications, and shared contracts represent use-case and workflow boundaries.",
            "implementation_design": "Implement workflows as application services or handlers that coordinate domain rules, persistence abstractions, and integrations.",
            "evidence": sample_component_refs(by_type.get("Service", []) + by_type.get("Handler", [])),
        },
        {
            "concern": "Domain Model",
            "legacy_design": "Domain entities and aggregate-style folders represent Basket, Catalog, Order, Buyer, and related business concepts.",
            "implementation_design": "Preserve domain concepts and invariants; keep domain types independent of UI/API/infrastructure dependencies.",
            "evidence": sample_component_refs(by_type.get("Entity", [])),
        },
        {
            "concern": "Persistence and Data Access",
            "legacy_design": "Repository, EF Core context/configuration, and data-access components provide persistence behavior.",
            "implementation_design": "Keep persistence behind repository/query abstractions; remove direct endpoint-to-repository access where flagged.",
            "evidence": sample_component_refs(by_type.get("Repository", [])),
        },
        {
            "concern": "Frontend / Admin UI",
            "legacy_design": "Frontend components and services represent admin/user-facing UI routes and API client behavior.",
            "implementation_design": "Preserve route intent and API calls while making state, auth, and API service boundaries explicit.",
            "evidence": sample_component_refs(by_type.get("FrontendComponent", []) + by_type.get("FrontendService", [])),
        },
        {
            "concern": "Cross-cutting and Configuration",
            "legacy_design": "Configuration, constants, middleware, and shared contracts cut across modules.",
            "implementation_design": "Centralize cross-cutting policies as explicit options, middleware, adapters, or shared contracts with clear ownership.",
            "evidence": sample_component_refs(by_type.get("Configuration", []) + by_type.get("Middleware", [])),
        },
        {
            "concern": "Module Boundary Governance",
            "legacy_design": "Module candidates are evidence-derived and several are weak or cyclic.",
            "implementation_design": "Finalize module boundaries only after resolving ownership, data ownership, cycles, and high coupling.",
            "evidence": [f"{module.get('module_id')} {module.get('name')} boundary={module.get('boundary_quality')}" for module in modules[:8]],
        },
    ]


def forward_contract(data: dict[str, Any]) -> dict[str, Any]:
    api_contracts = data["api_contracts"].get("api_contracts", [])
    capabilities = data["capabilities"].get("capabilities", [])
    consolidation = data["module_consolidation"].get("consolidated_modules", [])
    risks = data["risks"].get("risks", [])
    violations = data["violations"].get("violations", [])
    return {
        "preserve": [
            {
                "contract_id": contract.get("contract_id"),
                "method": contract.get("method"),
                "path_or_name": contract.get("path_or_name"),
                "owner_module": contract.get("owner_module"),
                "decision": contract.get("preservation_decision"),
                "evidence": contract.get("evidence", []),
            }
            for contract in api_contracts
            if contract.get("preservation_decision") in {"preserve", "preserve_behavior", "preserve_contract"}
        ][:40],
        "redesign": [
            {
                "risk_id": risk.get("risk_id"),
                "description": risk.get("description"),
                "affected_modules": risk.get("affected_modules", []),
                "affected_components": risk.get("affected_components", []),
                "evidence": risk.get("evidence", []),
            }
            for risk in risks
        ],
        "do_not_carry_forward": [
            {
                "violation_id": violation.get("violation_id"),
                "description": violation.get("description"),
                "affected_modules": violation.get("affected_modules", []),
                "affected_components": violation.get("affected_components", []),
                "evidence": violation.get("evidence", []),
            }
            for violation in violations
        ],
        "review": [
            {
                "capability_id": capability.get("capability_id"),
                "name": capability.get("name"),
                "decision": capability.get("decision"),
                "risks": capability.get("risks", []),
                "evidence": capability.get("evidence", []),
            }
            for capability in capabilities
            if "review" in str(capability.get("decision", "")).lower()
        ][:30],
        "module_consolidation_inputs": consolidation,
    }


def stakeholder_usage_model() -> list[dict[str, str]]:
    return [
        {
            "stakeholder": "Enterprise / Solution Architect",
            "use": "Validate application style, module boundaries, dependency direction, and redesign decisions.",
            "primary_sections": "Architecture Style, Layer Model, Module Blueprint, Forward Engineering Contract",
        },
        {
            "stakeholder": "Engineering Manager",
            "use": "Plan implementation waves, review risks, and track human-review decisions.",
            "primary_sections": "Forward Engineering Contract, Human Review Required, Acceptance Criteria",
        },
        {
            "stakeholder": "Backend / API Engineers",
            "use": "Implement preserved APIs, services, handlers, repositories, and dependency contracts.",
            "primary_sections": "Invocation Model, Behavior Model, Data Access Model, Module Blueprint",
        },
        {
            "stakeholder": "Frontend Engineers",
            "use": "Rebuild or preserve UI routes, frontend services, API call contracts, and state/auth clues.",
            "primary_sections": "Frontend Architecture Model, Invocation Model, Forward Engineering Contract",
        },
        {
            "stakeholder": "QA / Test Engineers",
            "use": "Create contract, scenario, integration, and regression tests from preserved flows and APIs.",
            "primary_sections": "Behavior And Scenario Model, Invocation Model, Runtime Evidence",
        },
        {
            "stakeholder": "Security / Compliance Reviewer",
            "use": "Review identity, exposed interfaces, PII/data ownership questions, and avoid-carry-forward violations.",
            "primary_sections": "Security And Compliance Baseline, Human Review Required",
        },
    ]


def architecture_decision_model(data: dict[str, Any]) -> dict[str, Any]:
    modules = data["modules"].get("modules", [])
    risks = data["risks"].get("risks", [])
    violations = data["violations"].get("violations", [])
    high_coupling_modules = data["dependencies"].get("high_coupling_modules", [])
    weak_modules = [
        module for module in modules
        if module.get("boundary_quality") in {"Weak", "Unknown"}
    ]
    return {
        "decisions_required_before_build": [
            {
                "decision_id": "EA-ADR-001",
                "decision": "Confirm target architecture style and whether the rebuild remains a layered monolith, modular monolith, or moves to separately deployable services.",
                "evidence": ["architecture-output/final/architecture-pattern-report.md"],
                "why_it_matters": "This determines deployment, module boundaries, data ownership, and team ownership.",
            },
            {
                "decision_id": "EA-ADR-002",
                "decision": "Confirm weak module boundaries before using them as target bounded contexts.",
                "affected_modules": [module.get("name") for module in weak_modules],
                "evidence": evidence_files(weak_modules, 8),
                "why_it_matters": "Weak boundaries and cycles can create a poor target design if copied directly.",
            },
            {
                "decision_id": "EA-ADR-003",
                "decision": "Decide how to handle direct API/UI-to-repository dependencies.",
                "affected_violations": [violation.get("violation_id") for violation in violations if "repository" in str(violation.get("description", "")).lower()],
                "evidence": evidence_files(violations, 8),
                "why_it_matters": "The target implementation should avoid carrying forward data-access coupling unless explicitly accepted.",
            },
            {
                "decision_id": "EA-ADR-004",
                "decision": "Confirm API contract preservation/versioning strategy.",
                "evidence": ["architecture-output/final/application-interface-catalogue.json", "architecture-output/final/api-contract-preservation-map.json"],
                "why_it_matters": "Forward implementation must not accidentally break externally visible behavior.",
            },
            {
                "decision_id": "EA-ADR-005",
                "decision": "Confirm data ownership and database boundary strategy.",
                "evidence": ["architecture-output/final/data-ownership-map.md"],
                "why_it_matters": "Module/service extraction cannot be finalized without data ownership decisions.",
            },
        ],
        "high_coupling_inputs": high_coupling_modules,
        "risk_inputs": risks,
    }


def nfr_and_governance_model(data: dict[str, Any]) -> dict[str, Any]:
    runtime = data.get("runtime_evidence", {})
    external = data["external_pack"].get("external_dependencies", [])
    interfaces = data["interfaces"].get("interfaces", [])
    health_interfaces = [
        item for item in interfaces
        if "health" in str(item.get("path_or_name", "")).lower()
    ]
    identity_interfaces = [
        item for item in interfaces
        if item.get("owner_module") == "Identity"
        or any(token in str(item.get("path_or_name", "")).lower() for token in ("auth", "login", "manage", "password"))
    ]
    return {
        "runtime_test_evidence": {
            "status": runtime.get("runtime_execution_status", "unknown"),
            "summary": (runtime.get("runtime_execution_evidence") or {}).get("summary", {}),
            "evidence_file": "architecture-output/final/test-runtime-evidence-map.json",
        },
        "availability_and_health_clues": [
            {
                "interface_id": item.get("interface_id"),
                "method": item.get("method"),
                "path_or_name": item.get("path_or_name"),
                "source_file": item.get("source_file"),
                "line": item.get("line"),
            }
            for item in health_interfaces
        ],
        "security_and_identity_clues": [
            {
                "interface_id": item.get("interface_id"),
                "method": item.get("method"),
                "path_or_name": item.get("path_or_name"),
                "entry_component": item.get("entry_component"),
                "source_file": item.get("source_file"),
                "line": item.get("line"),
            }
            for item in identity_interfaces[:25]
        ],
        "external_dependency_clues": external,
        "nfr_requirements_to_confirm": [
            "Availability/SLO targets are not derivable from static code and must be supplied by stakeholders.",
            "Latency, throughput, and scaling targets are not derivable from static code and must be supplied by product/platform owners.",
            "Observability requirements for logs, metrics, traces, audit events, and dashboards require runtime/platform review.",
            "Security and compliance posture require a separate specialist review before production implementation.",
            "Disaster recovery, backup, retention, and restore requirements require operations and data-owner input.",
        ],
    }


def acceptance_criteria_model() -> list[dict[str, Any]]:
    return [
        {
            "area": "Interface compatibility",
            "criteria": "Every preserved API/frontend route has a target implementation decision and contract/regression test.",
            "evidence_inputs": ["application-interface-catalogue.json", "api-contract-preservation-map.json", "call-flow-map.json"],
        },
        {
            "area": "Module ownership",
            "criteria": "Every future module/service has confirmed owner, responsibility, data ownership, and allowed dependencies.",
            "evidence_inputs": ["module-boundary-map.json", "module-consolidation-map.json", "open-questions.md"],
        },
        {
            "area": "Layering",
            "criteria": "Target implementation documents allowed layer dependencies and explicitly rejects or accepts each detected violation.",
            "evidence_inputs": ["architecture-violation-register.json", "layering-pattern-pack.json"],
        },
        {
            "area": "Behavior preservation",
            "criteria": "Read, write, auth, admin, and reliability/error-path scenarios are implemented or intentionally redesigned with review approval.",
            "evidence_inputs": ["call-flow-map.json", "enterprise-application-architecture-blueprint.json"],
        },
        {
            "area": "Risk remediation",
            "criteria": "Each application risk is accepted, mitigated, redesigned, or converted into backlog work.",
            "evidence_inputs": ["application-risk-register.json", "forward-engineering-backlog.md"],
        },
        {
            "area": "Human review closure",
            "criteria": "Open questions are assigned and resolved before final target architecture sign-off.",
            "evidence_inputs": ["open-questions.md", "architecture-decision-inputs.md"],
        },
    ]


def open_questions(data: dict[str, Any], scenarios: list[dict[str, Any]]) -> list[str]:
    questions = []
    open_questions_path = data["final_root"] / "open-questions.md"
    if open_questions_path.exists():
        for line in open_questions_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- "):
                questions.append(line[2:].strip())
    for scenario in scenarios:
        if scenario.get("status") == "unknown":
            questions.extend(scenario.get("open_questions", []))
    questions.extend(
        [
            "Confirm business capability names and ownership with product/domain stakeholders before using this as a target bounded-context model.",
            "Confirm production deployment topology; static repository evidence may include local-development services.",
            "Confirm non-functional requirements such as availability, latency, scaling, observability, and recovery objectives from runtime and business sources.",
        ]
    )
    return unique(questions)


def build_blueprint(data: dict[str, Any]) -> dict[str, Any]:
    system = data["system"]
    modules = data["modules"].get("modules", [])
    components = data["components"].get("components", [])
    interfaces = data["interfaces"].get("interfaces", [])
    pattern = primary_pattern(data["layering_pack"])
    scenarios = business_scenarios(data["flows"])
    return {
        "generated_at": utc_now(),
        "generator_version": GENERATOR_VERSION,
        "source_artifacts_used": SOURCE_ARTIFACTS,
        "architecture_blueprint": {
            "document_purpose": "Enterprise Application Architecture blueprint for rebuilding or forward-engineering the application from legacy-code evidence.",
            "system_name": system.get("system_name", "unknown"),
            "architecture_type": "Application Architecture",
            "architecture_vision": {
                "current_system_identity": system.get("system_name", "unknown"),
                "detected_application_shape": f"{len(system.get('applications', []))} application/support project records with {len(system.get('deployable_units', []))} deployable unit candidates.",
                "intended_forward_engineering_outcome": "Preserve externally visible behavior and implementation-critical flows while redesigning weak boundaries, high coupling, and detected architecture violations.",
                "evidence": system.get("deployable_units", [])[:8],
            },
            "architecture_style_and_patterns": {
                "primary_pattern": pattern,
                "secondary_patterns": [
                    candidate for candidate in data["layering_pack"].get("candidate_patterns", [])
                    if candidate.get("pattern") != pattern.get("pattern")
                ],
                "style_decision_for_target": "Use the detected layered application style as the baseline behavior model, but do not blindly preserve weak module boundaries or layer violations.",
                "pattern_catalogue": architecture_pattern_catalogue(data),
            },
            "application_design_overview": architecture_design_overview(data),
            "applications_and_deployables": {
                "applications": system.get("applications", []),
                "deployable_units": system.get("deployable_units", []),
                "supporting_projects": system.get("supporting_projects", []),
                "test_projects": system.get("test_projects", []),
                "deployment_files": system.get("deployment_files", []),
                "docker_compose_services": system.get("docker_compose_services", []),
            },
        },
        "implementation_model": {
            "layers": layer_model(data["layering_pack"], data["violations"]),
            "modules": module_blueprints(data),
            "component_summary": {
                "component_count": len(components),
                "components_by_type": dict(Counter(component.get("type", "Unknown") for component in components)),
                "components_by_layer": dict(Counter(component.get("layer", "Unknown") for component in components)),
                "semantic_component_count": sum(1 for component in components if component.get("semantic_symbol_id")),
            },
            "implementation_architecture_by_concern": implementation_architecture_by_concern(data),
            "data_access_and_persistence": data_access_model(data["components"], data["external_pack"]),
            "frontend_application": frontend_model(data["frontend_pack"]),
        },
        "invocation_model": invocation_model(data["interfaces"], data["flows"]),
        "behavior_model": {
            "business_scenarios": scenarios,
            "call_flow_summary": data["flows"].get("summary", {}),
            "implementation_rule": "Use call flows as behavior-preservation contracts where confidence is high; treat medium/low confidence flows as review inputs.",
        },
        "enterprise_governance_model": {
            "stakeholder_usage": stakeholder_usage_model(),
            "architecture_decisions": architecture_decision_model(data),
            "nfr_and_operational_baseline": nfr_and_governance_model(data),
            "target_build_acceptance_criteria": acceptance_criteria_model(),
        },
        "dependency_and_integration_model": {
            "dependency_graph_summary": {
                "node_count": len(data["dependencies"].get("nodes", [])),
                "edge_count": len(data["dependencies"].get("edges", [])),
                "cycle_count": len(data["dependencies"].get("cycles", {}).get("module_cycles", [])),
                "high_coupling_modules": data["dependencies"].get("high_coupling_modules", []),
                "high_coupling_components": data["dependencies"].get("high_coupling_components", []),
            },
            "external_boundaries": data["external_pack"].get("external_dependencies", []),
            "integration_rules": [
                "External targets inferred only from static evidence must be confirmed before target integration design.",
                "High-coupling components should become explicit adapters, services, or module APIs in the target design.",
                "Detected cycles must be broken or intentionally accepted before module/service extraction.",
            ],
        },
        "forward_engineering_contract": forward_contract(data),
        "quality_and_confidence": {
            "quality_review_file": "architecture-output/final/quality-review.md",
            "accuracy_report_file": "architecture-output/final/source-crosscheck-accuracy-report.md",
            "known_limitations": [
                "Business capabilities are inferred from architecture evidence and need stakeholder validation.",
                "Runtime traces are not complete; call flows are static/semantic evidence, not production telemetry.",
                "Database design, security testing, and compliance posture require separate specialist review before implementation.",
            ],
        },
        "human_review_required": open_questions(data, scenarios),
    }


def render_markdown(blueprint: dict[str, Any]) -> str:
    arch = blueprint["architecture_blueprint"]
    impl = blueprint["implementation_model"]
    invocation = blueprint["invocation_model"]
    behavior = blueprint["behavior_model"]
    governance = blueprint["enterprise_governance_model"]
    dependency = blueprint["dependency_and_integration_model"]
    forward = blueprint["forward_engineering_contract"]
    questions = blueprint["human_review_required"]
    pattern = arch["architecture_style_and_patterns"]["primary_pattern"]
    design = arch["application_design_overview"]
    pattern_catalogue = arch["architecture_style_and_patterns"].get("pattern_catalogue", [])
    modules = impl["modules"]
    concerns = impl.get("implementation_architecture_by_concern", [])
    scenarios = behavior["business_scenarios"]
    deployables = arch["applications_and_deployables"]["deployable_units"]
    applications = arch["applications_and_deployables"]["applications"]
    layers = impl["layers"]["detected_layers"]
    preserve = forward["preserve"][:15]
    redesign = forward["redesign"][:10]
    no_carry = forward["do_not_carry_forward"][:10]
    stakeholder_rows = "\n".join(
        f"| {item.get('stakeholder')} | {item.get('use')} | {item.get('primary_sections')} |"
        for item in governance["stakeholder_usage"]
    )
    adr_rows = "\n".join(
        f"| {item.get('decision_id')} | {item.get('decision')} | {short_list(item.get('affected_modules', item.get('affected_violations', [])), 5)} | {item.get('why_it_matters')} |"
        for item in governance["architecture_decisions"]["decisions_required_before_build"]
    )
    nfr = governance["nfr_and_operational_baseline"]
    acceptance_rows = "\n".join(
        f"| {item.get('area')} | {item.get('criteria')} | {short_list(item.get('evidence_inputs', []), 4)} |"
        for item in governance["target_build_acceptance_criteria"]
    )
    pattern_rows = "\n".join(
        f"| {item.get('pattern_or_style')} | {item.get('implementation_meaning')} | {item.get('target_guidance')} | {short_list(item.get('evidence', []), 3)} | {item.get('confidence')} |"
        for item in pattern_catalogue
    )
    concern_sections = []
    for concern in concerns:
        concern_sections.append(
            f"""### {concern.get('concern')}

Legacy design: {concern.get('legacy_design')}

Target implementation design: {concern.get('implementation_design')}

Evidence:

{md_list(concern.get('evidence', []))}
"""
        )

    module_rows = "\n".join(
        "| {module_id} | {name} | {boundary_quality} | {migration_readiness} | {component_count} | {entries} | {depends} |".format(
            module_id=module.get("module_id", ""),
            name=module.get("name", ""),
            boundary_quality=module.get("boundary_quality", ""),
            migration_readiness=module.get("migration_readiness", ""),
            component_count=module.get("component_count", 0),
            entries=len(module.get("entry_points_to_preserve_or_review", [])),
            depends=short_list(module.get("depends_on_modules", []), 4),
        )
        for module in modules
    )
    scenario_sections = []
    for scenario in scenarios:
        steps = scenario.get("layers_traced", [])
        step_rows = "\n".join(
            f"| {step.get('step')} | {step.get('component')} | {step.get('layer')} | {step.get('module')} | {step.get('action')} | {step.get('file')} |"
            for step in steps
        ) or "| GAP | GAP | GAP | GAP | GAP | GAP |"
        scenario_sections.append(
            f"""### {scenario.get('scenario_id')}: {scenario.get('name')}

Type: `{scenario.get('type')}`  
Status: `{scenario.get('status')}`  
Entry point: `{scenario.get('entry_point')}`  
Confidence: `{scenario.get('confidence')}`

Implementation contract: {scenario.get('implementation_contract')}

Flow narrative: {scenario.get('flow_narrative')}

| Step | Component | Layer | Module | Action | Source |
|---:|---|---|---|---|---|
{step_rows}
"""
        )

    return f"""# Enterprise Application Architecture Blueprint

## 1. Purpose

This document is the implementation-oriented Application Architecture blueprint for forward engineering this repository. It is written as if a team were rebuilding the application from scratch, but every major input is derived from generated reverse-engineering evidence.

The goal is not to copy the legacy code line-for-line. The goal is to preserve externally visible behavior and proven architectural responsibilities while redesigning weak boundaries, high coupling, and violations.

Source artifacts used:

{md_list(blueprint.get('source_artifacts_used', []))}

## 2. Architecture Vision

Architecture type: `Application Architecture`

Detected system name: `{arch.get('system_name', 'unknown')}`

Detected application shape: {arch['architecture_vision']['detected_application_shape']}

Forward-engineering outcome: {arch['architecture_vision']['intended_forward_engineering_outcome']}

System name remains `unknown` because no authoritative source-backed system-name artifact was found.

## 3. Application Design Overview

Design narrative:

{md_list(design['design_narrative'])}

Target design posture:

{md_list(design['target_design_posture'])}

Technology/style clues found in project evidence:

{md_list(design['technology_style_clues'])}

## 4. Pattern And Style Catalogue

This catalogue is the main design interpretation layer. It explains the implementation styles found in the legacy code and how they should influence a new build.

| Pattern / Style | What It Means In This Application | Target Implementation Guidance | Evidence | Confidence |
|---|---|---|---|---:|
{pattern_rows}

## 5. Applications And Deployable Units

Detected application/support records: {len(applications)}

Deployable unit candidates: {short_list([item.get('name') for item in deployables])}

| Unit | Type | Source Path | Framework | Evidence Confidence |
|---|---|---|---|---:|
{chr(10).join(f"| {item.get('name')} | {item.get('type')} | {item.get('source_path')} | {item.get('framework', 'unknown')} | {item.get('confidence', 0.0)} |" for item in deployables) if deployables else "| none detected | unknown | unknown | unknown | 0.0 |"}

Implementation meaning:

- Treat deployable units as runtime entry containers until deployment ownership is confirmed.
- Keep support/test projects separate from production module ownership.
- Do not infer cloud platform or production topology unless deployment evidence proves it.

## 6. Architecture Style And Pattern

Primary detected pattern: `{pattern.get('pattern', 'Unknown')}` with confidence `{pattern.get('confidence', 0.0)}`.

Pattern evidence: {pattern.get('evidence', 'unknown')}

Target style guidance: {arch['architecture_style_and_patterns']['style_decision_for_target']}

Secondary candidates: {short_list([item.get('pattern') for item in arch['architecture_style_and_patterns']['secondary_patterns']])}

## 7. Layer Model To Implement

| Layer | Component Count | Evidence Examples |
|---|---:|---|
{chr(10).join(f"| {layer.get('layer')} | {layer.get('component_count', 0)} | {short_list(layer.get('evidence_files', []), 3)} |" for layer in layers)}

Layer rules:

{md_list(impl['layers']['layer_rules_for_forward_engineering'])}

Do not blindly carry forward:

{md_list([f"{item.get('violation_id')}: {item.get('description')}" for item in impl['layers']['violations_not_to_carry_forward'][:10]])}

## 8. Module Blueprint

These are evidence-derived module candidates, not automatically confirmed future bounded contexts.

| ID | Module | Boundary | Migration Readiness | Components | Entry Points | Depends On |
|---|---|---|---|---:|---:|---|
{module_rows}

Module implementation guidance:

{md_list([f"{module.get('name')}: {short_list(module.get('implementation_guidance', []), 3)}" for module in modules])}

Module design contracts:

{md_list([f"{module.get('module_id')} {module.get('name')}: {module.get('design_role')} Target contract: {module.get('target_implementation_contract')} Patterns: {short_list(module.get('pattern_signals', []), 5)}" for module in modules])}

## 9. Component Model

Total components: {impl['component_summary']['component_count']}

Components by type: `{json.dumps(impl['component_summary']['components_by_type'], sort_keys=True)}`

Components by layer: `{json.dumps(impl['component_summary']['components_by_layer'], sort_keys=True)}`

Components with Roslyn semantic symbol evidence: {impl['component_summary']['semantic_component_count']}

Implementation meaning:

- Controllers/API endpoints and frontend components should be treated as invocation adapters.
- Services and handlers should own use-case orchestration.
- Repositories, DbContexts, and external clients should be adapters behind explicit contracts.
- Unknown components should be reviewed before deciding whether they are architecture-significant.

## 10. Implementation Architecture By Concern

{chr(10).join(concern_sections)}

## 11. Invocation Model

Entry point count: {invocation['summary']['entry_point_count']}

Entry points by type: `{json.dumps(invocation['summary']['entry_points_by_type'], sort_keys=True)}`

HTTP methods: `{json.dumps(invocation['summary']['http_methods'], sort_keys=True)}`

Entry points by module: `{json.dumps(invocation['summary']['entry_points_by_module'], sort_keys=True)}`

Implementation rules:

{md_list(invocation['implementation_rules'])}

Representative API contracts to preserve or review:

{md_list([f"{item.get('interface_id')}: {item.get('method')} {item.get('path_or_name')} -> {item.get('entry_component')} ({item.get('owner_module')}) [{item.get('source_file')}:{item.get('line')}]" for item in invocation['http_api_contracts'][:20]])}

## 12. Behavior And Scenario Model

Call flows detected: {behavior['call_flow_summary'].get('flow_count', 0)}

Semantic trace flows: {behavior['call_flow_summary'].get('semantic_trace_flow_count', 0)}

Flows with data access: {behavior['call_flow_summary'].get('flows_with_data_access_count', 0)}

Flows with external systems: {behavior['call_flow_summary'].get('flows_with_external_system_count', 0)}

{chr(10).join(scenario_sections)}

## 13. Data Access And Persistence Model

Repository candidates: {len(impl['data_access_and_persistence']['repositories'])}

Entity candidates: {len(impl['data_access_and_persistence']['entities'])}

Database context/session candidates: {len(impl['data_access_and_persistence']['database_context_or_session_candidates'])}

Database/infrastructure boundaries: {short_list([item.get('target_system') for item in impl['data_access_and_persistence']['database_or_infrastructure_boundaries']])}

Implementation rules:

{md_list(impl['data_access_and_persistence']['implementation_rules'])}

## 14. Frontend Architecture Model

Frontend status: `{impl['frontend_application']['status']}`

Frontend apps detected: {short_list([app.get('name') for app in impl['frontend_application']['frontend_apps']])}

Implementation rules:

{md_list(impl['frontend_application']['implementation_rules'])}

## 15. Dependency And Integration Model

Dependency graph nodes: {dependency['dependency_graph_summary']['node_count']}

Dependency graph edges: {dependency['dependency_graph_summary']['edge_count']}

Module cycle count: {dependency['dependency_graph_summary']['cycle_count']}

High-coupling modules: {short_list([item.get('name') for item in dependency['dependency_graph_summary']['high_coupling_modules']])}

High-coupling components: {short_list([item.get('name') for item in dependency['dependency_graph_summary']['high_coupling_components']])}

External boundaries: {short_list([item.get('target_system') for item in dependency['external_boundaries']])}

Integration rules:

{md_list(dependency['integration_rules'])}

## 16. Forward Engineering Contract

Preserve these behavior/API contracts unless an explicit replacement plan exists:

{md_list([f"{item.get('contract_id')}: {item.get('method')} {item.get('path_or_name')} ({item.get('owner_module')})" for item in preserve])}

Redesign before carrying forward:

{md_list([f"{item.get('risk_id')}: {item.get('description')}" for item in redesign])}

Do not blindly carry forward architecture violations:

{md_list([f"{item.get('violation_id')}: {item.get('description')}" for item in no_carry])}

Review before final target design:

{md_list([f"{item.get('capability_id')}: {item.get('name')} -> {item.get('decision')}" for item in forward['review'][:15]])}

## 17. Enterprise Governance And Stakeholders

This section explains who should use this blueprint and what each stakeholder should validate.

| Stakeholder | Use | Primary Sections |
|---|---|---|
{stakeholder_rows}

## 18. Architecture Decisions Required Before Build

These are not optional documentation items. They are decisions that should be closed before treating this as a final target architecture.

| ID | Decision | Affected Items | Why It Matters |
|---|---|---|---|
{adr_rows}

## 19. NFR And Operational Baseline

Runtime evidence status: `{nfr['runtime_test_evidence'].get('status')}`

Runtime evidence summary: `{json.dumps(nfr['runtime_test_evidence'].get('summary', {}), sort_keys=True)}`

Availability/health-check clues:

{md_list([f"{item.get('interface_id')}: {item.get('method')} {item.get('path_or_name')} [{item.get('source_file')}:{item.get('line')}]" for item in nfr['availability_and_health_clues']])}

Security/identity clues:

{md_list([f"{item.get('interface_id')}: {item.get('method')} {item.get('path_or_name')} -> {item.get('entry_component')} [{item.get('source_file')}:{item.get('line')}]" for item in nfr['security_and_identity_clues'][:15]])}

NFR requirements to confirm:

{md_list(nfr['nfr_requirements_to_confirm'])}

## 20. Target Build Acceptance Criteria

| Area | Criteria | Evidence Inputs |
|---|---|---|
{acceptance_rows}

## 21. Implementation Inputs For A New Build

Use this package as input to create the target implementation backlog:

- Use `application-interface-catalogue.json` and `api-contract-preservation-map.json` as interface contracts.
- Use `module-boundary-map.json` and this module blueprint as candidate module ownership.
- Use `call-flow-map.json` and the scenario model above as behavior-preservation input.
- Use `dependency-graph.json` to break cycles and reduce coupling before extraction.
- Use `application-risk-register.json` and `architecture-violation-register.json` as avoid-carry-forward controls.
- Use `open-questions.md` as the human review queue.

## 22. Human Review Required

{md_list(questions)}
"""


def load_data(output_root: Path) -> dict[str, Any]:
    final_root = output_root / "final"
    evidence_root = output_root / "evidence-packs"
    inventory_root = output_root / "inventory"
    return {
        "final_root": final_root,
        "project_inventory": load_json(inventory_root / "project-inventory.json", {"projects": []}),
        "system": load_json(final_root / "system-inventory.json", {}),
        "modules": load_json(final_root / "module-boundary-map.json", {"modules": []}),
        "components": load_json(final_root / "component-registry.json", {"components": []}),
        "dependencies": load_json(final_root / "dependency-graph.json", {"nodes": [], "edges": [], "cycles": {}}),
        "interfaces": load_json(final_root / "application-interface-catalogue.json", {"interfaces": []}),
        "flows": load_json(final_root / "call-flow-map.json", {"flows": [], "summary": {}}),
        "violations": load_json(final_root / "architecture-violation-register.json", {"violations": []}),
        "risks": load_json(final_root / "application-risk-register.json", {"risks": []}),
        "capabilities": load_json(final_root / "business-capability-map.json", {"capabilities": []}),
        "module_consolidation": load_json(final_root / "module-consolidation-map.json", {"consolidated_modules": []}),
        "api_contracts": load_json(final_root / "api-contract-preservation-map.json", {"api_contracts": []}),
        "runtime_evidence": load_json(final_root / "test-runtime-evidence-map.json", {}),
        "layering_pack": load_json(evidence_root / "layering-pattern-pack.json", {"candidate_patterns": [], "detected_layers": []}),
        "external_pack": load_json(evidence_root / "external-boundary-pack.json", {"external_dependencies": []}),
        "frontend_pack": load_json(evidence_root / "frontend-application-pack.json", {"frontend_apps": []}),
    }


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root).resolve()
    final_root = output_root / "final"
    data = load_data(output_root)
    blueprint = build_blueprint(data)
    write_json(final_root / "enterprise-application-architecture-blueprint.json", blueprint)
    write_text(final_root / "enterprise-application-architecture-blueprint.md", render_markdown(blueprint))
    print(
        json.dumps(
            {
                "enterprise_application_architecture_blueprint": str(final_root / "enterprise-application-architecture-blueprint.md"),
                "machine_readable_blueprint": str(final_root / "enterprise-application-architecture-blueprint.json"),
                "module_count": len(blueprint["implementation_model"]["modules"]),
                "entry_point_count": blueprint["invocation_model"]["summary"]["entry_point_count"],
                "scenario_count": len(blueprint["behavior_model"]["business_scenarios"]),
                "human_review_question_count": len(blueprint["human_review_required"]),
            },
            indent=2,
        )
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an enterprise application architecture blueprint from final architecture artifacts.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
