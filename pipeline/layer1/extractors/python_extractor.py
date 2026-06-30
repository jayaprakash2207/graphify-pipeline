import ast
from typing import Dict, List

from .base_extractor import BaseExtractor


class PythonExtractor(BaseExtractor):
    """Uses Python's built-in ast module for accurate parsing."""

    def extract(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                source = fh.read()
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            return []

        lines = source.split("\n")
        artifacts: List[Dict] = []

        for node in ast.walk(tree):
            # Classes
            if isinstance(node, ast.ClassDef):
                artifacts.append(self.make_artifact(
                    language="python",
                    source_file=file_path,
                    type="class",
                    name=node.name,
                    content=f"class {node.name}",
                    metadata={"line_number": node.lineno},
                    is_business_artifact=True,
                    business_category="class_definition",
                ))

            # Functions and methods
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                docstring = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]

                start = node.lineno - 1
                body_lines = lines[start: min(start + 50, len(lines))]
                content = "\n".join(body_lines)

                is_business = self.is_business_method(name)
                artifacts.append(self.make_artifact(
                    language="python",
                    source_file=file_path,
                    type="method",
                    name=name,
                    content=content,
                    metadata={
                        "line_number": node.lineno,
                        "args": args,
                        "docstring": docstring[:300],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    },
                    is_business_artifact=is_business,
                    business_category=self.get_business_category(name),
                ))

        return artifacts
