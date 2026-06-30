import re
from typing import Dict, List

from .base_extractor import BaseExtractor

_SKIP_NAMES = frozenset({
    "if", "while", "for", "switch", "catch", "try", "finally",
    "return", "new", "throw",
})

_METHOD_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|synchronized|native|abstract)\s+){1,6}"
    r"(?:@\w+\s+)?"                        # optional annotation on same line
    r"([\w<>\[\]?,\.]+)\s+"               # return type
    r"(\w+)\s*"                            # method name
    r"\(([^)]*)\)\s*"                      # parameters
    r"(?:throws\s+[\w\s,]+\s*)?"          # optional throws
    r"\{",
    re.MULTILINE,
)

_CLASS_RE = re.compile(
    r"(?:public|protected|private|abstract|final|static)?\s*"
    r"(class|interface|enum)\s+(\w+)",
    re.MULTILINE,
)


class JavaExtractor(BaseExtractor):

    def extract(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            return []

        artifacts: List[Dict] = []
        lines = content.split("\n")

        # Classes / interfaces / enums
        for m in _CLASS_RE.finditer(content):
            kind = m.group(1)
            name = m.group(2)
            artifacts.append(self.make_artifact(
                language="java",
                source_file=file_path,
                type=kind,
                name=name,
                content=f"{kind} {name}",
                metadata={"line_number": content[: m.start()].count("\n") + 1},
                is_business_artifact=(kind in ("class", "interface")),
                business_category="class_definition",
            ))

        # Methods
        for m in _METHOD_RE.finditer(content):
            return_type = m.group(1).strip()
            method_name = m.group(2)

            if method_name in _SKIP_NAMES:
                continue

            line_num = content[: m.start()].count("\n") + 1
            body_start = line_num - 1
            body = "\n".join(lines[body_start: min(body_start + 50, len(lines))])

            is_business = self.is_business_method(method_name)
            artifacts.append(self.make_artifact(
                language="java",
                source_file=file_path,
                type="method",
                name=method_name,
                content=body,
                metadata={
                    "return_type": return_type,
                    "line_number": line_num,
                },
                is_business_artifact=is_business,
                business_category=self.get_business_category(method_name),
            ))

        return artifacts
