import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class OutputSaver:
    """
    Step 8 — serialize all cleaned extraction results to JSON files
    and produce an extraction_summary.json.
    """

    def save(self, cleaned: Dict, output_dir: str, metadata: Dict) -> Dict:
        os.makedirs(output_dir, exist_ok=True)
        saved: Dict[str, str] = {}

        file_map = {
            "source_code": "source_code.json",
            "database": "database.json",
            "config": "config.json",
            "logs": "logs.json",
        }

        for key, filename in file_map.items():
            if key in cleaned:
                saved[key] = self._write(cleaned[key], output_dir, filename)

        summary = self._build_summary(cleaned, metadata, saved)
        saved["summary"] = self._write(summary, output_dir, "extraction_summary.json")

        return {"saved_files": saved, "summary": summary}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _write(self, data: Any, output_dir: str, filename: str) -> str:
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
        size_kb = os.path.getsize(path) / 1024
        print(f"  {filename:<35} {size_kb:>7.1f} KB")
        return path

    def _build_summary(
        self, cleaned: Dict, metadata: Dict, saved: Dict
    ) -> Dict:
        source = cleaned.get("source_code", [])
        db = cleaned.get("database", {})
        cfg = cleaned.get("config", {})
        logs = cleaned.get("logs", {})

        methods = [a for a in source if a.get("type") == "method"]
        classes = [a for a in source if a.get("type") in ("class", "struct")]
        interfaces = [a for a in source if a.get("type") == "interface"]
        enums = [a for a in source if a.get("type") == "enum"]
        business = [a for a in source if a.get("is_business_artifact")]

        db_count = sum(
            len(db.get(k, []))
            for k in ("tables", "stored_procedures", "triggers", "views", "ef_entities")
        )

        categories: Dict[str, int] = {}
        for a in business:
            cat = a.get("business_category", "general")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "extraction_date": datetime.now(timezone.utc).isoformat(),
            "source": metadata.get("original_source", ""),
            "source_type": metadata.get("source_type", ""),
            "language": metadata.get("language", ""),
            "total_methods": len(methods),
            "total_classes": len(classes),
            "total_interfaces": len(interfaces),
            "total_enums": len(enums),
            "total_business_artifacts": len(business),
            "total_db_objects": db_count,
            "total_config_params": len(cfg.get("all_params", [])),
            "total_business_params": len(cfg.get("business_params", [])),
            "total_feature_flags": len(cfg.get("feature_flags", [])),
            "log_events_found": len(logs.get("business_events", [])),
            "process_sequences": len(logs.get("process_sequences", [])),
            "business_categories": categories,
            "output_files": saved,
            "ready_for_layer2": True,
        }
