import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


# Config file names we always process regardless of directory depth
_CONFIG_NAMES = {
    "appsettings.json", "appsettings.development.json",
    "appsettings.production.json", "appsettings.staging.json",
    "appsettings.test.json", "appsettings.local.json",
    "web.config", "app.config",
    "settings.json", "configuration.json", "config.json",
    ".env", ".env.development", ".env.production", ".env.staging",
    "application.properties", "application.yml", "application.yaml",
    "bootstrap.yml", "bootstrap.yaml",
}

# Key fragments that signal a business-relevant parameter
_BUSINESS_KEYWORDS = {
    "max", "min", "limit", "threshold", "rate", "percent", "percentage",
    "approval", "discount", "tax", "fee", "timeout", "retry", "attempt",
    "enable", "disable", "flag", "active", "allowed", "blocked",
    "price", "cost", "amount", "balance", "credit", "debit",
    "expiry", "expire", "days", "hours", "period",
    "role", "permission", "access", "level", "tier",
    "batch", "size", "count", "capacity", "quota",
    "smtp", "email", "notify", "alert",
}

# Keys whose values should be redacted
_SENSITIVE_KEYWORDS = {
    "password", "secret", "key", "token", "credential",
    "pwd", "pass", "auth", "private", "certificate", "cert",
    "apikey", "api_key", "connectionstring",
}


class ConfigExtractor:
    """Extracts business parameters from config files of all common formats."""

    def extract(self, files: List[str]) -> Dict:
        results: Dict = {
            "all_params": [],
            "business_params": [],
            "connection_strings": [],
            "feature_flags": [],
            "role_definitions": [],
        }

        for file_path in files:
            name_lower = Path(file_path).name.lower()
            ext = Path(file_path).suffix.lower()

            is_config = (
                name_lower in _CONFIG_NAMES
                or ext in {".json", ".xml", ".yml", ".yaml", ".properties", ".config"}
                or name_lower.startswith(".env")
            )
            if is_config:
                self._process(file_path, results)

        return results

    # ── routing ───────────────────────────────────────────────────────────────

    def _process(self, file_path: str, results: Dict):
        name_lower = Path(file_path).name.lower()
        ext = Path(file_path).suffix.lower()

        try:
            if ext == ".json" or name_lower.startswith("appsettings"):
                self._from_json(file_path, results)
            elif ext in {".xml", ".config"} or name_lower in {"web.config", "app.config"}:
                self._from_xml(file_path, results)
            elif ext in {".yml", ".yaml"}:
                self._from_yaml(file_path, results)
            elif name_lower.startswith(".env") or ext == ".env":
                self._from_env(file_path, results)
            elif ext == ".properties":
                self._from_properties(file_path, results)
        except Exception:
            pass   # skip unparseable files silently

    # ── parsers ───────────────────────────────────────────────────────────────

    def _from_json(self, file_path: str, results: Dict):
        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            return
        self._ingest_params(self._flatten(data, source_file=file_path), results)

    def _from_xml(self, file_path: str, results: Dict):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError:
            return

        for elem in root.iter("add"):
            key = elem.get("key") or elem.get("name")
            value = elem.get("value") or elem.get("connectionString", "")
            if key:
                param = self._make_param(key, value, file_path, "xml")
                results["all_params"].append(param)
                self._classify(param, results)

        for conn in root.iter("connectionStrings"):
            for add in conn:
                name = add.get("name", "")
                cs = add.get("connectionString", "")
                if name:
                    p = self._make_param(name, cs, file_path, "connection_string")
                    results["connection_strings"].append(p)

    def _from_yaml(self, file_path: str, results: Dict):
        try:
            import yaml
            data = yaml.safe_load(
                Path(file_path).read_text(encoding="utf-8", errors="ignore")
            )
        except Exception:
            return
        if isinstance(data, dict):
            self._ingest_params(self._flatten(data, source_file=file_path), results)

    def _from_env(self, file_path: str, results: Dict):
        try:
            lines = Path(file_path).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            param = self._make_param(key.strip(), value.strip().strip("\"'"), file_path, "env")
            results["all_params"].append(param)
            self._classify(param, results)

    def _from_properties(self, file_path: str, results: Dict):
        try:
            lines = Path(file_path).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            param = self._make_param(key.strip(), value.strip(), file_path, "properties")
            results["all_params"].append(param)
            self._classify(param, results)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _ingest_params(self, params: List[Dict], results: Dict):
        for p in params:
            results["all_params"].append(p)
            self._classify(p, results)

    def _classify(self, param: Dict, results: Dict):
        key_lower = param["key"].lower().replace(".", "").replace("-", "").replace("_", "")

        if any(kw in key_lower for kw in _BUSINESS_KEYWORDS):
            results["business_params"].append(param)

        if "connectionstring" in key_lower or "datasource" in key_lower:
            results["connection_strings"].append(param)

        if any(kw in key_lower for kw in {"enable", "feature", "flag", "toggle", "isenabled"}):
            results["feature_flags"].append(param)

        if any(kw in key_lower for kw in {"role", "permission", "access", "policy"}):
            results["role_definitions"].append(param)

    @staticmethod
    def _make_param(key: str, value: str, source_file: str, source_type: str) -> Dict:
        key_lower = key.lower().replace("_", "").replace("-", "")
        if any(kw in key_lower for kw in _SENSITIVE_KEYWORDS):
            value = "***REDACTED***"
        return {
            "key": key,
            "value": str(value) if value is not None else "",
            "source_file": source_file,
            "source_type": source_type,
        }

    @staticmethod
    def _flatten(data: Any, prefix: str = "", source_file: str = "") -> List[Dict]:
        params: List[Dict] = []
        if isinstance(data, dict):
            for k, v in data.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    params.extend(ConfigExtractor._flatten(v, full_key, source_file))
                else:
                    key_lower = full_key.lower().replace("_", "").replace("-", "")
                    val = str(v) if v is not None else ""
                    if any(kw in key_lower for kw in _SENSITIVE_KEYWORDS):
                        val = "***REDACTED***"
                    params.append({
                        "key": full_key,
                        "value": val,
                        "source_file": source_file,
                        "source_type": "json",
                    })
        elif isinstance(data, list):
            for i, item in enumerate(data):
                params.extend(ConfigExtractor._flatten(item, f"{prefix}[{i}]", source_file))
        return params
