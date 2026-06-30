import re
from pathlib import Path
from typing import Dict, List

from .base_extractor import BaseExtractor

# Keywords that look like method signatures but are control-flow
_SKIP_NAMES = frozenset({
    "if", "else", "while", "for", "foreach", "switch", "catch",
    "using", "lock", "try", "finally", "return", "new", "throw",
    "await", "yield", "var", "void", "int", "string", "bool",
    "get", "set",
})

# Access / modifier keywords used to recognise method declarations
_MODIFIERS = (
    "public", "private", "protected", "internal",
    "static", "virtual", "override", "abstract",
    "async", "sealed", "new", "extern", "readonly",
    "partial",
)
_MOD_RE = "|".join(_MODIFIERS)

# A C# method / constructor signature at the start of a (possibly indented) line:
#   [modifiers...] ReturnType MethodName(
_METHOD_LINE_RE = re.compile(
    r"^\s*(?:(?:" + _MOD_RE + r")\s+){1,7}"  # 1-7 modifiers
    r"([\w<>\[\]?,\.]+(?:\s*\?)?)\s+"          # return type (inc. nullable)
    r"(\w+)\s*"                                 # method name
    r"(?:<[^>]*>)?\s*"                          # optional generic params
    r"\(",                                      # opening paren
)

# class / struct
_CLASS_RE = re.compile(
    r"(?:public|internal|private|protected)?\s*"
    r"(?:abstract|sealed|static|partial)?\s*"
    r"(?:abstract|sealed|static|partial)?\s*"
    r"(class|struct)\s+(\w+)",
    re.MULTILINE,
)

# interface
_INTERFACE_RE = re.compile(
    r"(?:public|internal)?\s*interface\s+(\w+)",
    re.MULTILINE,
)

# enum  (captures name + body)
_ENUM_RE = re.compile(
    r"(?:public|internal|private)?\s*enum\s+(\w+)\s*\{([^}]+)\}",
    re.MULTILINE | re.DOTALL,
)

# namespace
_NS_RE = re.compile(r"namespace\s+([\w\.]+)", re.MULTILINE)

# Fix 2: [Authorize] attribute — captures optional args (Roles, Policy, etc.)
_AUTHORIZE_RE = re.compile(r"\[Authorize(?:\(([^)]*)\))?\]")

# Fix 3: constructor signature — modifiers then ClassName( with no return type
_CONSTRUCTOR_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static)\s+){1,4}"
    r"([A-Z]\w*)\s*"
    r"(?:<[^>]*>)?\s*"
    r"\(",
)

# Business-relevant property keywords
_BUSINESS_PROP_KEYWORDS = frozenset({
    "status", "state", "type", "amount", "price", "discount",
    "total", "quantity", "count", "limit", "threshold", "rate",
    "flag", "enabled", "active", "approved", "rejected", "pending",
    "balance", "credit", "tax", "fee",
})

# Service / business class suffixes
_SERVICE_SUFFIXES = (
    "Service", "Manager", "Handler", "Controller",
    "Processor", "Repository", "Factory", "Builder",
    "Validator", "Calculator", "Orchestrator",
)

# Property line pattern
_PROP_RE = re.compile(
    r"(?:public|private|protected|internal|static|virtual|override)\s+"
    r"(?:readonly\s+)?"
    r"([\w<>\[\]?,\.]+(?:\s*\?)?)\s+"
    r"(\w+)\s*\{[^}]*(?:get|set)",
    re.MULTILINE,
)


class DotNetExtractor(BaseExtractor):
    """Extracts business artefacts from C# (.cs) and VB.NET (.vb) files."""

    def extract(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            return []

        ext = Path(file_path).suffix.lower()
        if ext not in (".cs", ".vb"):
            return []

        namespace = self._get_namespace(content)
        artifacts: List[Dict] = []

        artifacts.extend(self._extract_classes(content, file_path, namespace))
        artifacts.extend(self._extract_interfaces(content, file_path, namespace))
        artifacts.extend(self._extract_enums(content, file_path, namespace))
        artifacts.extend(self._extract_methods(content, file_path, namespace))
        artifacts.extend(self._extract_business_properties(content, file_path, namespace))
        artifacts.extend(self._extract_authorize_rules(content, file_path, namespace))
        artifacts.extend(self._extract_constructor_guards(content, file_path, namespace))

        return artifacts

    # ── helpers ────────────────────────────────────────────────────────────────

    def _get_namespace(self, content: str) -> str:
        m = _NS_RE.search(content)
        return m.group(1) if m else ""

    def _extract_classes(self, content: str, file_path: str, ns: str) -> List[Dict]:
        artifacts = []
        for m in _CLASS_RE.finditer(content):
            ctype = m.group(1)   # "class" or "struct"
            cname = m.group(2)
            is_service = cname.endswith(_SERVICE_SUFFIXES)
            artifacts.append(self.make_artifact(
                language="dotnet",
                source_file=file_path,
                type=ctype,
                name=cname,
                content=f"{ctype} {cname}",
                metadata={"namespace": ns, "is_service_class": is_service},
                is_business_artifact=is_service,
                business_category="class_definition",
            ))
        return artifacts

    def _extract_interfaces(self, content: str, file_path: str, ns: str) -> List[Dict]:
        artifacts = []
        for m in _INTERFACE_RE.finditer(content):
            name = m.group(1)
            artifacts.append(self.make_artifact(
                language="dotnet",
                source_file=file_path,
                type="interface",
                name=name,
                content=f"interface {name}",
                metadata={"namespace": ns},
                is_business_artifact=True,
                business_category="contract_definition",
            ))
        return artifacts

    def _extract_enums(self, content: str, file_path: str, ns: str) -> List[Dict]:
        artifacts = []
        for m in _ENUM_RE.finditer(content):
            name = m.group(1)
            body = m.group(2)
            values = [
                v.strip().split("=")[0].strip()
                for v in body.split(",")
                if v.strip() and not v.strip().startswith("//")
            ]
            values = [v for v in values if v and re.match(r"^\w+$", v)]
            artifacts.append(self.make_artifact(
                language="dotnet",
                source_file=file_path,
                type="enum",
                name=name,
                content=m.group(0),
                metadata={"namespace": ns, "values": values},
                is_business_artifact=True,
                business_category="business_state",
            ))
        return artifacts

    def _extract_methods(self, content: str, file_path: str, ns: str) -> List[Dict]:
        artifacts = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            m = _METHOD_LINE_RE.match(line)
            if not m:
                continue

            return_type = m.group(1).strip()
            method_name = m.group(2)

            if method_name in _SKIP_NAMES:
                continue
            if not method_name[0].isalpha() and method_name[0] != "_":
                continue

            body = self._extract_body(lines, i)
            is_business = self.is_business_method(method_name)
            category = self.get_business_category(method_name)

            artifacts.append(self.make_artifact(
                language="dotnet",
                source_file=file_path,
                type="method",
                name=method_name,
                content=body,
                metadata={
                    "namespace": ns,
                    "return_type": return_type,
                    "line_number": i + 1,
                },
                is_business_artifact=is_business,
                business_category=category,
            ))

        return artifacts

    def _extract_business_properties(self, content: str, file_path: str, ns: str) -> List[Dict]:
        artifacts = []
        for m in _PROP_RE.finditer(content):
            prop_type = m.group(1).strip()
            prop_name = m.group(2)
            if any(kw in prop_name.lower() for kw in _BUSINESS_PROP_KEYWORDS):
                artifacts.append(self.make_artifact(
                    language="dotnet",
                    source_file=file_path,
                    type="property",
                    name=prop_name,
                    content=f"{prop_type} {prop_name}",
                    metadata={"namespace": ns, "property_type": prop_type},
                    is_business_artifact=True,
                    business_category="business_attribute",
                ))
        return artifacts

    def _extract_authorize_rules(self, content: str, file_path: str, ns: str) -> List[Dict]:
        """Fix 2: extract [Authorize] attributes as restriction artifacts."""
        artifacts = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            m = _AUTHORIZE_RE.search(line)
            if not m:
                continue

            args = (m.group(1) or "").strip()

            # Find the next meaningful line to identify what is being protected
            target_name = "Unknown"
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j].strip()
                if not next_line or next_line.startswith("[") or next_line.startswith("//"):
                    continue
                name_m = re.search(r"\b([A-Z]\w+)\s*(?:<[^>]*>)?\s*[\(:{]", next_line)
                if name_m:
                    target_name = name_m.group(1)
                break

            roles_match = re.search(r"Roles\s*=\s*[^\s,)]+", args)
            if roles_match:
                roles_str = roles_match.group(0)
                description = f"[Authorize({roles_str})] on {target_name}"
                statement = (
                    f"IF caller does not have required role ({roles_str})"
                    f" THEN deny access to {target_name}"
                )
            elif args:
                description = f"[Authorize({args})] on {target_name}"
                statement = (
                    f"IF caller is not authorized ({args})"
                    f" THEN deny access to {target_name}"
                )
            else:
                description = f"[Authorize] on {target_name}"
                statement = (
                    f"IF caller is not authenticated"
                    f" THEN deny access to {target_name}"
                )

            artifacts.append(self.make_artifact(
                language="dotnet",
                source_file=file_path,
                type="authorization_rule",
                name=f"Authorize_{target_name}",
                content=description,
                metadata={
                    "namespace": ns,
                    "authorize_args": args,
                    "target": target_name,
                    "line_number": i + 1,
                    "business_statement": statement,
                },
                is_business_artifact=True,
                business_category="restriction",
            ))

        return artifacts

    def _extract_constructor_guards(self, content: str, file_path: str, ns: str) -> List[Dict]:
        """Fix 3: extract constructors that contain Guard.Against.* as validation artifacts."""
        artifacts = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            m = _CONSTRUCTOR_RE.match(line)
            if not m:
                continue

            name = m.group(1)
            if name.lower() in _SKIP_NAMES:
                continue

            body = self._extract_body(lines, i)

            if "Guard.Against." not in body:
                continue

            guard_calls = re.findall(r"Guard\.Against\.(\w+)\(", body)

            artifacts.append(self.make_artifact(
                language="dotnet",
                source_file=file_path,
                type="constructor",
                name=f"{name}_constructor",
                content=body,
                metadata={
                    "namespace": ns,
                    "constructor_class": name,
                    "guard_checks": guard_calls,
                    "line_number": i + 1,
                },
                is_business_artifact=True,
                business_category="validation",
            ))

        return artifacts

    @staticmethod
    def _extract_body(lines: List[str], start: int, max_lines: int = 60) -> str:
        """Collect lines from start until matching closing brace (capped)."""
        body_lines = []
        brace_count = 0
        found_open = False
        end = min(start + max_lines, len(lines))

        for line in lines[start:end]:
            body_lines.append(line)
            brace_count += line.count("{") - line.count("}")
            if "{" in line:
                found_open = True
            if found_open and brace_count <= 0:
                break

        return "\n".join(body_lines)
