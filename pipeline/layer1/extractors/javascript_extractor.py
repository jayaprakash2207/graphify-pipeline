import re
from typing import Dict, List

from .base_extractor import BaseExtractor

_SKIP_NAMES = frozenset({
    "if", "while", "for", "switch", "catch", "then",
    "map", "filter", "reduce", "forEach", "find",
})

# Patterns that cover the main JS/TS function declaration styles
_PATTERNS = [
    # function name(...)  or  async function name(...)
    re.compile(r"(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE),
    # const/let/var name = (async)? (...) =>  or  name = function(...)
    re.compile(
        r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*"
        r"(?:async\s+)?(?:function\s*\([^)]*\)|\([^)]*\)\s*=>|[^=\n]+=>)",
        re.MULTILINE,
    ),
    # name: function(...)  or  name: async function(...)
    re.compile(r"(\w+)\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*\{", re.MULTILINE),
    # class ClassName
    re.compile(r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
]


class JavaScriptExtractor(BaseExtractor):
    """Extracts functions and classes from JavaScript and TypeScript files."""

    def extract(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            return []

        artifacts: List[Dict] = []
        seen: set = set()

        for pattern in _PATTERNS:
            for m in pattern.finditer(content):
                name = m.group(1)

                if name in _SKIP_NAMES or name in seen:
                    continue
                seen.add(name)

                line_num = content[: m.start()].count("\n") + 1
                # grab up to 30 lines of context
                start_line = line_num - 1
                snippet_lines = content.split("\n")[start_line: start_line + 30]
                snippet = "\n".join(snippet_lines)

                is_class = "class" in m.group(0).split(name)[0]
                artifact_type = "class" if is_class else "function"
                is_business = self.is_business_method(name)

                artifacts.append(self.make_artifact(
                    language="javascript",
                    source_file=file_path,
                    type=artifact_type,
                    name=name,
                    content=snippet,
                    metadata={"line_number": line_num},
                    is_business_artifact=is_business,
                    business_category=self.get_business_category(name),
                ))

        return artifacts
