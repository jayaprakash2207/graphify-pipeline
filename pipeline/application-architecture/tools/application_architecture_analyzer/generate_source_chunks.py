#!/usr/bin/env python3
"""
Generate a source chunk index for evidence-first architecture extraction.

Inputs:
  - architecture-output/inventory/file-inventory.json
  - architecture-output/inventory/project-inventory.json

Outputs:
  - architecture-output/parsed/source-chunk-index.json

This stage improves traceability by creating stable, small source slices with
line ranges, hashes, language/project metadata, and lightweight symbol/route
hints. It does not modify legacy source code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHUNKER_VERSION = "0.1.0"
DEFAULT_CHUNK_LINES = 80
DEFAULT_OVERLAP_LINES = 10

CHUNKABLE_LANGUAGES = {
    "csharp",
    "razor",
    "javascript",
    "json",
    "msbuild",
    "xml",
    "yaml",
    "dockerfile",
    "bicep",
    "markdown",
}

SYMBOL_RE = re.compile(
    r"\b(class|interface|struct|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)"
    r"|\b(public|internal|protected|private)\s+(?:static\s+|async\s+|override\s+|virtual\s+)*[A-Za-z_][A-Za-z0-9_<>,\[\]\?\.]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)

ROUTE_RE = re.compile(
    r"(@page\s+\"[^\"]+\"|Map(?:Get|Post|Put|Delete|Patch|HealthChecks)\s*\(\s*@?\"[^\"]+\"|"
    r"\[Http(?:Get|Post|Put|Delete|Patch)(?:\s*\(\s*@?\"[^\"]*\"\s*\))?\]|"
    r"\b(?:Get|Post|Put|Delete|Patch)\s*\(\s*@?\"[^\"]+\")"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def normalize_slashes(value: str) -> str:
    return value.replace("\\", "/")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def project_for_file(path: str, projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = normalize_slashes(path)
    matches = [
        project
        for project in projects
        if normalized.startswith(normalize_slashes(project.get("source_path", "")).rstrip("/") + "/")
        or normalized == normalize_slashes(project.get("source_path", ""))
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda item: len(item.get("source_path", "")), reverse=True)[0]


def symbol_hints(text: str) -> list[str]:
    values: list[str] = []
    for match in SYMBOL_RE.finditer(text):
        value = match.group(2) or match.group(4)
        if value and value not in values:
            values.append(value)
        if len(values) >= 20:
            break
    return values


def route_hints(text: str) -> list[str]:
    values: list[str] = []
    for match in ROUTE_RE.finditer(text):
        value = re.sub(r"\s+", " ", match.group(0)).strip()
        if value and value not in values:
            values.append(value)
        if len(values) >= 20:
            break
    return values


def make_chunks(
    repo_root: Path,
    file_record: dict[str, Any],
    project: dict[str, Any] | None,
    chunk_lines: int,
    overlap_lines: int,
    next_id: int,
) -> tuple[list[dict[str, Any]], int]:
    rel_path = normalize_slashes(file_record["path"])
    path = repo_root / rel_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], next_id

    lines = text.splitlines()
    if not lines:
        lines = [""]
    file_hash = sha256_text(text)
    chunks: list[dict[str, Any]] = []
    step = max(1, chunk_lines - overlap_lines)
    for start_index in range(0, len(lines), step):
        end_index = min(len(lines), start_index + chunk_lines)
        chunk_text = "\n".join(lines[start_index:end_index])
        chunk_id = f"CHUNK-{next_id:06d}"
        next_id += 1
        chunks.append(
            {
                "chunk_id": chunk_id,
                "file": rel_path,
                "language": file_record.get("language", "unknown"),
                "project": project.get("name") if project else "unknown",
                "project_type": project.get("type") if project else "unknown",
                "project_category": project.get("category") if project else "unknown",
                "start_line": start_index + 1,
                "end_line": end_index,
                "line_count": end_index - start_index,
                "file_sha256": file_hash,
                "chunk_sha256": sha256_text(chunk_text),
                "symbol_hints": symbol_hints(chunk_text),
                "route_hints": route_hints(chunk_text),
                "contains_entry_point_hint": bool(route_hints(chunk_text) or rel_path.endswith("/Program.cs")),
                "contains_dependency_hint": any(
                    token in chunk_text
                    for token in ["using ", "@inject ", "AddScoped", "AddTransient", "AddSingleton", "AddDbContext", "ProjectReference"]
                ),
                "text_preview": chunk_text[:500],
            }
        )
        if end_index == len(lines):
            break
    return chunks, next_id


def build_chunk_index(repo_root: Path, output_root: Path, chunk_lines: int, overlap_lines: int) -> dict[str, Any]:
    inventory_root = output_root / "inventory"
    file_inventory = load_json(inventory_root / "file-inventory.json")
    project_inventory = load_json(inventory_root / "project-inventory.json")
    projects = project_inventory.get("projects", [])
    chunks: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    next_id = 1

    for file_record in file_inventory.get("files", []):
        language = file_record.get("language")
        rel_path = normalize_slashes(file_record.get("path", ""))
        if language not in CHUNKABLE_LANGUAGES:
            skipped.append({"path": rel_path, "reason": f"non_chunkable_language:{language}"})
            continue
        if file_record.get("is_binary"):
            skipped.append({"path": rel_path, "reason": "binary_file"})
            continue
        project = project_for_file(rel_path, projects)
        file_chunks, next_id = make_chunks(repo_root, file_record, project, chunk_lines, overlap_lines, next_id)
        if not file_chunks:
            skipped.append({"path": rel_path, "reason": "read_error_or_empty"})
            continue
        chunks.extend(file_chunks)

    return {
        "generated_at": utc_now(),
        "chunker_version": CHUNKER_VERSION,
        "source_inventory": "architecture-output/inventory/file-inventory.json",
        "project_inventory": "architecture-output/inventory/project-inventory.json",
        "chunking_strategy": {
            "chunk_lines": chunk_lines,
            "overlap_lines": overlap_lines,
            "purpose": "focused source evidence retrieval for architecture claims, parser verification, and human review",
        },
        "summary": {
            "chunk_count": len(chunks),
            "chunked_file_count": len({chunk["file"] for chunk in chunks}),
            "skipped_file_count": len(skipped),
            "chunks_by_language": dict(Counter(chunk["language"] for chunk in chunks)),
            "chunks_by_project": dict(Counter(chunk["project"] for chunk in chunks)),
            "entry_point_hint_chunks": sum(1 for chunk in chunks if chunk["contains_entry_point_hint"]),
            "dependency_hint_chunks": sum(1 for chunk in chunks if chunk["contains_dependency_hint"]),
        },
        "chunks": chunks,
        "skipped_files": skipped,
        "limitations": [
            "Chunking improves evidence retrieval and review precision but does not by itself provide compiler semantic binding.",
            "Chunk hints are intentionally lightweight; authoritative symbols/routes remain in parsed registries.",
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate chunked source evidence index.")
    parser.add_argument("--repo-root", default=".", help="Legacy repository root. Defaults to current directory.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    parser.add_argument("--chunk-lines", type=int, default=DEFAULT_CHUNK_LINES)
    parser.add_argument("--overlap-lines", type=int, default=DEFAULT_OVERLAP_LINES)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    payload = build_chunk_index(repo_root, output_root, args.chunk_lines, args.overlap_lines)
    output_path = output_root / "parsed" / "source-chunk-index.json"
    write_json(output_path, payload)
    print(
        json.dumps(
            {
                "source_chunk_index": str(output_path),
                "summary": payload["summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

