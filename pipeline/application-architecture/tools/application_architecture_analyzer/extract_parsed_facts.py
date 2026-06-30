#!/usr/bin/env python3
"""
Parser/symbol extraction phase for application architecture extraction.

Inputs:
  - architecture-output/inventory/file-inventory.json
  - architecture-output/inventory/project-inventory.json
  - architecture-output/inventory/language-summary.json

Outputs:
  - architecture-output/parsed/symbol-registry.json
  - architecture-output/parsed/route-registry.json
  - architecture-output/parsed/dependency-candidates.json
  - architecture-output/parsed/entry-point-candidates.json

The extractor adapts to the technologies detected by Step 1. XML/JSON inputs
are parsed with structured parsers. C# and Razor use framework-specific static
parsing by default, and the extractor records whether optional compiler/AST
backends such as Roslyn (`dotnet`) or tree-sitter are available.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


EXTRACTOR_VERSION = "0.2.0"

COMPONENT_TYPES = {
    "Controller",
    "Service",
    "Repository",
    "Entity",
    "DTO",
    "Mapper",
    "Validator",
    "Handler",
    "Gateway",
    "ExternalClient",
    "Middleware",
    "Configuration",
    "FrontendComponent",
    "FrontendService",
    "RouteGuard",
    "StateStore",
    "ScheduledJob",
    "MessageConsumer",
    "BatchJob",
    "Unknown",
}

LAYERS = {
    "Presentation/UI",
    "API",
    "Application",
    "Domain",
    "Infrastructure",
    "DataAccess",
    "Integration",
    "CrossCutting",
    "Unknown",
}

HTTP_METHOD_BY_MAP = {
    "Get": "GET",
    "Post": "POST",
    "Put": "PUT",
    "Patch": "PATCH",
    "Delete": "DELETE",
}

PRIMITIVE_TYPES = {
    "ActionResult",
    "bool",
    "byte",
    "CancellationToken",
    "char",
    "DateTime",
    "decimal",
    "double",
    "float",
    "Guid",
    "IActionResult",
    "IEnumerable",
    "IResult",
    "int",
    "long",
    "object",
    "short",
    "string",
    "Task",
    "uint",
    "ulong",
    "void",
}

DTO_LIKE_SUFFIXES = (
    "Dto",
    "DTO",
    "Request",
    "Response",
    "Result",
    "ViewModel",
    "Model",
)

ARCHITECTURE_DEPENDENCY_HINTS = (
    "Client",
    "Context",
    "Gateway",
    "Logger",
    "Manager",
    "Mapper",
    "Mediator",
    "Repository",
    "Sender",
    "Service",
    "Store",
)

IGNORED_SOURCE_PATTERNS = [
    "/Migrations/",
    "ModelSnapshot.cs",
]

CLASS_RE = re.compile(
    r"(?m)^\s*"
    r"(?:(?:public|internal|private|protected)\s+)?"
    r"(?:(?:abstract|static|sealed|partial|readonly|unsafe|new)\s+)*"
    r"(?P<kind>class|interface|struct|enum|record(?:\s+(?:class|struct))?)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*<(?P<generic>[^>{}\n]+)>)?"
    r"(?:\s*:\s*(?P<bases>[^{;\n]+))?"
)

NAMESPACE_FILE_SCOPED_RE = re.compile(r"(?m)^\s*namespace\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;")
NAMESPACE_BLOCK_RE = re.compile(r"(?m)^\s*namespace\s+([A-Za-z_][A-Za-z0-9_.]*)\s*\{")
USING_RE = re.compile(r"(?m)^\s*using\s+(?:static\s+)?(?:(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\s*;")


@dataclass
class ProjectContext:
    name: str
    path: str
    source_path: str
    category: str
    type: str
    framework: str
    package_references: list[str] = field(default_factory=list)
    project_references: list[str] = field(default_factory=list)


@dataclass
class ClassCandidate:
    name: str
    kind: str
    namespace: str | None
    file: str
    language: str
    project: str | None
    project_type: str | None
    project_category: str | None
    start_line: int
    end_line: int | None
    start_index: int
    end_index: int | None
    body_start_index: int
    bases: list[str]
    annotations: list[str]
    usings: list[str]
    body: str
    text: str
    parser_backend: str = "static_structural"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def normalize_slashes(value: str) -> str:
    return value.replace("\\", "/")


def is_probably_generated_source(path: str) -> tuple[bool, str | None]:
    probe = "/" + normalize_slashes(path)
    for pattern in IGNORED_SOURCE_PATTERNS:
        if pattern in probe or path.endswith(pattern):
            return True, f"generated_or_migration_pattern:{pattern}"
    return False, None


def line_number_at(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def line_start_indices(text: str) -> list[int]:
    starts = [0]
    for match in re.finditer("\n", text):
        starts.append(match.end())
    return starts


def index_for_line(starts: list[int], line_number: int) -> int:
    if line_number <= 1:
        return 0
    if line_number - 1 >= len(starts):
        return starts[-1]
    return starts[line_number - 1]


def find_matching_brace(text: str, open_index: int) -> int | None:
    depth = 0
    i = open_index
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    verbatim_string = False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if char == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_string:
            if verbatim_string:
                if char == '"' and nxt == '"':
                    i += 2
                    continue
                if char == '"':
                    in_string = False
                    verbatim_string = False
            else:
                if char == "\\":
                    i += 2
                    continue
                if char == '"':
                    in_string = False
            i += 1
            continue
        if in_char:
            if char == "\\":
                i += 2
                continue
            if char == "'":
                in_char = False
            i += 1
            continue

        if char == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if char == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if char == "@" and nxt == '"':
            in_string = True
            verbatim_string = True
            i += 2
            continue
        if char == '"':
            in_string = True
            verbatim_string = False
            i += 1
            continue
        if char == "'":
            in_char = True
            i += 1
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def split_top_level_commas(value: str) -> list[str]:
    items: list[str] = []
    depth_angle = 0
    depth_paren = 0
    current: list[str] = []
    for char in value:
        if char == "<":
            depth_angle += 1
        elif char == ">":
            depth_angle = max(0, depth_angle - 1)
        elif char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren = max(0, depth_paren - 1)
        if char == "," and depth_angle == 0 and depth_paren == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)
    item = "".join(current).strip()
    if item:
        items.append(item)
    return items


def clean_type_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\b(in|out|ref|params)\s+", "", value)
    value = value.replace("?", "")
    value = value.replace("global::", "")
    return value.strip()


def simple_type_name(value: str) -> str:
    value = clean_type_name(value)
    value = re.sub(r"\([^)]*\)", "", value)
    value = value.replace("typeof", "")
    value = value.strip("<> ")
    if "<" in value:
        value = value.split("<", 1)[0]
    if "." in value:
        value = value.rsplit(".", 1)[-1]
    return value.strip()


def is_primitive_type(value: str) -> bool:
    simple = simple_type_name(value)
    if not simple:
        return True
    if simple in PRIMITIVE_TYPES:
        return True
    if simple.endswith("[]") and simple[:-2] in PRIMITIVE_TYPES:
        return True
    return False


def is_dto_like_type(value: str) -> bool:
    simple = simple_type_name(value)
    return any(simple.endswith(suffix) for suffix in DTO_LIKE_SUFFIXES)


def is_architecture_dependency_type(value: str) -> bool:
    simple = simple_type_name(value)
    if not simple or is_primitive_type(simple):
        return False
    if is_dto_like_type(simple):
        return False
    if simple.startswith("I") and len(simple) > 2:
        return True
    return any(token in simple for token in ARCHITECTURE_DEPENDENCY_HINTS)


def parse_parameters(params_text: str) -> list[dict[str, str]]:
    params_text = params_text.strip()
    if not params_text:
        return []
    params_text = re.sub(r"//.*", "", params_text)
    result: list[dict[str, str]] = []
    for raw in split_top_level_commas(params_text):
        without_default = raw.split("=", 1)[0].strip()
        without_attrs = re.sub(r"\[[^\]]+\]\s*", "", without_default).strip()
        parts = without_attrs.split()
        if len(parts) < 2:
            continue
        name = parts[-1].lstrip("@")
        type_name = " ".join(parts[:-1])
        type_name = clean_type_name(type_name)
        if name and type_name:
            result.append({"type": type_name, "name": name})
    return result


def extract_namespace(text: str) -> str | None:
    match = NAMESPACE_FILE_SCOPED_RE.search(text)
    if match:
        return match.group(1)
    match = NAMESPACE_BLOCK_RE.search(text)
    if match:
        return match.group(1)
    return None


def extract_usings(text: str) -> list[str]:
    return sorted({match.group("name") for match in USING_RE.finditer(text)})


def previous_attribute_lines(lines: list[str], start_line: int) -> list[str]:
    attributes: list[str] = []
    i = start_line - 2
    collecting_multiline = False
    saw_attribute = False
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped:
            if saw_attribute:
                break
            i -= 1
            continue
        if stripped.startswith("]") or collecting_multiline:
            attributes.insert(0, stripped)
            saw_attribute = True
            if stripped.startswith("["):
                collecting_multiline = False
            else:
                collecting_multiline = True
            i -= 1
            continue
        if stripped.startswith("["):
            attributes.insert(0, stripped)
            saw_attribute = True
            i -= 1
            continue
        break
    return attributes


def attribute_names(attributes: list[str]) -> list[str]:
    names: list[str] = []
    for attr in attributes:
        for match in re.finditer(r"\[+\s*([A-Za-z_][A-Za-z0-9_.]*)", attr):
            names.append(match.group(1).rsplit(".", 1)[-1])
    return sorted(set(names))


def parse_csharp_classes(file_path: Path, rel_path: str, project: ProjectContext | None) -> list[ClassCandidate]:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    namespace = extract_namespace(text)
    usings = extract_usings(text)
    candidates: list[ClassCandidate] = []

    for match in CLASS_RE.finditer(text):
        name = match.group("name")
        kind = match.group("kind").replace("  ", " ")
        start_line = line_number_at(text, match.start())
        open_index = text.find("{", match.end())
        end_index = None
        end_line = None
        body_start_index = match.end()
        body = ""
        if open_index != -1:
            body_start_index = open_index + 1
            end_index = find_matching_brace(text, open_index)
            if end_index is not None:
                end_line = line_number_at(text, end_index)
                body = text[open_index + 1 : end_index]
        bases_text = match.group("bases") or ""
        bases = [clean_type_name(item) for item in split_top_level_commas(bases_text) if item.strip()]
        annotations = previous_attribute_lines(lines, start_line)
        candidates.append(
            ClassCandidate(
                name=name,
                kind=kind,
                namespace=namespace,
                file=rel_path,
                language="csharp",
                project=project.name if project else None,
                project_type=project.type if project else None,
                project_category=project.category if project else None,
                start_line=start_line,
                end_line=end_line,
                start_index=match.start(),
                end_index=end_index,
                body_start_index=body_start_index,
                bases=bases,
                annotations=annotations,
                usings=usings,
                body=body,
                text=text,
            )
        )

    if rel_path.endswith("/Program.cs") and not any(candidate.name == "Program" for candidate in candidates):
        candidates.append(
            ClassCandidate(
                name="Program",
                kind="top-level-statements",
                namespace=namespace,
                file=rel_path,
                language="csharp",
                project=project.name if project else None,
                project_type=project.type if project else None,
                project_category=project.category if project else None,
                start_line=1,
                end_line=len(lines),
                start_index=0,
                end_index=len(text),
                body_start_index=0,
                bases=[],
                annotations=[],
                usings=usings,
                body=text,
                text=text,
            )
        )

    return candidates


CSHARP_TREE_SITTER_NODE_TYPES = {
    "class_declaration",
    "interface_declaration",
    "struct_declaration",
    "enum_declaration",
    "record_declaration",
    "record_struct_declaration",
}


def tree_sitter_csharp_available() -> bool:
    return importlib.util.find_spec("tree_sitter") is not None and importlib.util.find_spec("tree_sitter_c_sharp") is not None


def tree_sitter_text(source: bytes, node: Any | None) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def iter_tree_sitter_nodes(node: Any) -> Any:
    yield node
    for child in getattr(node, "children", []) or []:
        yield from iter_tree_sitter_nodes(child)


def first_child_of_type(node: Any, node_type: str) -> Any | None:
    for child in getattr(node, "children", []) or []:
        if child.type == node_type:
            return child
    return None


def extract_tree_sitter_namespace(source: bytes, root_node: Any) -> str | None:
    for node in iter_tree_sitter_nodes(root_node):
        if node.type in {"file_scoped_namespace_declaration", "namespace_declaration"}:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                return tree_sitter_text(source, name_node)
    return None


def tree_sitter_declaration_kind(node_type: str) -> str:
    return node_type.replace("_declaration", "").replace("_", " ")


def parse_csharp_classes_tree_sitter(file_path: Path, rel_path: str, project: ProjectContext | None) -> list[ClassCandidate]:
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_c_sharp
    except Exception:
        return parse_csharp_classes(file_path, rel_path, project)

    source = file_path.read_bytes()
    text = source.decode("utf-8", errors="replace")
    lines = text.splitlines()
    parser = Parser()
    parser.language = Language(tree_sitter_c_sharp.language())
    tree = parser.parse(source)
    namespace = extract_tree_sitter_namespace(source, tree.root_node) or extract_namespace(text)
    usings = extract_usings(text)
    candidates: list[ClassCandidate] = []

    for node in iter_tree_sitter_nodes(tree.root_node):
        if node.type not in CSHARP_TREE_SITTER_NODE_TYPES:
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            name_node = first_child_of_type(node, "identifier")
        if name_node is None:
            continue
        name = tree_sitter_text(source, name_node).strip()
        if not name:
            continue
        body_node = node.child_by_field_name("body") or first_child_of_type(node, "declaration_list")
        body = tree_sitter_text(source, body_node)
        body_start_index = body_node.start_byte if body_node is not None else node.end_byte
        if body.startswith("{") and body.endswith("}"):
            body = body[1:-1]
            body_start_index += 1
        base_node = first_child_of_type(node, "base_list")
        bases_text = tree_sitter_text(source, base_node)
        bases_text = bases_text[1:].strip() if bases_text.startswith(":") else bases_text
        bases = [clean_type_name(item) for item in split_top_level_commas(bases_text) if item.strip()]
        annotations = [tree_sitter_text(source, child) for child in node.children if child.type == "attribute_list"]
        start_line = node.start_point[0] + 1
        candidates.append(
            ClassCandidate(
                name=name,
                kind=tree_sitter_declaration_kind(node.type),
                namespace=namespace,
                file=rel_path,
                language="csharp",
                project=project.name if project else None,
                project_type=project.type if project else None,
                project_category=project.category if project else None,
                start_line=start_line,
                end_line=node.end_point[0] + 1,
                start_index=node.start_byte,
                end_index=node.end_byte,
                body_start_index=body_start_index,
                bases=bases,
                annotations=annotations or previous_attribute_lines(lines, start_line),
                usings=usings,
                body=body,
                text=text,
                parser_backend="tree_sitter_csharp_ast",
            )
        )

    if rel_path.endswith("/Program.cs") and not any(candidate.name == "Program" for candidate in candidates):
        candidates.append(
            ClassCandidate(
                name="Program",
                kind="top-level-statements",
                namespace=namespace,
                file=rel_path,
                language="csharp",
                project=project.name if project else None,
                project_type=project.type if project else None,
                project_category=project.category if project else None,
                start_line=1,
                end_line=len(lines),
                start_index=0,
                end_index=len(text),
                body_start_index=0,
                bases=[],
                annotations=[],
                usings=usings,
                body=text,
                text=text,
                parser_backend="tree_sitter_csharp_ast",
            )
        )

    return candidates or parse_csharp_classes(file_path, rel_path, project)


def method_matches(body: str, class_name: str, class_kind: str) -> list[dict[str, Any]]:
    methods: list[dict[str, Any]] = []
    method_re = re.compile(
        r"(?m)^\s*public\s+"
        r"(?:(?:static|async|override|virtual|abstract|sealed|new|partial)\s+)*"
        r"(?P<return>[A-Za-z_][A-Za-z0-9_<>,\[\]\?\.]*(?:\s*<[^;\n{}]+>)?)\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
        r"\((?P<params>[^;{}]*)\)"
    )
    for match in method_re.finditer(body):
        name = match.group("name")
        if name == class_name:
            continue
        methods.append(
            {
                "name": name,
                "return_type": clean_type_name(match.group("return")),
                "parameters": parse_parameters(match.group("params")),
                "relative_index": match.start(),
            }
        )

    if class_kind.startswith("interface"):
        interface_re = re.compile(
            r"(?m)^\s*(?P<return>[A-Za-z_][A-Za-z0-9_<>,\[\]\?\.]*(?:\s*<[^;\n{}]+>)?)\s+"
            r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^;{}]*)\)\s*;"
        )
        existing = {method["name"] for method in methods}
        for match in interface_re.finditer(body):
            name = match.group("name")
            if name not in existing:
                methods.append(
                    {
                        "name": name,
                        "return_type": clean_type_name(match.group("return")),
                        "parameters": parse_parameters(match.group("params")),
                        "relative_index": match.start(),
                    }
                )
    return methods


def find_constructor_dependencies(candidate: ClassCandidate) -> tuple[list[dict[str, Any]], dict[str, str]]:
    constructor_re = re.compile(
        rf"(?s)(?:public|internal|protected|private)\s+{re.escape(candidate.name)}\s*\((?P<params>.*?)\)\s*[:{{]"
    )
    dependencies: list[dict[str, Any]] = []
    param_to_type: dict[str, str] = {}
    for match in constructor_re.finditer(candidate.body):
        for param in parse_parameters(match.group("params")):
            dependencies.append(
                {
                    "type": param["type"],
                    "name": param["name"],
                    "source": "constructor",
                    "confidence": 0.9,
                }
            )
            param_to_type[param["name"]] = param["type"]
    return dependencies, param_to_type


def find_field_types(candidate: ClassCandidate) -> dict[str, str]:
    field_types: dict[str, str] = {}
    field_re = re.compile(
        r"(?m)^\s*(?:private|protected|internal)\s+(?:readonly\s+)?(?P<type>[A-Za-z_][A-Za-z0-9_<>,\.\?]*)\s+(?P<name>_[A-Za-z_][A-Za-z0-9_]*)\s*;"
    )
    for match in field_re.finditer(candidate.body):
        field_types[match.group("name")] = clean_type_name(match.group("type"))
    return field_types


def find_property_injections(candidate: ClassCandidate) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    injection_re = re.compile(
        r"(?ms)(?:\[Inject\]|\[Microsoft\.AspNetCore\.Components\.Inject\])\s*"
        r"public\s+(?P<type>[A-Za-z_][A-Za-z0-9_<>,\.\?]*)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{"
    )
    for match in injection_re.finditer(candidate.body):
        dependencies.append(
            {
                "type": clean_type_name(match.group("type")),
                "name": match.group("name"),
                "source": "property_injection",
                "confidence": 0.9,
            }
            )
    return dependencies


def find_method_parameter_dependencies(method_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    for method in method_details:
        for param in method.get("parameters", []) or []:
            param_type = param.get("type", "")
            if not is_architecture_dependency_type(param_type):
                continue
            dependencies.append(
                {
                    "type": param_type,
                    "name": param.get("name", ""),
                    "source": "method_parameter",
                    "method": method.get("name", "unknown"),
                    "confidence": 0.76,
                }
            )
    return unique_dicts(dependencies, ["type", "name", "method"])


def infer_field_dependency_map(candidate: ClassCandidate, constructor_param_types: dict[str, str], field_types: dict[str, str]) -> dict[str, str]:
    mapping = dict(field_types)
    assignment_re = re.compile(r"(?m)\b(?P<field>_[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<param>[A-Za-z_][A-Za-z0-9_]*)\s*;")
    for match in assignment_re.finditer(candidate.body):
        param = match.group("param")
        if param in constructor_param_types:
            mapping[match.group("field")] = constructor_param_types[param]
    return mapping


def extract_method_body(candidate: ClassCandidate, method_relative_index: int) -> str:
    absolute = candidate.body_start_index + method_relative_index
    open_index = candidate.text.find("{", absolute)
    if open_index == -1 or (candidate.end_index and open_index > candidate.end_index):
        return ""
    close_index = find_matching_brace(candidate.text, open_index)
    if close_index is None:
        return ""
    return candidate.text[open_index + 1 : close_index]


def method_parameter_type_map(method: dict[str, Any]) -> dict[str, str]:
    return {
        param.get("name", ""): param.get("type", "")
        for param in method.get("parameters", []) or []
        if param.get("name") and param.get("type")
    }


def local_variable_type_map(method_body: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    new_re = re.compile(
        r"\b(?:var|(?P<declared>[A-Za-z_][A-Za-z0-9_<>,\.\?]*))\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:await\s+)?new\s+"
        r"(?P<type>[A-Za-z_][A-Za-z0-9_<>,\.\?]*)"
    )
    for match in new_re.finditer(method_body):
        mapping[match.group("name")] = clean_type_name(match.group("type") or match.group("declared") or "")
    typed_re = re.compile(
        r"\b(?P<type>[A-Za-z_][A-Za-z0-9_<>,\.\?]*)\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    )
    for match in typed_re.finditer(method_body):
        name = match.group("name")
        if name not in mapping and is_architecture_dependency_type(match.group("type")):
            mapping[name] = clean_type_name(match.group("type"))
    return {key: value for key, value in mapping.items() if value}


def find_component_calls(candidate: ClassCandidate, field_map: dict[str, str]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    call_re = re.compile(r"\b(?P<target>_[A-Za-z_][A-Za-z0-9_]*|[A-Z][A-Za-z0-9_]*)\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for match in call_re.finditer(candidate.body):
        target = match.group("target")
        method = match.group("method")
        if target in {"Task", "Math", "Guid", "DateTime", "JsonSerializer", "Enum", "Results", "Console", "Path", "Convert", "StringComparer"}:
            continue
        target_type = field_map.get(target, target if target[:1].isupper() else None)
        if not target_type:
            continue
        calls.append(
            {
                "target": target,
                "target_type": target_type,
                "method": method,
                "line": line_number_at(candidate.text, candidate.body_start_index + match.start()),
            }
        )
    return unique_dicts(calls, ["target", "target_type", "method", "line"])


def find_method_component_calls(
    candidate: ClassCandidate,
    field_map: dict[str, str],
    method_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    call_re = re.compile(r"\b(?P<target>_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
    ignored_static_targets = {
        "Array",
        "Convert",
        "Console",
        "DateTime",
        "Enum",
        "Guid",
        "JsonSerializer",
        "Math",
        "Path",
        "Results",
        "StringComparer",
        "Task",
    }
    ignored_instance_targets = {
        "HttpContext",
        "ModelState",
        "Request",
        "Response",
        "User",
    }
    for method in method_details:
        method_body = extract_method_body(candidate, method.get("relative_index", 0))
        if not method_body:
            continue
        type_map = {
            **field_map,
            **method_parameter_type_map(method),
            **local_variable_type_map(method_body),
        }
        for match in call_re.finditer(method_body):
            target = match.group("target")
            target_method = match.group("method")
            if target in ignored_static_targets or target in ignored_instance_targets:
                continue
            target_type = type_map.get(target, target if target[:1].isupper() else None)
            if not target_type:
                continue
            if is_primitive_type(target_type) or is_dto_like_type(target_type):
                continue
            calls.append(
                {
                    "source_method": method.get("name", "unknown"),
                    "target": target,
                    "target_type": target_type,
                    "method": target_method,
                    "line": line_number_at(candidate.text, candidate.body_start_index + method.get("relative_index", 0) + match.start()),
                    "confidence_basis": "method_scoped_call_extraction",
                }
            )
    return unique_dicts(calls, ["source_method", "target", "target_type", "method", "line"])


def find_mediatr_send_calls(
    candidate: ClassCandidate,
    field_map: dict[str, str],
    method_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sends: list[dict[str, Any]] = []
    send_re = re.compile(
        r"\b(?P<target>_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\.Send\s*"
        r"\(\s*(?:new\s+)?(?P<request>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    )
    for method in method_details:
        method_body = extract_method_body(candidate, method.get("relative_index", 0))
        if not method_body:
            continue
        type_map = {**field_map, **method_parameter_type_map(method)}
        for match in send_re.finditer(method_body):
            target = match.group("target")
            target_type = type_map.get(target)
            if target_type and simple_type_name(target_type) != "IMediator":
                continue
            sends.append(
                {
                    "source_method": method.get("name", "unknown"),
                    "target": target,
                    "target_type": target_type or "IMediator",
                    "request_type": match.group("request"),
                    "line": line_number_at(candidate.text, candidate.body_start_index + method.get("relative_index", 0) + match.start()),
                    "confidence_basis": "mediatr_send_request_extraction",
                }
            )
    return unique_dicts(sends, ["source_method", "target", "request_type", "line"])


def confidence_breakdown(
    parser: str,
    type_confidence: float,
    module_confidence: float,
    evidence_signals: list[str],
    uncertainty: list[str],
) -> dict[str, Any]:
    penalty = min(0.18, len(uncertainty) * 0.04)
    composite = max(0.0, min(1.0, (type_confidence * 0.62) + (module_confidence * 0.28) + (min(len(evidence_signals), 4) * 0.025) - penalty))
    return {
        "parser": parser,
        "type_confidence": round(type_confidence, 3),
        "module_confidence": round(module_confidence, 3),
        "evidence_signal_count": len(evidence_signals),
        "uncertainty_count": len(uncertainty),
        "uncertainty_penalty": round(penalty, 3),
        "composite_confidence": round(composite, 3),
    }


def find_api_calls(text: str, rel_path: str, component_name: str | None, project: ProjectContext | None) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    service_re = re.compile(
        r"\b(?P<target>_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\."
        r"Http(?P<method>Get|Post|Put|Delete)(?:<[^>]+>)?\s*\(\s*(?P<arg>[^,\)\n]+)"
    )
    client_re = re.compile(
        r"\b(?P<target>_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\."
        r"(?P<method>GetAsync|PostAsync|PutAsync|DeleteAsync|PatchAsync)\s*\(\s*(?P<arg>[^,\)\n]+)"
    )
    for match in service_re.finditer(text):
        arg = match.group("arg").strip()
        path = first_string_literal(arg) or arg
        calls.append(
            {
                "kind": "frontend_api_call" if project and project.category == "frontend" else "api_call",
                "http_method": HTTP_METHOD_BY_MAP.get(match.group("method"), "unknown"),
                "path_or_expression": path,
                "target": match.group("target"),
                "source_component": component_name,
                "source_file": rel_path,
                "line": line_number_at(text, match.start()),
                "confidence": 0.78 if first_string_literal(arg) else 0.55,
            }
        )
    for match in client_re.finditer(text):
        arg = match.group("arg").strip()
        path = first_string_literal(arg) or arg
        method = match.group("method").replace("Async", "").upper()
        calls.append(
            {
                "kind": "frontend_api_call" if project and project.category == "frontend" else "http_client_call",
                "http_method": method,
                "path_or_expression": path,
                "target": match.group("target"),
                "source_component": component_name,
                "source_file": rel_path,
                "line": line_number_at(text, match.start()),
                "confidence": 0.75 if first_string_literal(arg) else 0.5,
            }
        )
    return unique_dicts(calls, ["kind", "http_method", "path_or_expression", "source_file", "line"])


def first_string_literal(value: str) -> str | None:
    match = re.search(r'\$?@"([^"]+)"|\$?"([^"]+)"', value)
    if not match:
        return None
    return match.group(1) or match.group(2)


def classify_component(candidate: ClassCandidate, dependencies: list[dict[str, Any]]) -> tuple[str, str, float, list[str], list[str]]:
    path = candidate.file
    lower_path = path.lower()
    name = candidate.name
    lower_name = name.lower()
    bases = " ".join(candidate.bases)
    annotations = " ".join(candidate.annotations)
    dep_types = " ".join(dep["type"] for dep in dependencies)
    evidence: list[str] = []
    uncertainty: list[str] = []

    component_type = "Unknown"
    layer = "Unknown"
    confidence = 0.5

    if path.endswith("/Program.cs") or lower_name in {"dependencies", "servicesconfiguration"}:
        component_type = "Configuration"
        layer = "CrossCutting"
        confidence = 0.78
        evidence.append("bootstrap or service configuration file")
    elif lower_path.startswith("tests/"):
        component_type = "Unknown"
        layer = "CrossCutting"
        confidence = 0.62
        evidence.append("test project source artifact")
        uncertainty.append("Test source component retained as verification evidence, not a production application component")
    elif lower_name.endswith("settings") or lower_name.endswith("options") or lower_name.endswith("constants") or "/constants/" in lower_path:
        component_type = "Configuration"
        layer = "CrossCutting" if "/applicationcore/" in lower_path or "/web/" in lower_path else "Presentation/UI" if candidate.project_category == "frontend" else "Application"
        confidence = 0.76
        evidence.append("settings/constants/options naming or folder pattern")
    elif lower_name.endswith("exception"):
        component_type = "Unknown"
        layer = "CrossCutting"
        confidence = 0.66
        evidence.append("exception class naming pattern")
        uncertainty.append("Exception type has no exact requested component category; layer classified as CrossCutting")
    elif lower_name.endswith("specification") or lower_name.endswith("spec") or "/specifications/" in lower_path:
        component_type = "Repository"
        layer = "DataAccess"
        confidence = 0.74
        evidence.append("Specification pattern query object used by repositories")
        uncertainty.append("Specification classified as Repository-adjacent DataAccess because requested type list has no Specification category")
    elif lower_name.endswith("seed"):
        component_type = "BatchJob"
        layer = "DataAccess"
        confidence = 0.72
        evidence.append("database seed class naming pattern")
        uncertainty.append("Seed class classified as BatchJob-style data initialization support")
    elif lower_name.endswith("healthcheck"):
        component_type = "Service"
        layer = "CrossCutting"
        confidence = 0.74
        evidence.append("ASP.NET health check component naming pattern")
    elif lower_name.endswith("schemafilters") or lower_name.endswith("filter") or "ISchemaFilter" in bases:
        component_type = "Configuration"
        layer = "API"
        confidence = 0.72
        evidence.append("API/schema/filter configuration naming or interface pattern")
    elif lower_name.endswith("hostingstartup"):
        component_type = "Configuration"
        layer = "CrossCutting"
        confidence = 0.74
        evidence.append("ASP.NET hosting startup naming pattern")
    elif lower_name.endswith("helper") or lower_name.endswith("helpers") or "/helpers/" in lower_path or "/extensions/" in lower_path:
        component_type = "Service"
        layer = "CrossCutting" if not candidate.project_category == "frontend" else "Presentation/UI"
        confidence = 0.68
        evidence.append("helper/extension support utility naming or folder pattern")
        uncertainty.append("Helper/extension classified as Service-style support component because requested type list has no Helper category")
    elif candidate.kind.startswith("interface") and lower_name.startswith("i"):
        if "repository" in lower_name:
            component_type = "Repository"
            layer = "DataAccess"
            confidence = 0.84
            evidence.append("repository interface naming pattern")
        elif "sender" in lower_name or "client" in lower_name or "gateway" in lower_name:
            component_type = "ExternalClient"
            layer = "Integration"
            confidence = 0.76
            evidence.append("integration interface naming pattern")
        elif "aggregateroot" in lower_name or "entity" in lower_name:
            component_type = "Entity"
            layer = "Domain"
            confidence = 0.78
            evidence.append("domain marker interface naming pattern")
        else:
            component_type = "Service"
            layer = "Application" if "/applicationcore/" in lower_path else "CrossCutting"
            confidence = 0.7
            evidence.append("interface classified as service contract by naming/path")
            uncertainty.append("Generic interface classified as Service contract because no narrower category was detected")
    elif candidate.file.endswith(".razor.cs") or "BlazorComponent" in bases or "InputSelect" in bases or "ViewComponent" in bases:
        component_type = "FrontendComponent"
        layer = "Presentation/UI"
        confidence = 0.82
        evidence.append("Razor/Blazor/MVC view component code-behind or base class")
    elif "IdentityUser" in bases:
        component_type = "Entity"
        layer = "Infrastructure"
        confidence = 0.8
        evidence.append("ASP.NET Identity user entity base class")
    elif "IOutboundParameterTransformer" in bases or lower_name.endswith("transformer"):
        component_type = "Configuration"
        layer = "Presentation/UI"
        confidence = 0.74
        evidence.append("ASP.NET route parameter transformer")
    elif "/views/" in lower_path and (lower_name.endswith("navpages") or "nav" in lower_name):
        component_type = "FrontendComponent"
        layer = "Presentation/UI"
        confidence = 0.7
        evidence.append("MVC view navigation helper under Views folder")
        uncertainty.append("Static MVC view helper classified as FrontendComponent because requested type list has no ViewHelper category")
    elif lower_name.endswith("attribute"):
        component_type = "Configuration"
        layer = "CrossCutting"
        confidence = 0.72
        evidence.append("custom attribute metadata class")
    elif "/authorization/" in lower_path and lower_name in {"roles", "constants"}:
        component_type = "Configuration"
        layer = "CrossCutting"
        confidence = 0.74
        evidence.append("authorization constants/configuration artifact")
    elif "/authorization/" in lower_path or lower_name in {"claimvalue", "userinfo"}:
        component_type = "DTO"
        layer = "Application"
        confidence = 0.76
        evidence.append("authorization data transfer object")
    elif "IAppLogger" in bases or lower_name.endswith("adapter"):
        component_type = "Service"
        layer = "CrossCutting"
        confidence = 0.76
        evidence.append("adapter/service contract implementation")
    elif "IRequest" in bases:
        component_type = "Handler"
        layer = "Application"
        confidence = 0.74
        evidence.append("MediatR request/query message")
        uncertainty.append("MediatR request object classified as Handler-style application component because requested type list has no Command/Query category")
    elif "/data/" in lower_path and lower_name.endswith("item"):
        component_type = "DTO"
        layer = "Infrastructure"
        confidence = 0.7
        evidence.append("data/infrastructure transfer object naming and path")
    if "controller" in lower_name or "Controller" in bases or "ApiController" in annotations:
        component_type = "Controller"
        layer = "API"
        confidence = 0.9
        evidence.append("controller name/base class/API controller attribute")
    elif lower_name.endswith("endpoint") or "IEndpoint" in bases or "EndpointBaseAsync" in bases:
        component_type = "Controller"
        layer = "API"
        confidence = 0.86
        evidence.append("endpoint class implementing ASP.NET endpoint abstraction")
        uncertainty.append("endpoint-style HTTP component classified as Controller because requested type list has no Endpoint category")
    elif "pagemodel" in bases.lower() or lower_name.endswith("model") and "/pages/" in lower_path:
        component_type = "Controller"
        layer = "Presentation/UI"
        confidence = 0.8
        evidence.append("Razor PageModel class")
        uncertainty.append("Razor PageModel classified as Controller-like presentation component")
    elif lower_name.endswith("middleware") or "/middleware/" in lower_path:
        component_type = "Middleware"
        layer = "CrossCutting"
        confidence = 0.88
        evidence.append("middleware name/path")
    elif lower_name.endswith("handler") or "IRequestHandler" in bases:
        component_type = "Handler"
        layer = "Application"
        confidence = 0.86
        evidence.append("handler name or MediatR IRequestHandler implementation")
    elif lower_name.endswith("repository") or "RepositoryBase" in bases or "IRepository" in bases:
        component_type = "Repository"
        layer = "DataAccess"
        confidence = 0.9
        evidence.append("repository name/base/interface")
    elif "DbContext" in bases or lower_name.endswith("dbcontext"):
        component_type = "Repository"
        layer = "DataAccess"
        confidence = 0.82
        evidence.append("database context class")
        uncertainty.append("DbContext captured under Repository because requested type list has no DatabaseContext category")
    elif "IEntityTypeConfiguration" in bases or lower_name.endswith("configuration") or "/configuration/" in lower_path or "/config/" in lower_path:
        component_type = "Configuration"
        layer = "Infrastructure" if "/infrastructure/" in lower_path else "CrossCutting"
        confidence = 0.84
        evidence.append("configuration name/path/interface")
    elif lower_name.endswith("profile") or "Profile" in bases:
        component_type = "Mapper"
        layer = "Application"
        confidence = 0.82
        evidence.append("mapping profile")
    elif lower_name.endswith("validator") or "validator" in lower_name or "validation" in lower_path:
        component_type = "Validator"
        layer = "Application"
        confidence = 0.76
        evidence.append("validator name/path")
    elif lower_name.endswith("service") or "/services/" in lower_path:
        if candidate.project_category == "frontend":
            component_type = "FrontendService"
            layer = "Presentation/UI"
            confidence = 0.82
            evidence.append("service class in frontend project")
        elif "HttpClient" in dep_types or lower_name.endswith("client"):
            component_type = "ExternalClient"
            layer = "Integration"
            confidence = 0.78
            evidence.append("service/client uses HttpClient")
        else:
            component_type = "Service"
            layer = "Application"
            confidence = 0.84
            evidence.append("service name/path")
    elif lower_name.endswith("client") or "HttpClient" in dep_types:
        component_type = "ExternalClient"
        layer = "Integration"
        confidence = 0.75
        evidence.append("client name or HttpClient dependency")
    elif lower_name.endswith("gateway"):
        component_type = "Gateway"
        layer = "Integration"
        confidence = 0.78
        evidence.append("gateway name")
    elif lower_name.endswith("stateprovider") or "AuthenticationStateProvider" in bases:
        component_type = "StateStore"
        layer = "Presentation/UI"
        confidence = 0.76
        evidence.append("state provider base/name")
    elif "ComponentBase" in bases or "LayoutComponentBase" in bases or "/helpers/blazor" in lower_path:
        component_type = "FrontendComponent"
        layer = "Presentation/UI"
        confidence = 0.78
        evidence.append("Blazor component base class")
    elif "/entities/" in lower_path or "IAggregateRoot" in bases or "BaseEntity" in bases:
        component_type = "Entity"
        layer = "Domain"
        confidence = 0.88
        evidence.append("entity path/base/interface")
    elif any(token in lower_name for token in ["dto", "request", "response", "viewmodel", "message"]) or any(
        token in lower_path for token in ["/viewmodels/", "/models/"]
    ):
        component_type = "DTO"
        layer = "Presentation/UI" if candidate.project_category == "frontend" or "/ui/" in lower_path or "/web/" in lower_path else "Application"
        confidence = 0.78
        evidence.append("DTO/request/response/view-model name or path")
    elif lower_name.endswith("job"):
        component_type = "ScheduledJob"
        layer = "Application"
        confidence = 0.7
        evidence.append("job name")
    elif "BackgroundService" in bases or "IHostedService" in bases:
        component_type = "ScheduledJob"
        layer = "Application"
        confidence = 0.8
        evidence.append("hosted/background service base")
    elif lower_name.endswith("consumer") or lower_name.endswith("listener"):
        component_type = "MessageConsumer"
        layer = "Integration"
        confidence = 0.78
        evidence.append("consumer/listener name")
    elif lower_name.endswith("batch") or lower_name.endswith("migration"):
        component_type = "BatchJob"
        layer = "DataAccess"
        confidence = 0.68
        evidence.append("batch/migration name")

    if component_type == "Unknown":
        uncertainty.append("No strong component classification signal from name, path, attributes, base types, or dependencies")

    if component_type not in COMPONENT_TYPES:
        component_type = "Unknown"
        uncertainty.append("Classification fell outside requested component type set")
    if layer not in LAYERS:
        layer = "Unknown"
        uncertainty.append("Layer fell outside requested layer set")

    return component_type, layer, confidence, evidence, uncertainty


def architecture_significance_for_component(candidate: ClassCandidate, component_type: str, layer: str) -> dict[str, Any]:
    lower_path = candidate.file.lower()
    lower_name = candidate.name.lower()
    if lower_path.startswith("tests/"):
        return {
            "architecture_significance": "VerificationOnly",
            "is_major_application_component": False,
            "architecture_significance_reason": "test source artifact used for regression/runtime evidence, not production architecture ownership",
        }
    if component_type in {"Controller", "Service", "Repository", "ExternalClient", "Gateway", "Middleware", "Handler", "ScheduledJob", "MessageConsumer", "BatchJob"}:
        return {
            "architecture_significance": "Major",
            "is_major_application_component": True,
            "architecture_significance_reason": "component type participates directly in entry points, orchestration, data access, integration, or background work",
        }
    if component_type in {"Entity", "DTO", "Mapper", "Validator", "Configuration", "FrontendComponent", "FrontendService", "RouteGuard", "StateStore"}:
        return {
            "architecture_significance": "Supporting",
            "is_major_application_component": True,
            "architecture_significance_reason": "component supports application architecture and ownership decisions",
        }
    if any(token in lower_name for token in ["exception", "constant", "helper", "extension"]) or any(
        token in lower_path for token in ["/constants/", "/helpers/", "/extensions/", "/javascript/"]
    ):
        return {
            "architecture_significance": "SupportOnly",
            "is_major_application_component": False,
            "architecture_significance_reason": "support utility/constant/exception artifact has limited standalone architecture ownership",
        }
    return {
        "architecture_significance": "UnclassifiedCandidate",
        "is_major_application_component": True,
        "architecture_significance_reason": "component remains potentially architecture-significant until reviewed",
    }


GENERIC_MODULE_NAME_SUFFIX_RE = re.compile(
    r"(Controller|Endpoint|Service|Repository|Handler|Dto|DTO|Request|Response|ViewModel|Model|Configuration|Config|Middleware|Validator|Page|Component|Test|Tests)$"
)

GENERIC_MODULE_FOLDER_TOKENS = {
    "src",
    "source",
    "test",
    "tests",
    "pages",
    "page",
    "controllers",
    "controller",
    "endpoints",
    "endpoint",
    "services",
    "service",
    "repositories",
    "repository",
    "models",
    "model",
    "viewmodels",
    "views",
    "components",
    "component",
    "features",
    "helpers",
    "configuration",
    "config",
    "middleware",
    "data",
    "entities",
    "entity",
    "interfaces",
    "shared",
    "common",
    "core",
    "application",
    "domain",
    "infrastructure",
    "web",
    "api",
    "client",
    "server",
    "wwwroot",
    "properties",
}

SEMANTIC_MODULE_RULES = [
    (
        "Catalog",
        {
            "catalog",
            "catalogaggregate",
            "catalogbrand",
            "catalogbrands",
            "catalogitem",
            "catalogitems",
            "catalogtype",
            "catalogtypes",
            "product",
            "products",
        },
    ),
    (
        "Basket",
        {
            "basket",
            "basketaggregate",
            "basketitem",
            "basketitems",
            "checkout",
            "cart",
        },
    ),
    (
        "Order",
        {
            "order",
            "orders",
            "orderaggregate",
            "orderitem",
            "orderitems",
            "buyer",
            "buyeraggregate",
            "payment",
            "paymentmethod",
            "address",
        },
    ),
    (
        "Identity",
        {
            "identity",
            "auth",
            "authenticate",
            "authorization",
            "account",
            "login",
            "logout",
            "register",
            "manage",
            "user",
            "token",
            "claims",
        },
    ),
    (
        "Admin",
        {
            "admin",
            "blazoradmin",
        },
    ),
    (
        "SharedContracts",
        {
            "shared",
            "blazorshared",
            "contract",
            "contracts",
        },
    ),
]


def split_identifier_tokens(value: str) -> list[str]:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value or "")
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return [word.lower() for word in words.split() if word]


def source_project_root(path: str) -> str | None:
    parts = list(PurePosixPath(path).parts)
    if len(parts) >= 2 and parts[0] in {"src", "tests"}:
        return parts[1]
    return None


def semantic_module_from_evidence(path: str, name: str, namespace: str | None, component_type: str) -> tuple[str, float, str] | None:
    normalized_path = path.replace("\\", "/")
    lower_path = normalized_path.lower()
    if lower_path.startswith("tests/"):
        return "Verification", 0.9, "test source is separated as verification evidence, not a production module"

    tokens = set(split_identifier_tokens(name))
    tokens.update(split_identifier_tokens(namespace or ""))
    for part in PurePosixPath(normalized_path).parts:
        tokens.update(split_identifier_tokens(part))

    joined = " ".join(sorted(tokens))
    for module, rule_tokens in SEMANTIC_MODULE_RULES:
        if tokens & rule_tokens:
            return module, 0.88, f"semantic module token match: {module} from {sorted(tokens & rule_tokens)}"

    if "infrastructure" in lower_path:
        if any(token in tokens for token in {"data", "dbcontext", "repository", "context", "migration", "migrations", "seed"}):
            return "DataAccess", 0.84, "infrastructure data/repository/context evidence"
        return "Infrastructure", 0.78, "infrastructure project/folder evidence"

    if component_type in {"Configuration", "Middleware"}:
        return "CrossCutting", 0.72, "cross-cutting component type"

    project_root = source_project_root(normalized_path)
    if project_root in {"PublicApi", "Web"}:
        return project_root, 0.68, "project-level host module used because no stronger domain token was detected"
    if project_root == "ApplicationCore":
        return "ApplicationCore", 0.68, "application-core project evidence with no narrower domain token"
    if project_root == "BlazorShared":
        return "SharedContracts", 0.76, "shared frontend/backend contract project evidence"
    if project_root == "BlazorAdmin":
        return "Admin", 0.76, "BlazorAdmin project evidence"

    return None


def clean_module_candidate(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = GENERIC_MODULE_NAME_SUFFIX_RE.sub("", value).strip("_-. ")
    cleaned = re.sub(
        r"^(Get|List|Create|Update|Delete|Remove|Add|Edit|Set|Read|Write|Post|Put|Patch|Search|Find)(By|For|With)?(?=[A-Z])",
        "",
        cleaned,
    )
    cleaned = cleaned.strip("_-. ")
    if not cleaned:
        return None
    if cleaned.lower() in GENERIC_MODULE_FOLDER_TOKENS:
        return None
    if len(cleaned) < 3:
        return None
    return cleaned[0].upper() + cleaned[1:]


def module_guess_for_path_name(path: str, name: str, namespace: str | None, component_type: str) -> tuple[str, float, str]:
    parts = [part for part in PurePosixPath(path).parts if part]
    lower_parts = [part.lower() for part in parts]
    semantic = semantic_module_from_evidence(path, name, namespace, component_type)
    if semantic:
        return semantic
    name_without_suffix = clean_module_candidate(name)

    if name_without_suffix:
        return name_without_suffix, 0.72, "component name provides candidate module term after generic suffix removal"
    for part in reversed(parts[:-1]):
        clean = clean_module_candidate(part)
        if clean:
            return clean, 0.7, "source path folder provides candidate module term after generic token filtering"
    if namespace:
        ns_parts = namespace.split(".")
        for ns_part in reversed(ns_parts):
            clean = clean_module_candidate(ns_part)
            if clean:
                return clean, 0.66, "namespace segment provides candidate module term after generic token filtering"
    if component_type in {"Configuration", "Middleware"}:
        return "CrossCutting", 0.55, "cross-cutting component type"
    if "infrastructure" in lower_parts:
        return "Infrastructure", 0.52, "infrastructure path"
    return "Unknown", 0.3, "no module signal detected"


def unique_dicts(values: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for value in values:
        marker = tuple(value.get(key) for key in keys)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def extract_razor_directives(text: str) -> dict[str, Any]:
    pages = []
    injects = []
    inherits = []
    attributes = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip().lstrip("\ufeff")
        page_match = re.match(r'@page(?:\s+(?P<route>".*?"|\S+))?', stripped)
        if page_match:
            route = page_match.group("route")
            route = route.strip('"') if route else None
            pages.append({"route": route, "line": line_number})
        inject_match = re.match(r"@inject\s+(?P<type>[A-Za-z_][A-Za-z0-9_.<>]*)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)", stripped)
        if inject_match:
            injects.append({"type": inject_match.group("type"), "name": inject_match.group("name"), "line": line_number})
        inherit_match = re.match(r"@inherits\s+(?P<type>.+)", stripped)
        if inherit_match:
            inherits.append({"type": inherit_match.group("type").strip(), "line": line_number})
        attr_match = re.match(r"@attribute\s+(?P<attr>.+)", stripped)
        if attr_match:
            attributes.append({"attribute": attr_match.group("attr").strip(), "line": line_number})
    return {"pages": pages, "injects": injects, "inherits": inherits, "attributes": attributes}


def razor_route_from_file(path: str, route: str | None) -> str:
    if route:
        return route if route.startswith("/") else "/" + route
    pure = PurePosixPath(path)
    parts = list(pure.parts)
    if "Pages" in parts:
        idx = parts.index("Pages")
        route_parts = parts[idx + 1 :]
        if route_parts:
            route_parts[-1] = PurePosixPath(route_parts[-1]).stem
            if route_parts[-1] == "Index":
                route_parts = route_parts[:-1]
            route_path = "/" + "/".join(route_parts)
            return route_path if route_path != "/" else "/"
    return "/" + pure.stem


def parse_razor_component(file_path: Path, rel_path: str, project: ProjectContext | None) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    directives = extract_razor_directives(text)
    name = PurePosixPath(rel_path).stem
    if name in {"_ViewImports", "_ViewStart"}:
        confidence = 0.55
    else:
        confidence = 0.76
    component_type = "FrontendComponent"
    layer = "Presentation/UI"
    module_guess, module_conf, module_reason = module_guess_for_path_name(rel_path, name, None, component_type)
    dependencies = [
        {
            "type": inject["type"],
            "name": inject["name"],
            "source": "razor_inject",
            "confidence": 0.86,
        }
        for inject in directives["injects"]
    ]
    if directives["inherits"]:
        dependencies.extend(
            {
                "type": item["type"],
                "name": "base_component",
                "source": "razor_inherits",
                "confidence": 0.78,
            }
            for item in directives["inherits"]
        )
    annotations = [item["attribute"] for item in directives["attributes"]]
    component = {
        "component_id": None,
        "name": name,
        "namespace_or_package": None,
        "module_path": rel_path,
        "project": project.name if project else "unknown",
        "project_type": project.type if project else "unknown",
        "language": "razor",
        "component_type": component_type,
        "type": component_type,
        "layer_guess": layer,
        "layer": layer,
        "module_guess": module_guess,
        "module_guess_confidence": module_conf,
        "module_guess_evidence": module_reason,
        "file": rel_path,
        "start_line": 1,
        "end_line": len(text.splitlines()),
        "public_methods": [],
        "method_details": [],
        "dependencies": dependencies,
        "imports": [],
        "annotations": annotations,
        "base_class": directives["inherits"][0]["type"] if directives["inherits"] else None,
        "implemented_interfaces": [],
        "confidence": confidence,
        "evidence": [
            {
                "file": rel_path,
                "line": 1,
                "reason": "Razor/Blazor component file detected from Step 1 inventory",
            }
        ],
        "uncertainty": [],
    }

    routes: list[dict[str, Any]] = []
    for page in directives["pages"]:
        route_type = "FrontendRoute" if rel_path.endswith(".razor") else "HTTP_API"
        routes.append(
            {
                "route_id": None,
                "type": route_type,
                "method": "GET" if route_type == "HTTP_API" else "unknown",
                "path": razor_route_from_file(rel_path, page["route"]),
                "component": name,
                "action": "@page",
                "file": rel_path,
                "line": page["line"],
                "owning_module_guess": module_guess,
                "called_services": [dep["type"] for dep in dependencies],
                "confidence": 0.84 if page["route"] else 0.72,
                "evidence": [
                    {
                        "file": rel_path,
                        "line": page["line"],
                        "reason": "Razor @page directive",
                    }
                ],
                "uncertainty": [] if page["route"] else ["Route path inferred from Razor Pages file location"],
            }
        )

    api_calls = find_api_calls(text, rel_path, name, project)
    return component, routes, api_calls


def extract_route_attributes(attributes: list[str]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    joined = " ".join(attributes)
    for match in re.finditer(r"\bHttp(Get|Post|Put|Patch|Delete)(?:Attribute)?\s*(?:\((?P<args>[^)]*)\))?", joined):
        args = match.group("args") or ""
        routes.append(
            {
                "method": HTTP_METHOD_BY_MAP[match.group(1)],
                "path": first_string_literal(args),
                "attribute": match.group(0),
            }
        )
    for match in re.finditer(r"\bRoute(?:Attribute)?\s*\((?P<args>[^)]*)\)", joined):
        routes.append(
            {
                "method": "unknown",
                "path": first_string_literal(match.group("args")),
                "attribute": match.group(0),
            }
        )
    return routes


def extract_area_attribute(attributes: list[str]) -> str | None:
    joined = " ".join(attributes)
    match = re.search(r"\bArea(?:Attribute)?\s*\((?P<args>[^)]*)\)", joined)
    if not match:
        return None
    return first_string_literal(match.group("args"))


def combine_route_paths(class_route: str | None, method_route: str | None, class_name: str, action: str, area: str | None = None) -> str:
    class_part = class_route or ""
    method_part = method_route or ""
    combined = "/".join(part.strip("/") for part in [area, class_part, method_part] if part and part.strip("/") != "")
    if not combined:
        combined = f"{class_name.removesuffix('Controller')}/{action}"
    combined = combined.replace("[controller]", class_name.removesuffix("Controller"))
    combined = combined.replace("[area]", area or "")
    combined = combined.replace("[action]", action)
    combined = re.sub(r"\{(?P<name>[A-Za-z_][A-Za-z0-9_]*):[^}]+\}", r"{\g<name>}", combined)
    combined = re.sub(r"/+", "/", combined)
    return "/" + combined.strip("/")


def method_attribute_blocks(candidate: ClassCandidate) -> list[dict[str, Any]]:
    text = candidate.text
    lines = text.splitlines()
    methods = method_matches(candidate.body, candidate.name, candidate.kind)
    results: list[dict[str, Any]] = []
    starts = line_start_indices(text)
    for method in methods:
        abs_index = candidate.body_start_index + method["relative_index"]
        start_line = line_number_at(text, abs_index)
        attrs = previous_attribute_lines(lines, start_line)
        method_body = extract_method_body(candidate, method["relative_index"])
        results.append({**method, "line": start_line, "annotations": attrs, "body": method_body})
    return results


def csharp_routes_for_candidate(candidate: ClassCandidate, module_guess: str, field_map: dict[str, str]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    class_routes = [route for route in extract_route_attributes(candidate.annotations) if route["path"]]
    class_route_path = class_routes[0]["path"] if class_routes else None
    area = extract_area_attribute(candidate.annotations)

    for method in method_attribute_blocks(candidate):
        method_routes = extract_route_attributes(method["annotations"])
        http_routes = [route for route in method_routes if route["method"] != "unknown"]
        route_only = [route for route in method_routes if route["method"] == "unknown" and route["path"]]
        if not http_routes:
            continue
        for http_route in http_routes:
            effective_method_path = http_route["path"] or (route_only[0]["path"] if route_only else None)
            called_services = called_services_from_body(method["body"], field_map)
            routes.append(
                {
                    "route_id": None,
                    "type": "HTTP_API",
                    "method": http_route["method"],
                    "path": combine_route_paths(class_route_path, effective_method_path, candidate.name, method["name"], area),
                    "component": candidate.name,
                    "action": method["name"],
                    "file": candidate.file,
                    "line": method["line"],
                    "owning_module_guess": module_guess,
                    "called_services": called_services,
                    "confidence": 0.9 if class_route_path or effective_method_path else 0.82,
                    "evidence": [
                        {
                            "file": candidate.file,
                            "line": method["line"],
                            "reason": "ASP.NET HTTP method attribute",
                        }
                    ],
                    "uncertainty": [] if class_route_path or effective_method_path else ["Route path inferred from controller/action convention."],
                    "parser_strategy": "aspnet_attribute_route_parser",
                }
            )
    return routes


def minimal_api_routes_for_candidate(
    candidate: ClassCandidate,
    module_guess: str,
    field_map: dict[str, str],
    method_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    group_prefixes: dict[str, str] = {"app": ""}
    group_re = re.compile(
        r"\b(?:var\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<parent>app|[A-Za-z_][A-Za-z0-9_]*)\.MapGroup\s*\(\s*(?P<path>\$?@?\"[^\"]+\")"
    )
    for match in group_re.finditer(candidate.body):
        parent = match.group("parent")
        parent_prefix = group_prefixes.get(parent, "")
        path = first_string_literal(match.group("path")) or ""
        group_prefixes[match.group("name")] = "/" + "/".join(part.strip("/") for part in [parent_prefix, path] if part and part.strip("/"))

    map_re = re.compile(r"\b(?P<target>app|[A-Za-z_][A-Za-z0-9_]*)\.Map(?P<verb>Get|Post|Put|Patch|Delete)\s*\(\s*(?P<path>\$?@?\"[^\"]+\")")
    handler_method = next((method for method in method_details if method.get("name") == "HandleAsync"), None)
    handler_calls = called_services_from_body(
        extract_method_body(candidate, handler_method.get("relative_index", 0)) if handler_method else "",
        {**field_map, **method_parameter_type_map(handler_method or {})},
    )
    for match in map_re.finditer(candidate.body):
        path = first_string_literal(match.group("path")) or "unknown"
        prefix = group_prefixes.get(match.group("target"), "")
        combined_path = "/" + "/".join(part.strip("/") for part in [prefix, path] if part and part.strip("/"))
        routes.append(
            {
                "route_id": None,
                "type": "HTTP_API",
                "method": HTTP_METHOD_BY_MAP[match.group("verb")],
                "path": combined_path or "/" + path.strip("/"),
                "component": candidate.name,
                "action": "HandleAsync" if handler_method else "AddRoute" if "AddRoute" in candidate.body[: match.start()] else "unknown",
                "file": candidate.file,
                "line": line_number_at(candidate.text, candidate.body_start_index + match.start()),
                "owning_module_guess": module_guess,
                "called_services": handler_calls,
                "confidence": 0.92 if match.group("target") != "app" else 0.9,
                "evidence": [
                    {
                        "file": candidate.file,
                        "line": line_number_at(candidate.text, candidate.body_start_index + match.start()),
                        "reason": "ASP.NET Minimal API Map* call" + (" with MapGroup prefix" if match.group("target") != "app" else ""),
                    }
                ],
                "uncertainty": [],
                "parser_strategy": "aspnet_minimal_api_parser",
            }
        )
    return routes


def program_routes_for_candidate(candidate: ClassCandidate, module_guess: str) -> list[dict[str, Any]]:
    if not candidate.file.endswith("/Program.cs"):
        return []
    text = candidate.body
    routes: list[dict[str, Any]] = []
    patterns = [
        (r"\bapp\.MapControllerRoute\s*\(\s*\"(?P<name>[^\"]+)\"\s*,\s*\"(?P<path>[^\"]+)\"", "HTTP_API", "unknown", "ASP.NET conventional MVC route"),
        (r"\bapp\.MapRazorPages\s*\(", "HTTP_API", "unknown", "ASP.NET Razor Pages route registration"),
        (r"\bapp\.MapControllers\s*\(", "HTTP_API", "unknown", "ASP.NET controller route registration"),
        (r"\bapp\.MapEndpoints\s*\(", "HTTP_API", "unknown", "MinimalApi.Endpoint route registration"),
        (r"\bapp\.MapFallbackToFile\s*\(\s*\"(?P<path>[^\"]+)\"", "FrontendRoute", "unknown", "SPA fallback route"),
        (r"\bapp\.MapHealthChecks\s*\(\s*\"(?P<path>[^\"]+)\"", "HTTP_API", "GET", "ASP.NET health check route"),
    ]
    for pattern, route_type, method, reason in patterns:
        for match in re.finditer(pattern, text):
            path = match.groupdict().get("path") or match.groupdict().get("name") or reason
            if path.startswith("{"):
                normalized = "/" + path
            elif path.startswith("/"):
                normalized = path
            elif path in {"ASP.NET Razor Pages route registration", "ASP.NET controller route registration", "MinimalApi.Endpoint route registration"}:
                normalized = path
            else:
                normalized = "/" + path.strip("/")
            routes.append(
                {
                    "route_id": None,
                    "type": route_type,
                    "method": method,
                    "path": normalized,
                    "component": "Program",
                    "action": reason,
                    "file": candidate.file,
                    "line": line_number_at(candidate.text, match.start()),
                    "owning_module_guess": module_guess,
                    "called_services": [],
                    "confidence": 0.72,
                    "evidence": [
                        {
                            "file": candidate.file,
                            "line": line_number_at(candidate.text, match.start()),
                            "reason": reason,
                        }
                    ],
                    "uncertainty": ["Framework-level route registration; individual endpoints may be in controller/Razor/endpoint files"],
                }
            )
    return routes


def called_services_from_body(body: str, field_map: dict[str, str]) -> list[str]:
    calls: list[str] = []
    call_re = re.compile(r"\b(?P<field>_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for match in call_re.finditer(body):
        field = match.group("field")
        if field in field_map:
            calls.append(f"{field_map[field]}.{match.group('method')}")
    return sorted(set(calls))


def parse_generic_invocations(text: str, method_names: set[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    method_re = re.compile(r"\b(?P<prefix>(?:builder\.)?services|builder\.Services)\.(?P<method>Add[A-Za-z0-9_]+)\s*<")
    for match in method_re.finditer(text):
        method = match.group("method")
        if method not in method_names:
            continue
        generic_start = match.end() - 1
        depth = 0
        end = None
        for idx in range(generic_start, len(text)):
            char = text[idx]
            if char == "<":
                depth += 1
            elif char == ">":
                depth -= 1
                if depth == 0:
                    end = idx
                    break
        if end is None:
            continue
        args = split_top_level_commas(text[generic_start + 1 : end])
        results.append(
            {
                "method": method,
                "args": [clean_type_name(arg) for arg in args],
                "line": line_number_at(text, match.start()),
            }
        )
    return results


def extract_di_registrations(text: str, rel_path: str) -> list[dict[str, Any]]:
    registrations: list[dict[str, Any]] = []
    generic_methods = {"AddScoped", "AddTransient", "AddSingleton", "AddDbContext", "AddHostedService"}
    for invocation in parse_generic_invocations(text, generic_methods):
        method = invocation["method"]
        args = invocation["args"]
        service = args[0] if args else "unknown"
        implementation = args[1] if len(args) > 1 else args[0] if args else "unknown"
        registrations.append(
            {
                "kind": "db_context_registration" if method == "AddDbContext" else "di_registration",
                "lifetime": method.replace("Add", ""),
                "service": service,
                "implementation": implementation,
                "source_file": rel_path,
                "line": invocation["line"],
                "confidence": 0.86,
            }
        )

    typeof_re = re.compile(
        r"\bservices\.Add(?P<lifetime>Scoped|Transient|Singleton)\s*\(\s*typeof\((?P<service>[^)]+)\)\s*,\s*typeof\((?P<impl>[^)]+)\)"
    )
    for match in typeof_re.finditer(text):
        registrations.append(
            {
                "kind": "di_registration",
                "lifetime": match.group("lifetime"),
                "service": clean_type_name(match.group("service")),
                "implementation": clean_type_name(match.group("impl")),
                "source_file": rel_path,
                "line": line_number_at(text, match.start()),
                "confidence": 0.88,
            }
        )
    return unique_dicts(registrations, ["kind", "service", "implementation", "source_file", "line"])


def project_for_file(path: str, projects: list[ProjectContext]) -> ProjectContext | None:
    normalized = normalize_slashes(path)
    matches = [
        project
        for project in projects
        if normalized == project.source_path or normalized.startswith(project.source_path.rstrip("/") + "/")
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda item: len(item.source_path), reverse=True)[0]


def project_by_csproj_path(project_inventory: dict[str, Any]) -> dict[str, ProjectContext]:
    result = {}
    for item in project_inventory.get("projects", []):
        result[normalize_slashes(item["path"])] = ProjectContext(
            name=item["name"],
            path=normalize_slashes(item["path"]),
            source_path=normalize_slashes(item["source_path"]),
            category=item.get("category", "unknown"),
            type=item.get("type", "unknown"),
            framework=item.get("framework", "unknown"),
            package_references=item.get("package_references", []),
            project_references=[normalize_slashes(ref) for ref in item.get("project_references", [])],
        )
    return result


def resolve_project_reference(project: ProjectContext, reference: str, projects_by_path: dict[str, ProjectContext]) -> ProjectContext | None:
    base = PurePosixPath(project.source_path)
    ref_path = PurePosixPath(normalize_slashes(reference))
    resolved = normalize_pure_posix(base / ref_path)
    return projects_by_path.get(resolved)


def normalize_pure_posix(path: PurePosixPath) -> str:
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def optional_ast_backend_status() -> list[dict[str, Any]]:
    dotnet_path = find_dotnet_executable()
    tree_sitter_available = importlib.util.find_spec("tree_sitter") is not None
    tree_sitter_csharp_available_now = importlib.util.find_spec("tree_sitter_c_sharp") is not None
    return [
        {
            "name": "Roslyn compiler AST",
            "available": bool(dotnet_path),
            "active": False,
            "detected_from": [str(dotnet_path)] if dotnet_path else [],
            "parser_strategy": "available for future C# semantic extraction; not active until a Roslyn semantic extractor is implemented",
            "reason_unavailable": None if dotnet_path else "dotnet executable was not found on PATH",
        },
        {
            "name": "tree-sitter C# AST",
            "available": bool(tree_sitter_available and tree_sitter_csharp_available_now),
            "active": bool(tree_sitter_available and tree_sitter_csharp_available_now),
            "detected_from": ["python package:tree_sitter", "python package:tree_sitter_c_sharp"]
            if tree_sitter_available and tree_sitter_csharp_available_now
            else [],
            "parser_strategy": "C# syntax tree parser for class/interface/record/struct declarations; framework extractors still handle routes, DI, and call candidates",
            "reason_unavailable": None
            if tree_sitter_available and tree_sitter_csharp_available_now
            else "tree_sitter and tree_sitter_c_sharp Python packages are not both installed",
        },
    ]


def find_dotnet_executable() -> str | None:
    existing = shutil.which("dotnet")
    if existing:
        return existing
    candidates = [
        Path.home() / ".dotnet8" / "dotnet.exe",
        Path.home() / ".dotnet" / "dotnet.exe",
        Path("architecture-output") / "dotnet" / "dotnet.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def detected_technology_stacks(project_inventory: dict[str, Any], language_summary: dict[str, Any]) -> list[dict[str, Any]]:
    languages = {item["language"]: item for item in language_summary.get("languages", [])}
    packages = {
        package
        for project in project_inventory.get("projects", [])
        for package in project.get("package_references", [])
    }
    stacks: list[dict[str, Any]] = []
    if "csharp" in languages:
        ast_status = optional_ast_backend_status()
        active_ast = [item["name"] for item in ast_status if item.get("active")]
        stacks.append(
            {
                "name": ".NET / C#",
                "detected_from": ["language-summary:csharp", "project-inventory:*.csproj"],
                "parser_strategy": "compiler/AST-backed parser when available; otherwise C# source structural parser; project XML parsed structurally",
                "ast_backends": ast_status,
                "active_ast_backend": active_ast[0] if active_ast else "static_structural_fallback",
            }
        )
    if any(project.get("type") in {"backend_web_api", "backend_web_app"} for project in project_inventory.get("projects", [])):
        stacks.append(
            {
                "name": "ASP.NET Core",
                "detected_from": ["Microsoft.NET.Sdk.Web", "Program.cs", "controllers/endpoints"],
                "parser_strategy": "ASP.NET route/DI/framework-call extraction",
            }
        )
    if "MinimalApi.Endpoint" in packages:
        stacks.append(
            {
                "name": "MinimalApi.Endpoint",
                "detected_from": ["PackageReference:MinimalApi.Endpoint"],
                "parser_strategy": "IEndpoint/AddRoute and app.Map* extraction",
            }
        )
    if "Ardalis.ApiEndpoints" in packages:
        stacks.append(
            {
                "name": "Ardalis.ApiEndpoints",
                "detected_from": ["PackageReference:Ardalis.ApiEndpoints"],
                "parser_strategy": "EndpointBaseAsync + HTTP attribute extraction",
            }
        )
    if any("EntityFrameworkCore" in package for package in packages):
        stacks.append(
            {
                "name": "Entity Framework Core",
                "detected_from": ["PackageReference:Microsoft.EntityFrameworkCore.*"],
                "parser_strategy": "DbContext, IEntityTypeConfiguration, AddDbContext, repository usage extraction",
            }
        )
    if "razor" in languages:
        stacks.append(
            {
                "name": "Razor / Blazor",
                "detected_from": ["language-summary:razor", "Blazor WebAssembly project"],
                "parser_strategy": "@page/@inject/@inherits directive extraction",
            }
        )
    if "MediatR" in packages:
        stacks.append(
            {
                "name": "MediatR",
                "detected_from": ["PackageReference:MediatR"],
                "parser_strategy": "IRequest/IRequestHandler and IMediator.Send call extraction",
            }
        )
    return stacks


def build_symbol_registry(
    repo_root: Path,
    file_inventory: dict[str, Any],
    project_inventory: dict[str, Any],
    language_summary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    projects_by_path = project_by_csproj_path(project_inventory)
    projects = list(projects_by_path.values())

    components: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    dependency_records: list[dict[str, Any]] = []
    entry_points: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []
    api_call_records: list[dict[str, Any]] = []
    internal_component_state: dict[str, dict[str, Any]] = {}

    relevant_languages = {item["language"] for item in language_summary.get("languages", [])}
    parser_technologies = detected_technology_stacks(project_inventory, language_summary)

    inventory_files = file_inventory.get("files", [])
    csharp_files = [
        record
        for record in inventory_files
        if record.get("language") == "csharp" and record.get("path", "").endswith(".cs")
    ]
    razor_files = [
        record
        for record in inventory_files
        if record.get("language") == "razor" and record.get("extension") in {".razor", ".cshtml"}
    ]

    component_seq = 1
    route_seq = 1

    for record in csharp_files:
        rel_path = normalize_slashes(record["path"])
        generated, reason = is_probably_generated_source(rel_path)
        if generated:
            skipped_files.append({"path": rel_path, "reason": reason or "generated_or_migration_pattern"})
            continue
        file_path = repo_root / rel_path
        project = project_for_file(rel_path, projects)
        try:
            candidates = (
                parse_csharp_classes_tree_sitter(file_path, rel_path, project)
                if tree_sitter_csharp_available()
                else parse_csharp_classes(file_path, rel_path, project)
            )
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped_files.append({"path": rel_path, "reason": f"read_error:{exc.__class__.__name__}"})
            continue

        file_di_registrations = extract_di_registrations(text, rel_path)
        for registration in file_di_registrations:
            dependency_records.append(
                {
                    "dependency_id": None,
                    "kind": registration["kind"],
                    "from": project.name if project else "unknown",
                    "to": registration["implementation"],
                    "relationship": "registers",
                    "source_file": rel_path,
                    "line": registration["line"],
                    "evidence": f"{registration['lifetime']} registration maps {registration['service']} to {registration['implementation']}",
                    "confidence": registration["confidence"],
                    "metadata": registration,
                }
            )

        for candidate in candidates:
            constructor_deps, constructor_param_types = find_constructor_dependencies(candidate)
            property_deps = find_property_injections(candidate)
            all_deps = constructor_deps + property_deps
            field_types = find_field_types(candidate)
            field_map = infer_field_dependency_map(candidate, constructor_param_types, field_types)
            method_details = method_matches(candidate.body, candidate.name, candidate.kind)
            method_parameter_deps = find_method_parameter_dependencies(method_details)
            all_deps = constructor_deps + property_deps + method_parameter_deps
            public_method_names = sorted({method["name"] for method in method_details})
            component_type, layer, confidence, class_evidence, uncertainty = classify_component(candidate, all_deps)
            module_guess, module_conf, module_reason = module_guess_for_path_name(
                candidate.file, candidate.name, candidate.namespace, component_type
            )
            architecture_significance = architecture_significance_for_component(candidate, component_type, layer)
            component_id = f"COMP-{component_seq:04d}"
            component_seq += 1

            component = {
                "component_id": component_id,
                "name": candidate.name,
                "namespace_or_package": candidate.namespace,
                "module_path": candidate.file,
                "project": candidate.project or "unknown",
                "project_type": candidate.project_type or "unknown",
                "parser_backend": candidate.parser_backend,
                "language": candidate.language,
                "component_type": component_type,
                "type": component_type,
                "layer_guess": layer,
                "layer": layer,
                **architecture_significance,
                "module_guess": module_guess,
                "module_guess_confidence": module_conf,
                "module_guess_evidence": module_reason,
                "file": candidate.file,
                "start_line": candidate.start_line,
                "end_line": candidate.end_line,
                "public_methods": public_method_names,
                "method_details": [
                    {
                        "name": method["name"],
                        "return_type": method.get("return_type"),
                        "parameters": method.get("parameters", []),
                    }
                    for method in method_details
                ],
                "dependencies": all_deps,
                "imports": candidate.usings,
                "annotations": attribute_names(candidate.annotations),
                "raw_annotations": candidate.annotations,
                "base_class": candidate.bases[0] if candidate.bases else None,
                "implemented_interfaces": candidate.bases[1:] if len(candidate.bases) > 1 else candidate.bases if candidate.bases and candidate.bases[0].startswith("I") else [],
                "confidence": confidence,
                "confidence_breakdown": confidence_breakdown(
                    candidate.parser_backend + "_with_framework_heuristics",
                    confidence,
                    module_conf,
                    class_evidence,
                    uncertainty,
                ),
                "evidence": [
                    {
                        "file": candidate.file,
                        "line": candidate.start_line,
                        "reason": "; ".join(class_evidence) if class_evidence else "C# type declaration detected",
                    }
                ],
                "uncertainty": uncertainty,
            }
            components.append(component)
            internal_component_state[component_id] = {
                "candidate": candidate,
                "field_map": field_map,
                "module_guess": module_guess,
                "component_type": component_type,
                "layer": layer,
            }

            for using in candidate.usings:
                dependency_records.append(
                    {
                        "dependency_id": None,
                        "kind": "import",
                        "from": candidate.name,
                        "to": using,
                        "relationship": "imports",
                        "source_file": candidate.file,
                        "line": 1,
                        "evidence": f"C# using directive imports {using}",
                        "confidence": 0.76,
                        "metadata": {"project": candidate.project},
                    }
                )
            for dep in all_deps:
                dependency_records.append(
                    {
                        "dependency_id": None,
                        "kind": dep["source"],
                        "from": candidate.name,
                        "to": dep["type"],
                        "relationship": "injects" if "injection" in dep["source"] or dep["source"] == "constructor" else "uses",
                        "source_file": candidate.file,
                        "line": candidate.start_line,
                        "evidence": (
                            f"{dep['source']} dependency {dep['type']} {dep['name']} on method {dep.get('method')}"
                            if dep.get("method")
                            else f"{dep['source']} dependency {dep['type']} {dep['name']}"
                        ),
                        "confidence": dep["confidence"],
                        "metadata": dep,
                    }
                )

            method_calls = find_method_component_calls(candidate, field_map, method_details)
            fallback_calls = find_component_calls(candidate, field_map) if not method_calls else []
            for call in method_calls + fallback_calls:
                source_method = call.get("source_method")
                dependency_records.append(
                    {
                        "dependency_id": None,
                        "kind": "component_call",
                        "from": candidate.name,
                        "to": f"{call['target_type']}.{call['method']}",
                        "relationship": "calls",
                        "source_file": candidate.file,
                        "line": call["line"],
                        "evidence": (
                            f"{candidate.name}.{source_method} calls {call['target']}.{call['method']}()"
                            if source_method
                            else f"{candidate.name} calls {call['target']}.{call['method']}()"
                        ),
                        "confidence": 0.74 if source_method else 0.68,
                        "metadata": {
                            **call,
                            "source_component": candidate.name,
                            "source_method": source_method,
                            "target_component_or_type": call["target_type"],
                            "target_method": call["method"],
                            "resolution_quality": "method_scoped" if source_method else "class_body_fallback",
                        },
                    }
                )

            for send in find_mediatr_send_calls(candidate, field_map, method_details):
                dependency_records.append(
                    {
                        "dependency_id": None,
                        "kind": "mediatr_send",
                        "from": candidate.name,
                        "to": send["request_type"],
                        "relationship": "dispatches",
                        "source_file": candidate.file,
                        "line": send["line"],
                        "evidence": f"{candidate.name}.{send['source_method']} dispatches MediatR request {send['request_type']}",
                        "confidence": 0.82,
                        "metadata": {
                            **send,
                            "source_component": candidate.name,
                            "target_component_or_type": send["request_type"],
                            "target_method": "Handle",
                            "resolution_quality": "mediatr_request_dispatch",
                        },
                    }
                )

            for route in (
            csharp_routes_for_candidate(candidate, module_guess, field_map)
                + minimal_api_routes_for_candidate(candidate, module_guess, field_map, method_details)
                + program_routes_for_candidate(candidate, module_guess)
            ):
                route["route_id"] = f"ROUTE-{route_seq:04d}"
                route_seq += 1
                routes.append(route)

            for api_call in find_api_calls(text, rel_path, candidate.name, project):
                api_call_records.append(api_call)

    for record in razor_files:
        rel_path = normalize_slashes(record["path"])
        file_path = repo_root / rel_path
        project = project_for_file(rel_path, projects)
        try:
            component, razor_routes, api_calls = parse_razor_component(file_path, rel_path, project)
        except OSError as exc:
            skipped_files.append({"path": rel_path, "reason": f"read_error:{exc.__class__.__name__}"})
            continue
        component["component_id"] = f"COMP-{component_seq:04d}"
        component_seq += 1
        components.append(component)
        for dep in component["dependencies"]:
            dependency_records.append(
                {
                    "dependency_id": None,
                    "kind": dep["source"],
                    "from": component["name"],
                    "to": dep["type"],
                    "relationship": "injects" if "inject" in dep["source"] else "inherits",
                    "source_file": rel_path,
                    "line": component["start_line"],
                    "evidence": f"Razor directive {dep['source']} references {dep['type']}",
                    "confidence": dep["confidence"],
                    "metadata": dep,
                }
            )
        for route in razor_routes:
            route["route_id"] = f"ROUTE-{route_seq:04d}"
            route_seq += 1
            routes.append(route)
        api_call_records.extend(api_calls)

    for api_call in api_call_records:
        dependency_records.append(
            {
                "dependency_id": None,
                "kind": api_call["kind"],
                "from": api_call.get("source_component") or api_call["source_file"],
                "to": api_call["path_or_expression"],
                "relationship": "calls",
                "source_file": api_call["source_file"],
                "line": api_call["line"],
                "evidence": f"{api_call['http_method']} HTTP call to {api_call['path_or_expression']}",
                "confidence": api_call["confidence"],
                "metadata": api_call,
            }
        )

    for project in projects:
        for reference in project.project_references:
            target_project = resolve_project_reference(project, reference, projects_by_path)
            dependency_records.append(
                {
                    "dependency_id": None,
                    "kind": "project_reference",
                    "from": project.name,
                    "to": target_project.name if target_project else reference,
                    "relationship": "references",
                    "source_file": project.path,
                    "line": None,
                    "evidence": f"{project.name} project references {reference}",
                    "confidence": 0.93 if target_project else 0.65,
                    "metadata": {
                        "from_project_path": project.path,
                        "reference": reference,
                        "resolved_project": target_project.name if target_project else None,
                    },
                }
            )

    add_di_resolution_candidates(dependency_records)
    add_mediatr_handler_candidates(dependency_records, components)
    add_module_dependency_candidates(dependency_records, components)

    for idx, dependency in enumerate(dependency_records, start=1):
        dependency["dependency_id"] = f"DEP-{idx:05d}"

    for idx, route in enumerate(routes, start=1):
        entry_points.append(
            {
                "entry_point_id": f"ENTRY-{idx:04d}",
                "type": route["type"],
                "method": route.get("method", "unknown"),
                "path_or_name": route.get("path", "unknown"),
                "owning_component": route.get("component", "unknown"),
                "owning_module_guess": route.get("owning_module_guess", "Unknown"),
                "called_service_or_handler": route.get("called_services", []),
                "source_file": route.get("file", "unknown"),
                "line": route.get("line"),
                "confidence": route.get("confidence", 0.0),
                "evidence": route.get("evidence", []),
                "uncertainty": route.get("uncertainty", []),
                "parser_strategy": route.get("parser_strategy", "unknown"),
                "route_action": route.get("action", "unknown"),
            }
        )

    program_components = [component for component in components if component["file"].endswith("/Program.cs")]
    for component in program_components:
        entry_points.append(
            {
                "entry_point_id": f"ENTRY-{len(entry_points) + 1:04d}",
                "type": "CLI",
                "method": "unknown",
                "path_or_name": ".NET application bootstrap Program.cs",
                "owning_component": component["name"],
                "owning_module_guess": component.get("module_guess", "Unknown"),
                "called_service_or_handler": [],
                "source_file": component["file"],
                "line": component["start_line"],
                "confidence": 0.74,
                "evidence": [
                    {
                        "file": component["file"],
                        "line": component["start_line"],
                        "reason": "Program.cs top-level/application bootstrap entry point",
                    }
                ],
                "uncertainty": ["CLI classification here means executable bootstrap, not a user-facing command surface"],
            }
        )

    summary = summarize_counts(components, routes, dependency_records, entry_points)
    limitations = extraction_limitations(relevant_languages, parser_technologies, skipped_files)

    symbol_registry = {
        "generated_at": utc_now(),
        "extractor_version": EXTRACTOR_VERSION,
        "input_inventory_files": {
            "file_inventory": "architecture-output/inventory/file-inventory.json",
            "project_inventory": "architecture-output/inventory/project-inventory.json",
            "language_summary": "architecture-output/inventory/language-summary.json",
        },
        "technology_stacks_used_for_parsing": parser_technologies,
        "summary": summary,
        "components": components,
        "skipped_files": skipped_files,
        "limitations": limitations,
    }
    route_registry = {
        "generated_at": utc_now(),
        "extractor_version": EXTRACTOR_VERSION,
        "technology_stacks_used_for_parsing": parser_technologies,
        "summary": {
            "route_count": len(routes),
            "by_type": dict(Counter(route["type"] for route in routes)),
            "by_method": dict(Counter(route.get("method", "unknown") for route in routes)),
            "by_parser_strategy": dict(Counter(route.get("parser_strategy", "unknown") for route in routes)),
            "routes_with_source_evidence": sum(1 for route in routes if route.get("file") and route.get("line")),
        },
        "routes": routes,
        "limitations": limitations,
    }
    dependency_candidates = {
        "generated_at": utc_now(),
        "extractor_version": EXTRACTOR_VERSION,
        "technology_stacks_used_for_parsing": parser_technologies,
        "summary": {
            "dependency_count": len(dependency_records),
            "by_kind": dict(Counter(dep["kind"] for dep in dependency_records)),
            "by_relationship": dict(Counter(dep["relationship"] for dep in dependency_records)),
        },
        "dependencies": dependency_records,
        "limitations": limitations,
    }
    entry_point_candidates = {
        "generated_at": utc_now(),
        "extractor_version": EXTRACTOR_VERSION,
        "technology_stacks_used_for_parsing": parser_technologies,
        "summary": {
            "entry_point_count": len(entry_points),
            "by_type": dict(Counter(entry["type"] for entry in entry_points)),
        },
        "entry_points": entry_points,
        "limitations": limitations,
    }
    return symbol_registry, route_registry, dependency_candidates, entry_point_candidates


def component_module_lookup(components: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for component in components:
        lookup[component["name"]] = component.get("module_guess", "Unknown")
        if component["name"].startswith("I") and len(component["name"]) > 1:
            lookup[component["name"][1:]] = component.get("module_guess", "Unknown")
    return lookup


def add_di_resolution_candidates(dependency_records: list[dict[str, Any]]) -> None:
    registrations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dep in dependency_records:
        if dep.get("kind") not in {"di_registration", "db_context_registration"}:
            continue
        metadata = dep.get("metadata", {})
        service = simple_type_name(metadata.get("service") or dep.get("to", ""))
        implementation = simple_type_name(metadata.get("implementation") or dep.get("to", ""))
        if service and implementation and service != "unknown":
            registrations[service].append(dep)

    existing = {
        (dep.get("kind"), dep.get("from"), dep.get("to"), dep.get("source_file"), dep.get("line"))
        for dep in dependency_records
    }
    for dep in list(dependency_records):
        if dep.get("kind") not in {"constructor", "property_injection", "method_parameter", "razor_inject"}:
            continue
        target = simple_type_name(dep.get("to", ""))
        candidates = registrations.get(target)
        if not candidates and target.startswith("I"):
            candidates = registrations.get(target[1:])
        if not candidates:
            continue
        for registration in candidates[:3]:
            metadata = registration.get("metadata", {})
            implementation = simple_type_name(metadata.get("implementation") or registration.get("to", ""))
            marker = ("di_resolution_candidate", dep.get("from"), implementation, dep.get("source_file"), dep.get("line"))
            if marker in existing:
                continue
            existing.add(marker)
            dependency_records.append(
                {
                    "dependency_id": None,
                    "kind": "di_resolution_candidate",
                    "from": dep.get("from"),
                    "to": implementation,
                    "relationship": "resolves_to",
                    "source_file": dep.get("source_file"),
                    "line": dep.get("line"),
                    "evidence": f"{dep.get('from')} dependency {dep.get('to')} can resolve to registered implementation {implementation}",
                    "confidence": min(0.82, float(dep.get("confidence", 0.6)), float(registration.get("confidence", 0.6))),
                    "metadata": {
                        "source_dependency": dep.get("metadata", {}),
                        "registration": metadata,
                        "registration_file": registration.get("source_file"),
                        "registration_line": registration.get("line"),
                        "resolution_quality": "explicit_di_registration",
                    },
                }
            )


def add_mediatr_handler_candidates(dependency_records: list[dict[str, Any]], components: list[dict[str, Any]]) -> None:
    handlers_by_request: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for component in components:
        bases = [component.get("base_class")] + list(component.get("implemented_interfaces", []) or [])
        for base in bases:
            if not base or "IRequestHandler" not in str(base):
                continue
            generic_start = str(base).find("<")
            generic_end = str(base).rfind(">")
            if generic_start == -1 or generic_end == -1 or generic_end <= generic_start:
                continue
            args = split_top_level_commas(str(base)[generic_start + 1 : generic_end])
            if not args:
                continue
            request_type = simple_type_name(args[0])
            if request_type:
                handlers_by_request[request_type].append(component)

    existing = {
        (dep.get("kind"), dep.get("from"), dep.get("to"), dep.get("source_file"), dep.get("line"))
        for dep in dependency_records
    }
    for dep in list(dependency_records):
        if dep.get("kind") != "mediatr_send":
            continue
        request_type = simple_type_name(dep.get("to", ""))
        for handler in handlers_by_request.get(request_type, [])[:3]:
            marker = ("mediatr_handler_candidate", dep.get("from"), handler.get("name"), dep.get("source_file"), dep.get("line"))
            if marker in existing:
                continue
            existing.add(marker)
            dependency_records.append(
                {
                    "dependency_id": None,
                    "kind": "mediatr_handler_candidate",
                    "from": dep.get("from"),
                    "to": handler.get("name"),
                    "relationship": "dispatches_to",
                    "source_file": dep.get("source_file"),
                    "line": dep.get("line"),
                    "evidence": f"{dep.get('from')} MediatR request {request_type} can dispatch to handler {handler.get('name')}",
                    "confidence": min(0.84, float(dep.get("confidence", 0.7)), float(handler.get("confidence", 0.7))),
                    "metadata": {
                        "source_dependency": dep.get("metadata", {}),
                        "request_type": request_type,
                        "handler_component_id": handler.get("component_id"),
                        "handler_file": handler.get("file"),
                        "source_method": (dep.get("metadata") or {}).get("source_method"),
                        "target_component_or_type": handler.get("name"),
                        "target_method": "Handle",
                        "resolution_quality": "mediatr_handler_resolution",
                    },
                }
            )


def add_module_dependency_candidates(dependency_records: list[dict[str, Any]], components: list[dict[str, Any]]) -> None:
    comp_by_name = {component["name"]: component for component in components}
    module_by_component = component_module_lookup(components)
    existing: set[tuple[str, str, str]] = set()
    for dep in list(dependency_records):
        source_name = dep["from"]
        source_component = comp_by_name.get(source_name)
        if not source_component:
            continue
        source_module = source_component.get("module_guess", "Unknown")
        target = dep["to"]
        target_simple = simple_type_name(target.split(".", 1)[0])
        target_module = module_by_component.get(target_simple)
        if not target_module:
            if target_simple.startswith("I"):
                target_module = module_by_component.get(target_simple[1:])
        if not target_module or source_module == "Unknown" or target_module == "Unknown" or source_module == target_module:
            continue
        marker = (source_module, target_module, dep["kind"])
        if marker in existing:
            continue
        existing.add(marker)
        dependency_records.append(
            {
                "dependency_id": None,
                "kind": "module_dependency_candidate",
                "from": source_module,
                "to": target_module,
                "relationship": "uses",
                "source_file": dep["source_file"],
                "line": dep.get("line"),
                "evidence": f"Component dependency suggests {source_module} depends on {target_module}: {dep['from']} -> {dep['to']}",
                "confidence": min(0.72, dep.get("confidence", 0.6)),
                "metadata": {
                    "source_dependency_id": dep.get("dependency_id"),
                    "source_component": dep["from"],
                    "target": dep["to"],
                },
            }
        )


def summarize_counts(
    components: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    dependency_records: list[dict[str, Any]],
    entry_points: list[dict[str, Any]],
) -> dict[str, Any]:
    frontend_types = {"FrontendComponent", "FrontendService", "RouteGuard", "StateStore"}
    backend_types = {"Controller", "Service", "Repository", "Middleware", "Handler", "Configuration", "ExternalClient", "Gateway", "Entity", "DTO", "Mapper", "Validator"}
    job_types = {"ScheduledJob", "MessageConsumer", "BatchJob"}
    return {
        "component_count": len(components),
        "entry_point_count": len(entry_points),
        "route_count": len(routes),
        "dependency_count": len(dependency_records),
        "frontend_artifact_count": sum(1 for component in components if component["component_type"] in frontend_types),
        "backend_artifact_count": sum(1 for component in components if component["component_type"] in backend_types),
        "jobs_consumers_count": sum(1 for component in components if component["component_type"] in job_types)
        + sum(1 for entry in entry_points if entry["type"] in {"ScheduledJob", "MessageConsumer", "BatchJob"}),
        "components_by_type": dict(Counter(component["component_type"] for component in components)),
        "components_by_layer": dict(Counter(component["layer_guess"] for component in components)),
        "components_by_parser_backend": dict(Counter(component.get("parser_backend", "unknown") for component in components)),
        "entry_points_by_type": dict(Counter(entry["type"] for entry in entry_points)),
        "dependencies_by_kind": dict(Counter(dep["kind"] for dep in dependency_records)),
    }


def extraction_limitations(
    relevant_languages: set[str],
    parser_technologies: list[dict[str, Any]],
    skipped_files: list[dict[str, str]],
) -> list[str]:
    csharp_stack = next((item for item in parser_technologies if item.get("name") == ".NET / C#"), {})
    ast_backends = csharp_stack.get("ast_backends", [])
    unavailable_ast = [
        f"{backend.get('name')}: {backend.get('reason_unavailable')}"
        for backend in ast_backends
        if not backend.get("available") and backend.get("reason_unavailable")
    ]
    limitations = [
        "C# symbol extraction uses static structural/framework parsing unless an optional Roslyn or tree-sitter backend is available.",
        "Method-call extraction records dependency candidates, not complete call graphs; overload resolution and dynamic dispatch are not resolved.",
        "Razor/Blazor parsing captures directives and injected services but does not compile generated partial classes.",
        "Module guesses are evidence-derived domain/project/support candidates for parsed facts only; final module maps still require evidence-pack consolidation and human review.",
        "Route templates with framework conventions are captured as templates; runtime route token transformers and filters are not fully evaluated.",
    ]
    if unavailable_ast:
        limitations.append("Optional AST backends unavailable in this environment: " + "; ".join(unavailable_ast) + ".")
    if skipped_files:
        limitations.append(f"{len(skipped_files)} generated or migration-pattern source files were skipped for parser safety.")
    unsupported = relevant_languages - {"csharp", "razor", "json", "msbuild", "dotnet_solution", "xml", "yaml", "bicep", "markdown", "css", "image", "unknown", "dockerfile", "docker_ignore", "editorconfig", "git_attributes", "git_ignore", "javascript"}
    if unsupported:
        limitations.append(f"Detected languages without parser support in this step: {', '.join(sorted(unsupported))}.")
    return limitations


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract structured parsed facts from Step 1 inventory.")
    parser.add_argument("--repo-root", default=".", help="Legacy repository root. Defaults to current directory.")
    parser.add_argument(
        "--output-root",
        default="architecture-output",
        help="Architecture output root. Defaults to ./architecture-output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    inventory_root = output_root / "inventory"
    parsed_root = output_root / "parsed"

    file_inventory = load_json(inventory_root / "file-inventory.json")
    project_inventory = load_json(inventory_root / "project-inventory.json")
    language_summary = load_json(inventory_root / "language-summary.json")

    symbol_registry, route_registry, dependency_candidates, entry_point_candidates = build_symbol_registry(
        repo_root,
        file_inventory,
        project_inventory,
        language_summary,
    )

    write_json(parsed_root / "symbol-registry.json", symbol_registry)
    write_json(parsed_root / "route-registry.json", route_registry)
    write_json(parsed_root / "dependency-candidates.json", dependency_candidates)
    write_json(parsed_root / "entry-point-candidates.json", entry_point_candidates)

    print(
        json.dumps(
            {
                "symbol_registry": str(parsed_root / "symbol-registry.json"),
                "route_registry": str(parsed_root / "route-registry.json"),
                "dependency_candidates": str(parsed_root / "dependency-candidates.json"),
                "entry_point_candidates": str(parsed_root / "entry-point-candidates.json"),
                "summary": symbol_registry["summary"],
                "technology_stacks_used_for_parsing": [item["name"] for item in symbol_registry["technology_stacks_used_for_parsing"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
