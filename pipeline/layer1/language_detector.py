import os
from collections import Counter
from pathlib import Path
from typing import Dict, List


class LanguageDetector:

    # Maps file extension → logical language name used by extractor map
    EXTENSION_MAP: Dict[str, str] = {
        ".cs": "dotnet",
        ".vb": "dotnet",
        ".csproj": "dotnet",
        ".vbproj": "dotnet",
        ".sln": "dotnet",
        ".java": "java",
        ".py": "python",
        ".js": "javascript",
        ".ts": "javascript",
        ".jsx": "javascript",
        ".tsx": "javascript",
        ".cbl": "cobol",
        ".cob": "cobol",
        ".cpy": "cobol",
        ".php": "php",
        ".rb": "ruby",
        ".go": "go",
        ".kt": "kotlin",
        ".swift": "swift",
        ".rs": "rust",
    }

    # A language must account for at least this % of code files to be included
    THRESHOLD_PERCENT = 5

    # Directories to skip during detection scan
    _SKIP_DIRS = {
        "node_modules", "vendor", "__pycache__", "dist", "build",
        "bin", "obj", ".git", ".svn", ".idea", ".vs",
    }

    def detect(self, local_path: str) -> dict:
        """
        Walk the directory, count files per language, return:
            primary_language   – the dominant language
            languages          – {lang: percentage} for all detected
            extractors_to_use  – languages above THRESHOLD_PERCENT
            total_code_files   – raw count of recognised source files
        """
        lang_counts: Counter = Counter()
        total = 0

        for root, dirs, files in os.walk(local_path):
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                ext = Path(fname).suffix.lower()
                lang = self.EXTENSION_MAP.get(ext)
                if lang:
                    lang_counts[lang] += 1
                    total += 1

        if total == 0:
            return {
                "primary_language": "unknown",
                "languages": {},
                "extractors_to_use": [],
                "total_code_files": 0,
            }

        percentages = {
            lang: round(count / total * 100, 1)
            for lang, count in lang_counts.items()
        }

        primary = lang_counts.most_common(1)[0][0]

        extractors = [
            lang for lang, pct in percentages.items()
            if pct >= self.THRESHOLD_PERCENT
        ]
        if not extractors:
            extractors = [primary]

        return {
            "primary_language": primary,
            "languages": percentages,
            "extractors_to_use": extractors,
            "total_code_files": total,
        }
