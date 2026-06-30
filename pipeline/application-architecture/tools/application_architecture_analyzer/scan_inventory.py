#!/usr/bin/env python3
"""
Scanner/inventory phase for application architecture extraction.

This tool intentionally stops at file, language, and project inventory. It does
not parse symbols, infer module boundaries, or generate final architecture
artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCANNER_VERSION = "0.1.0"

IGNORED_DIRECTORY_NAMES = {
    ".git": "ignored_directory:.git",
    ".idea": "ignored_directory:.idea",
    ".vscode": "ignored_directory:.vscode",
    "bin": "ignored_directory:bin",
    "build": "ignored_directory:build",
    "coverage": "ignored_directory:coverage",
    "dist": "ignored_directory:dist",
    "generated": "ignored_directory:generated",
    "logs": "ignored_directory:logs",
    "node_modules": "ignored_directory:node_modules",
    "obj": "ignored_directory:obj",
    "target": "ignored_directory:target",
}

ANALYZER_TOOLING_PREFIX = PurePosixPath("tools/application_architecture_analyzer")
OUTPUT_PREFIX = PurePosixPath("architecture-output")

LANGUAGE_BY_EXTENSION = {
    ".bicep": "bicep",
    ".config": "xml",
    ".cs": "csharp",
    ".cshtml": "razor",
    ".csproj": "msbuild",
    ".css": "css",
    ".dcproj": "msbuild",
    ".editorconfig": "editorconfig",
    ".gitattributes": "git_attributes",
    ".gitignore": "git_ignore",
    ".html": "html",
    ".ico": "image",
    ".jpeg": "image",
    ".jpg": "image",
    ".js": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".png": "image",
    ".props": "msbuild",
    ".razor": "razor",
    ".runsettings": "xml",
    ".sln": "dotnet_solution",
    ".svg": "svg",
    ".targets": "msbuild",
    ".txt": "text",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}

LANGUAGE_BY_FILENAME = {
    ".dockerignore": "docker_ignore",
    ".editorconfig": "editorconfig",
    ".gitattributes": "git_attributes",
    ".gitignore": "git_ignore",
    "Dockerfile": "dockerfile",
    "Jenkinsfile": "jenkins",
}

BUILD_FILE_NAMES = {
    "angular.json",
    "build.gradle",
    "composer.json",
    "Directory.Packages.props",
    "docker-compose.dcproj",
    "docker-compose.override.yml",
    "docker-compose.yml",
    "Everything.sln",
    "global.json",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "settings.gradle",
}

DEPLOYMENT_FILE_NAMES = {
    "azure-pipelines.yml",
    "azure.yaml",
    "docker-compose.override.yml",
    "docker-compose.yml",
    "Dockerfile",
    "Jenkinsfile",
}

TEXT_EXTENSIONS = {
    ".bicep",
    ".config",
    ".cs",
    ".cshtml",
    ".csproj",
    ".css",
    ".dcproj",
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    ".html",
    ".js",
    ".json",
    ".md",
    ".props",
    ".razor",
    ".runsettings",
    ".sln",
    ".svg",
    ".targets",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel_posix(path: Path, root: Path) -> str:
    if path == root:
        return "."
    return path.relative_to(root).as_posix()


def rel_pure(path: Path, root: Path) -> PurePosixPath:
    relative = rel_posix(path, root)
    if relative == ".":
        return PurePosixPath(".")
    return PurePosixPath(relative)


def is_relative_to(path: PurePosixPath, prefix: PurePosixPath) -> bool:
    return path == prefix or path.is_relative_to(prefix)


def should_ignore_directory(rel_path: PurePosixPath) -> str | None:
    if rel_path == PurePosixPath("."):
        return None
    if is_relative_to(rel_path, OUTPUT_PREFIX):
        return "generated_output:architecture-output"
    if is_relative_to(rel_path, ANALYZER_TOOLING_PREFIX):
        return "analyzer_tooling:tools/application_architecture_analyzer"
    for part in rel_path.parts:
        reason = IGNORED_DIRECTORY_NAMES.get(part)
        if reason:
            return reason
    if "vendor" in rel_path.parts:
        return "ignored_directory:vendor"
    return None


def should_ignore_file(rel_path: PurePosixPath) -> str | None:
    directory_reason = should_ignore_directory(rel_path.parent)
    if directory_reason:
        return directory_reason

    name = rel_path.name
    lower_name = name.lower()
    lower_suffixes = [suffix.lower() for suffix in rel_path.suffixes]

    if lower_name.endswith(".min.js"):
        return "ignored_file:minified_js"
    if lower_name.endswith(".map") or ".map" in lower_suffixes:
        return "ignored_file:source_map"
    if lower_name.endswith(".log"):
        return "ignored_file:log"
    if lower_name.endswith(".g.cs") or lower_name.endswith(".g.i.cs"):
        return "ignored_file:generated_csharp"
    if lower_name.endswith(".designer.cs"):
        return "ignored_file:generated_designer_csharp"
    if ".generated." in lower_name:
        return "ignored_file:generated_file"
    return None


def detect_language(path: PurePosixPath) -> str:
    if path.name in LANGUAGE_BY_FILENAME:
        return LANGUAGE_BY_FILENAME[path.name]
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "unknown")


def classify_candidate(path: PurePosixPath, language: str) -> str:
    name = path.name
    lower_name = name.lower()
    lower_parts = [part.lower() for part in path.parts]
    suffix = path.suffix.lower()

    if name in BUILD_FILE_NAMES or suffix in {".sln", ".csproj", ".dcproj", ".props", ".targets"}:
        return "build"
    if name in DEPLOYMENT_FILE_NAMES or ".github" in lower_parts and "workflows" in lower_parts:
        return "build"
    if lower_name.startswith("appsettings") or lower_name in {"web.config", "global.json"}:
        return "config"
    if suffix in {".json", ".config", ".xml", ".yaml", ".yml", ".runsettings"} and (
        "properties" in lower_parts or "configuration" in lower_parts or lower_name.endswith("config.json")
    ):
        return "config"
    if suffix == ".cs" and (lower_name.endswith("controller.cs") or "endpoints" in lower_name or any(part.endswith("endpoints") for part in lower_parts)):
        return "controller"
    if suffix == ".cs" and (lower_name.endswith("service.cs") or "services" in lower_parts):
        return "service"
    if suffix == ".cs" and (lower_name.endswith("repository.cs") or "repositories" in lower_parts):
        return "repository"
    if suffix == ".cs" and ("entities" in lower_parts or lower_name.endswith("entity.cs")):
        return "entity"
    if suffix in {".razor", ".cshtml"}:
        return "frontend_component"
    if language in {"css", "html", "javascript"} and any(part in {"pages", "views", "wwwroot"} for part in lower_parts):
        return "frontend_component"
    return "unknown"


def looks_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    if not data:
        return False
    sample = data[:4096]
    text_chars = bytes(range(32, 127)) + b"\n\r\t\f\b"
    non_text = sample.translate(None, text_chars)
    return len(non_text) / len(sample) > 0.30


def line_count_for_file(path: Path, data: bytes, extension: str) -> int | None:
    if looks_binary(data) and extension.lower() not in TEXT_EXTENSIONS:
        return None
    if not data:
        return 0
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
            except UnicodeDecodeError:
                return None
    return len(text.splitlines())


def hash_file(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def collect_ignored_files(ignored_dir: Path, root: Path, reason: str) -> list[dict[str, Any]]:
    ignored_files: list[dict[str, Any]] = []
    for walk_root, dirs, files in os.walk(ignored_dir):
        dirs[:] = sorted(d for d in dirs if not should_ignore_directory(rel_pure(Path(walk_root) / d, root)))
        for file_name in sorted(files):
            file_path = Path(walk_root) / file_name
            rel_path = rel_pure(file_path, root)
            ignored_files.append(
                {
                    "path": rel_path.as_posix(),
                    "extension": file_path.suffix.lower(),
                    "ignore_reason": should_ignore_file(rel_path) or reason,
                }
            )
    return ignored_files


def scan_files(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    included_files: list[dict[str, Any]] = []
    ignored_files: list[dict[str, Any]] = []
    ignored_directories: list[dict[str, Any]] = []

    for walk_root, dirs, files in os.walk(repo_root):
        walk_path = Path(walk_root)

        kept_dirs: list[str] = []
        for dir_name in sorted(dirs):
            dir_path = walk_path / dir_name
            rel_dir = rel_pure(dir_path, repo_root)
            reason = should_ignore_directory(rel_dir)
            if reason:
                files_in_dir = collect_ignored_files(dir_path, repo_root, reason)
                ignored_directories.append(
                    {
                        "path": rel_dir.as_posix(),
                        "ignore_reason": reason,
                        "ignored_file_count": len(files_in_dir),
                    }
                )
                ignored_files.extend(files_in_dir)
            else:
                kept_dirs.append(dir_name)
        dirs[:] = kept_dirs

        for file_name in sorted(files):
            file_path = walk_path / file_name
            rel_path = rel_pure(file_path, repo_root)
            ignore_reason = should_ignore_file(rel_path)
            if ignore_reason:
                ignored_files.append(
                    {
                        "path": rel_path.as_posix(),
                        "extension": file_path.suffix.lower(),
                        "ignore_reason": ignore_reason,
                    }
                )
                continue

            try:
                data = file_path.read_bytes()
                stat = file_path.stat()
            except OSError as exc:
                ignored_files.append(
                    {
                        "path": rel_path.as_posix(),
                        "extension": file_path.suffix.lower(),
                        "ignore_reason": f"read_error:{exc.__class__.__name__}",
                    }
                )
                continue

            language = detect_language(rel_path)
            included_files.append(
                {
                    "path": rel_path.as_posix(),
                    "extension": file_path.suffix.lower(),
                    "language": language,
                    "size_bytes": stat.st_size,
                    "line_count": line_count_for_file(file_path, data, file_path.suffix),
                    "hash": hash_file(data),
                    "candidate_type": classify_candidate(rel_path, language),
                    "ignored": False,
                    "ignore_reason": None,
                }
            )

    return included_files, ignored_files, ignored_directories


def first_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if child.tag.split("}")[-1] == name and child.text:
            return child.text.strip()
    return None


def values_by_tag(element: ET.Element, name: str, attribute: str | None = None) -> list[str]:
    values: list[str] = []
    for child in element.iter():
        if child.tag.split("}")[-1] != name:
            continue
        if attribute:
            value = child.attrib.get(attribute)
        else:
            value = child.text
        if value:
            values.append(value.strip())
    return sorted(set(values))


def parse_csproj(path: Path, repo_root: Path) -> dict[str, Any]:
    rel_path = rel_posix(path, repo_root)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {
            "name": path.stem,
            "path": rel_path,
            "project_kind": "dotnet",
            "type": "unknown",
            "category": "unknown",
            "framework": "unknown",
            "deployable": False,
            "source_path": path.parent.relative_to(repo_root).as_posix(),
            "framework_indicators": [],
            "package_references": [],
            "project_references": [],
            "evidence": [{"file": rel_path, "reason": f"csproj parse error: {exc}"}],
            "confidence": 0.2,
        }

    sdk = root.attrib.get("Sdk", "unknown")
    target_framework = first_text(root, "TargetFramework") or first_text(root, "TargetFrameworks") or "unknown"
    package_refs = values_by_tag(root, "PackageReference", "Include")
    project_refs = [Path(ref).as_posix() for ref in values_by_tag(root, "ProjectReference", "Include")]
    output_type = first_text(root, "OutputType") or "unknown"
    rel_parent = path.parent.relative_to(repo_root).as_posix()
    lower_path = rel_path.lower()
    lower_name = path.stem.lower()

    indicators: list[str] = [f"sdk:{sdk}"]
    if target_framework != "unknown":
        indicators.append(f"target_framework:{target_framework}")
    if output_type != "unknown":
        indicators.append(f"output_type:{output_type}")

    package_set = {package.lower() for package in package_refs}
    has_program = (path.parent / "Program.cs").exists()
    has_startup = (path.parent / "Startup.cs").exists()
    has_dockerfile = (path.parent / "Dockerfile").exists()
    has_appsettings = any(path.parent.glob("appsettings*.json"))

    if "microsoft.net.test.sdk" in package_set or "\\tests\\" in f"\\{lower_path}" or lower_name.endswith("tests"):
        project_type = "test_project"
        category = "test"
        deployable = False
        confidence = 0.95
        indicators.append("test_indicator:Microsoft.NET.Test.Sdk_or_tests_path")
    elif "Microsoft.NET.Sdk.BlazorWebAssembly".lower() in sdk.lower() or "microsoft.aspnetcore.components.webassembly" in package_set:
        project_type = "frontend_spa"
        category = "frontend"
        deployable = False
        confidence = 0.9
        indicators.append("frontend_indicator:BlazorWebAssembly")
    elif "Microsoft.NET.Sdk.Web".lower() in sdk.lower():
        if "api" in lower_name or "ardalis.apiendpoints" in package_set or "minimalapi.endpoint" in package_set:
            project_type = "backend_web_api"
        else:
            project_type = "backend_web_app"
        category = "backend"
        deployable = True
        confidence = 0.92
        indicators.append("backend_indicator:Microsoft.NET.Sdk.Web")
    elif "microsoft.entityframeworkcore.sqlserver" in package_set or "microsoft.entityframeworkcore.inmemory" in package_set:
        project_type = "database_support_library"
        category = "database_support"
        deployable = False
        confidence = 0.78
        indicators.append("database_indicator:EntityFrameworkCore")
    else:
        project_type = "library"
        category = "support"
        deployable = False
        confidence = 0.75

    if has_program:
        indicators.append("entry_point_file:Program.cs")
    if has_startup:
        indicators.append("entry_point_file:Startup.cs")
    if has_appsettings:
        indicators.append("config_file:appsettings.json")
    if has_dockerfile:
        indicators.append("deployment_file:Dockerfile")

    evidence_reason = f".NET project file using {sdk}"
    if deployable:
        evidence_reason += "; deployable inferred from web SDK"

    return {
        "name": path.stem,
        "path": rel_path,
        "project_kind": "dotnet",
        "type": project_type,
        "category": category,
        "framework": f".NET ({sdk}; target={target_framework})",
        "deployable": deployable,
        "source_path": rel_parent,
        "framework_indicators": sorted(set(indicators)),
        "package_references": package_refs,
        "project_references": project_refs,
        "evidence": [{"file": rel_path, "reason": evidence_reason}],
        "confidence": confidence,
    }


def parse_solution(path: Path, repo_root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    projects = []
    for match in re.finditer(r'Project\("[^"]+"\)\s*=\s*"([^"]+)",\s*"([^"]+)",\s*"', text):
        projects.append({"name": match.group(1), "path": PurePosixPath(match.group(2).replace("\\", "/")).as_posix()})
    return {
        "name": path.stem,
        "path": rel_posix(path, repo_root),
        "project_count": len(projects),
        "projects": projects,
    }


def detect_package_json(path: Path, repo_root: Path) -> dict[str, Any]:
    rel_path = rel_posix(path, repo_root)
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "name": path.parent.name,
            "path": rel_path,
            "project_kind": "frontend",
            "type": "unknown",
            "category": "unknown",
            "framework": "unknown",
            "deployable": False,
            "source_path": path.parent.relative_to(repo_root).as_posix(),
            "framework_indicators": [f"package_json_parse_error:{exc.__class__.__name__}"],
            "evidence": [{"file": rel_path, "reason": "package.json parse failed"}],
            "confidence": 0.2,
        }

    deps = set((content.get("dependencies") or {}).keys()) | set((content.get("devDependencies") or {}).keys())
    indicators = ["frontend_indicator:package.json"]
    framework = "unknown"
    if "react" in deps:
        framework = "React"
        indicators.append("dependency:react")
    elif "@angular/core" in deps:
        framework = "Angular"
        indicators.append("dependency:@angular/core")
    elif "vue" in deps:
        framework = "Vue"
        indicators.append("dependency:vue")
    elif "vite" in deps:
        framework = "Vite"
        indicators.append("dependency:vite")

    return {
        "name": content.get("name") or path.parent.name,
        "path": rel_path,
        "project_kind": "frontend",
        "type": "frontend_spa",
        "category": "frontend",
        "framework": framework,
        "deployable": True,
        "source_path": path.parent.relative_to(repo_root).as_posix(),
        "framework_indicators": indicators,
        "package_references": sorted(deps),
        "project_references": [],
        "evidence": [{"file": rel_path, "reason": "frontend package manifest"}],
        "confidence": 0.75 if framework == "unknown" else 0.9,
    }


def classify_build_or_deployment_file(rel_path: str) -> str | None:
    name = PurePosixPath(rel_path).name
    lower = rel_path.lower()
    if name in DEPLOYMENT_FILE_NAMES or lower.startswith(".github/workflows/") or lower.startswith("infra/"):
        return "deployment"
    if name in BUILD_FILE_NAMES or Path(name).suffix.lower() in {".sln", ".csproj", ".dcproj", ".props", ".targets"}:
        return "build"
    return None


def detect_projects(repo_root: Path, files: list[dict[str, Any]]) -> dict[str, Any]:
    by_path = {record["path"]: record for record in files}
    csproj_paths = sorted(Path(repo_root / record["path"]) for record in files if record["extension"] == ".csproj")
    sln_paths = sorted(Path(repo_root / record["path"]) for record in files if record["extension"] == ".sln")
    package_json_paths = sorted(Path(repo_root / record["path"]) for record in files if record["path"].endswith("package.json"))

    dotnet_projects = [parse_csproj(path, repo_root) for path in csproj_paths]
    frontend_package_projects = [detect_package_json(path, repo_root) for path in package_json_paths]
    all_projects = dotnet_projects + frontend_package_projects

    build_files = []
    deployment_files = []
    for record in files:
        role = classify_build_or_deployment_file(record["path"])
        if role == "build":
            build_files.append(record["path"])
        elif role == "deployment":
            deployment_files.append(record["path"])

    solutions = [parse_solution(path, repo_root) for path in sln_paths]

    backend_projects = [project for project in all_projects if project["category"] == "backend"]
    frontend_projects = [project for project in all_projects if project["category"] == "frontend"]
    database_projects = [project for project in all_projects if project["category"] == "database_support"]
    supporting_projects = [project for project in all_projects if project["category"] in {"support", "database_support"}]
    test_projects = [project for project in all_projects if project["category"] == "test"]
    deployable_units = [project for project in all_projects if project["deployable"]]

    docker_compose_services = detect_docker_compose_services(repo_root, by_path)

    return {
        "repo_root": str(repo_root),
        "generated_at": utc_now(),
        "scanner_version": SCANNER_VERSION,
        "solutions": solutions,
        "projects": all_projects,
        "backend_projects": backend_projects,
        "frontend_projects": frontend_projects,
        "database_projects": database_projects,
        "supporting_projects": supporting_projects,
        "test_projects": test_projects,
        "deployable_units": deployable_units,
        "build_files": sorted(set(build_files)),
        "deployment_files": sorted(set(deployment_files)),
        "docker_compose_services": docker_compose_services,
        "framework_indicators": sorted(
            set(
                indicator
                for project in all_projects
                for indicator in project.get("framework_indicators", [])
            )
        ),
        "summary": {
            "solution_count": len(solutions),
            "project_count": len(all_projects),
            "backend_project_count": len(backend_projects),
            "frontend_project_count": len(frontend_projects),
            "database_project_count": len(database_projects),
            "supporting_project_count": len(supporting_projects),
            "test_project_count": len(test_projects),
            "deployable_unit_count": len(deployable_units),
        },
    }


def detect_docker_compose_services(repo_root: Path, by_path: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    services: list[dict[str, str]] = []
    compose_paths = [path for path in by_path if PurePosixPath(path).name in {"docker-compose.yml", "docker-compose.yaml"}]
    for rel_path in sorted(compose_paths):
        text = (repo_root / rel_path).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        in_services = False
        for line in lines:
            stripped = line.strip()
            if stripped == "services:":
                in_services = True
                continue
            if not in_services:
                continue
            match = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
            if match:
                services.append({"name": match.group(1), "file": rel_path})
    return services


def language_summary(files: list[dict[str, Any]], ignored_files: list[dict[str, Any]]) -> dict[str, Any]:
    language_counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"file_count": 0, "total_bytes": 0, "total_lines": 0})
    extension_counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"file_count": 0, "total_bytes": 0})

    for record in files:
        language = record["language"]
        language_counts[language]["file_count"] += 1
        language_counts[language]["total_bytes"] += record["size_bytes"]
        if record["line_count"] is not None:
            language_counts[language]["total_lines"] += record["line_count"]

        extension = record["extension"] or "[no extension]"
        extension_counts[extension]["file_count"] += 1
        extension_counts[extension]["total_bytes"] += record["size_bytes"]

    languages = [
        {"language": language, **values}
        for language, values in sorted(language_counts.items(), key=lambda item: (-item[1]["file_count"], item[0]))
    ]
    extensions = [
        {"extension": extension, **values}
        for extension, values in sorted(extension_counts.items(), key=lambda item: (-item[1]["file_count"], item[0]))
    ]

    return {
        "generated_at": utc_now(),
        "scanner_version": SCANNER_VERSION,
        "total_files_scanned": len(files),
        "total_files_ignored": len(ignored_files),
        "languages": languages,
        "extensions": extensions,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def run(repo_root: Path, output_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()

    files, ignored_files, ignored_directories = scan_files(repo_root)
    projects = detect_projects(repo_root, files)
    lang_summary = language_summary(files, ignored_files)

    inventory_dir = output_root / "inventory"
    file_inventory = {
        "repo_root": str(repo_root),
        "generated_at": utc_now(),
        "scanner_version": SCANNER_VERSION,
        "summary": {
            "total_files_scanned": len(files),
            "total_files_ignored": len(ignored_files),
        },
        "files": files,
    }
    ignored_report = {
        "repo_root": str(repo_root),
        "generated_at": utc_now(),
        "scanner_version": SCANNER_VERSION,
        "ignored_rules": {
            "directories": IGNORED_DIRECTORY_NAMES,
            "files": [
                "*.min.js",
                "*.map",
                "*.log",
                "*.g.cs",
                "*.g.i.cs",
                "*.designer.cs",
                "*.generated.*",
            ],
            "additional_non_legacy_artifacts": [
                "architecture-output/",
                "tools/application_architecture_analyzer/",
            ],
        },
        "total_files_ignored": len(ignored_files),
        "total_directories_ignored": len(ignored_directories),
        "ignored_directories": ignored_directories,
        "ignored_files": ignored_files,
    }

    write_json(inventory_dir / "file-inventory.json", file_inventory)
    write_json(inventory_dir / "project-inventory.json", projects)
    write_json(inventory_dir / "language-summary.json", lang_summary)
    write_json(inventory_dir / "ignored-files-report.json", ignored_report)

    return {
        "file_inventory": inventory_dir / "file-inventory.json",
        "project_inventory": inventory_dir / "project-inventory.json",
        "language_summary": inventory_dir / "language-summary.json",
        "ignored_report": inventory_dir / "ignored-files-report.json",
        "total_files_scanned": len(files),
        "total_files_ignored": len(ignored_files),
        "languages": [item["language"] for item in lang_summary["languages"]],
        "projects": projects,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate scanner/inventory artifacts for application architecture extraction.")
    parser.add_argument("--repo-root", default=".", help="Legacy repository root. Defaults to current directory.")
    parser.add_argument(
        "--output-root",
        default="architecture-output",
        help="Architecture output root. Defaults to ./architecture-output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root)
    output_root = Path(args.output_root)
    result = run(repo_root, output_root)
    print(json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in result.items() if key != "projects"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
