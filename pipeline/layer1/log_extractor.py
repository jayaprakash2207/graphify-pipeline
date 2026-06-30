import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

_LOG_EXTS = {".log", ".out", ".err"}

# Business-level action words found in log lines
_ACTION_RE = re.compile(
    r"\b(Created|Updated|Deleted|Approved|Rejected|Validated|Processed|"
    r"Submitted|Confirmed|Cancelled|Completed|Failed|Started|Finished|"
    r"Authenticated|Authorized|Registered|Assigned|Dispatched|Sent|"
    r"Imported|Exported|Synced|Calculated|Charged|Refunded|Allocated)\b",
    re.IGNORECASE,
)

_LOG_LEVEL_RE = re.compile(
    r"\b(INFO|DEBUG|WARN|WARNING|ERROR|FATAL|TRACE|CRITICAL)\b",
    re.IGNORECASE,
)

_ERROR_RE = re.compile(
    r"\b(ERROR|EXCEPTION|FATAL|CRITICAL|UNHANDLED)\b",
    re.IGNORECASE,
)

_MAX_FILES = 10
_MAX_LINES_PER_FILE = 5000


class LogExtractor:
    """
    Mines transaction logs for business event patterns and process sequences.
    Caps file and line counts to keep runtime bounded.
    """

    def extract(self, files: List[str], root_path: str) -> Dict:
        results: Dict = {
            "log_files_found": [],
            "business_events": [],
            "error_patterns": [],
            "process_sequences": [],
        }

        log_files = [f for f in files if Path(f).suffix.lower() in _LOG_EXTS]

        for log_file in log_files[:_MAX_FILES]:
            results["log_files_found"].append(log_file)
            self._mine_file(log_file, results)

        if results["business_events"]:
            results["process_sequences"] = self._mine_sequences(results["business_events"])

        return results

    # ── helpers ───────────────────────────────────────────────────────────────

    def _mine_file(self, file_path: str, results: Dict):
        try:
            lines = Path(file_path).read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines()[:_MAX_LINES_PER_FILE]
        except OSError:
            return

        for line in lines:
            line = line.strip()
            if not line:
                continue

            action_m = _ACTION_RE.search(line)
            if action_m:
                level_m = _LOG_LEVEL_RE.search(line)
                results["business_events"].append({
                    "action": action_m.group(1).upper(),
                    "log_level": level_m.group(1).upper() if level_m else "INFO",
                    "raw_line": line[:200],
                    "source_file": file_path,
                })

            if _ERROR_RE.search(line):
                results["error_patterns"].append({
                    "line": line[:200],
                    "source_file": file_path,
                })

    @staticmethod
    def _mine_sequences(events: List[Dict], top_n: int = 15) -> List[Dict]:
        transitions: Dict[str, int] = defaultdict(int)

        for i in range(1, len(events)):
            transition = f"{events[i-1]['action']} → {events[i]['action']}"
            transitions[transition] += 1

        ranked = sorted(transitions.items(), key=lambda x: x[1], reverse=True)
        return [
            {"sequence": seq, "frequency": freq}
            for seq, freq in ranked[:top_n]
        ]
