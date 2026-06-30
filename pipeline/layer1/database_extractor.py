import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

# ── SQL patterns ───────────────────────────────────────────────────────────────

_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:\[?(\w+)\]?\.)?"        # optional schema
    r"\[?(\w+)\]?\s*"            # table name
    r"\(([^;]{10,}?)\)"          # column block
    r"\s*(?:;|GO|ON\s+\[|\Z)",
    re.IGNORECASE | re.DOTALL,
)

_CREATE_PROC = re.compile(
    r"CREATE\s+(?:OR\s+(?:ALTER|REPLACE)\s+)?(?:PROCEDURE|PROC)\s+"
    r"(?:\[?(\w+)\]?\.)?"        # schema
    r"\[?(\w+)\]?",
    re.IGNORECASE,
)

_CREATE_TRIGGER = re.compile(
    r"CREATE\s+(?:OR\s+(?:ALTER|REPLACE)\s+)?TRIGGER\s+"
    r"(?:\[?(\w+)\]?\.)?"
    r"\[?(\w+)\]?\s+ON\s+\[?(\w+)\]?",
    re.IGNORECASE,
)

_CREATE_VIEW = re.compile(
    r"CREATE\s+(?:OR\s+(?:ALTER|REPLACE)\s+)?VIEW\s+"
    r"(?:\[?(\w+)\]?\.)?"
    r"\[?(\w+)\]?\s+AS",
    re.IGNORECASE,
)

_FK = re.compile(
    r"FOREIGN\s+KEY[^R]*REFERENCES\s+\[?(\w+)\]?",
    re.IGNORECASE,
)

# ── C# EF Core patterns ────────────────────────────────────────────────────────

_DBSET = re.compile(r"DbSet<(\w+)>", re.MULTILINE)
_EF_ENTITY = re.compile(r"modelBuilder\.Entity<(\w+)>", re.MULTILINE)
_TABLE_ATTR = re.compile(r'\[Table\(["\'](\w+)["\']\)\]')
_COLUMN_LINE = re.compile(
    r"\[?(\w+)\]?\s+([\w]+(?:\(\d+(?:,\s*\d+)?\))?)"
    r"(?:\s+(NOT\s+NULL|NULL))?"
    r"(?:\s+(PRIMARY\s+KEY|IDENTITY|UNIQUE))?",
    re.IGNORECASE,
)

# File extensions considered SQL scripts
_SQL_EXTS = {".sql", ".ddl", ".dml", ".prc", ".trg", ".vw", ".fnc", ".pkb", ".pks"}


class DatabaseExtractor:
    """Extracts database objects from SQL scripts and EF Core C# files."""

    def extract(self, files: List[str], root_path: str) -> Dict:
        results: Dict = {
            "tables": [],
            "stored_procedures": [],
            "triggers": [],
            "views": [],
            "relationships": [],
            "ef_entities": [],
            "db_contexts": [],
        }

        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext in _SQL_EXTS:
                self._from_sql(file_path, results)
            elif ext == ".cs":
                self._from_csharp(file_path, results)

        return results

    # ── SQL ────────────────────────────────────────────────────────────────────

    def _from_sql(self, file_path: str, results: Dict):
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        for m in _CREATE_TABLE.finditer(content):
            schema = m.group(1) or "dbo"
            name = m.group(2)
            col_block = m.group(3)
            results["tables"].append({
                "name": name,
                "schema": schema,
                "columns": self._parse_columns(col_block),
                "source_file": file_path,
                "ddl": m.group(0)[:1500],
            })

        for m in _CREATE_PROC.finditer(content):
            results["stored_procedures"].append({
                "name": m.group(2),
                "schema": m.group(1) or "dbo",
                "source_file": file_path,
            })

        for m in _CREATE_TRIGGER.finditer(content):
            results["triggers"].append({
                "name": m.group(2),
                "on_table": m.group(3),
                "source_file": file_path,
            })

        for m in _CREATE_VIEW.finditer(content):
            results["views"].append({
                "name": m.group(2),
                "schema": m.group(1) or "dbo",
                "source_file": file_path,
            })

        for m in _FK.finditer(content):
            results["relationships"].append({
                "references_table": m.group(1),
                "source_file": file_path,
            })

    # ── C# EF Core ─────────────────────────────────────────────────────────────

    def _from_csharp(self, file_path: str, results: Dict):
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        # DbContext file detection
        if "DbContext" in content:
            entities = list({m.group(1) for m in _DBSET.finditer(content)})
            entities += [
                m.group(1) for m in _EF_ENTITY.finditer(content)
                if m.group(1) not in entities
            ]
            if entities:
                results["db_contexts"].append({
                    "file": file_path,
                    "entities": entities,
                })
                for entity in entities:
                    results["ef_entities"].append({
                        "entity_name": entity,
                        "source_file": file_path,
                        "type": "ef_entity",
                    })

        # Data annotation tables ([Table("...")])
        for m in _TABLE_ATTR.finditer(content):
            results["tables"].append({
                "name": m.group(1),
                "source_file": file_path,
                "source": "data_annotation",
                "columns": [],
            })

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_columns(col_block: str) -> List[Dict]:
        columns = []
        skip_starts = ("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "INDEX", "KEY")

        for raw_line in col_block.split("\n"):
            line = raw_line.strip().rstrip(",")
            if not line or line.upper().startswith(skip_starts):
                continue

            m = _COLUMN_LINE.match(line)
            if m:
                col_name = m.group(1)
                if col_name.upper() in ("GO", "END", "BEGIN"):
                    continue
                columns.append({
                    "name": col_name,
                    "type": m.group(2),
                    "nullable": "NOT NULL" not in (m.group(3) or "").upper(),
                    "is_primary_key": bool(
                        re.search(r"PRIMARY\s+KEY|IDENTITY", m.group(4) or "", re.IGNORECASE)
                    ),
                })

        return columns
