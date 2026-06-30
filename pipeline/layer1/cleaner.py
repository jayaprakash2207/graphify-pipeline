import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class Cleaner:
    """
    Step 7 — clean, deduplicate, normalize, and tag all extracted artifacts
    before they are saved to disk.
    """

    def clean_and_tag(
        self, raw: Dict, root_path: str, language: str
    ) -> Dict:
        ts = datetime.now(timezone.utc).isoformat()
        return {
            "source_code": self._clean_artifacts(
                raw.get("source_code", []), root_path, ts
            ),
            "database": self._clean_db(raw.get("database", {}), root_path, ts),
            "config": self._clean_config(raw.get("config", {}), ts),
            "logs": self._tag_dict(raw.get("logs", {}), ts),
        }

    # ── source code ───────────────────────────────────────────────────────────

    def _clean_artifacts(
        self, artifacts: List[Dict], root_path: str, ts: str
    ) -> List[Dict]:
        seen: set = set()
        cleaned: List[Dict] = []

        for a in artifacts:
            name = (a.get("name") or "").strip()
            content = (a.get("content") or "").strip()

            if not name or not content or len(content) < 10:
                continue

            h = hashlib.md5(f"{name}|{content}".encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)

            a["name"] = name
            a["content"] = self._normalize_text(content)
            a["source_file"] = self._relative(a.get("source_file", ""), root_path)
            a["extraction_timestamp"] = ts
            a["content_hash"] = h

            if "metadata" not in a:
                a["metadata"] = {}

            cleaned.append(a)

        return cleaned

    # ── database ──────────────────────────────────────────────────────────────

    def _clean_db(self, db: Dict, root_path: str, ts: str) -> Dict:
        cleaned: Dict = {}
        for key, items in db.items():
            if not isinstance(items, list):
                cleaned[key] = items
                continue
            seen: set = set()
            unique: List[Dict] = []
            for item in items:
                name = item.get("name") or item.get("entity_name", "")
                if name and name not in seen:
                    seen.add(name)
                    item["extraction_timestamp"] = ts
                    if "source_file" in item:
                        item["source_file"] = self._relative(
                            item["source_file"], root_path
                        )
                    unique.append(item)
            cleaned[key] = unique
        return cleaned

    # ── config ────────────────────────────────────────────────────────────────

    def _clean_config(self, config: Dict, ts: str) -> Dict:
        cleaned: Dict = {}
        for key, items in config.items():
            if not isinstance(items, list):
                cleaned[key] = items
                continue
            tagged = []
            for item in items:
                item["extraction_timestamp"] = ts
                tagged.append(item)
            cleaned[key] = tagged
        return cleaned

    # ── generic ───────────────────────────────────────────────────────────────

    def _tag_dict(self, d: Dict, ts: str) -> Dict:
        d["extraction_timestamp"] = ts
        return d

    # ── utils ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _relative(file_path: str, root_path: str) -> str:
        if not file_path or not root_path:
            return file_path
        try:
            return str(Path(file_path).relative_to(root_path)).replace("\\", "/")
        except ValueError:
            return file_path

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return "\n".join(line.rstrip() for line in text.split("\n"))
