import os
from pathlib import Path
from typing import List, Set


class FileFilter:

    # Directory names that are always excluded
    EXCLUDED_DIRS: Set[str] = {
        # Build outputs
        "bin", "obj", "dist", "build", "out", "target", "release", "debug",
        "publish", "artifacts",
        # Package caches / vendor
        "node_modules", "vendor", "packages", ".nuget", "bower_components",
        # IDE / tooling
        ".vs", ".idea", ".vscode", ".git", ".svn", ".hg",
        # Generated / scaffolded
        "migrations", "generated", "auto-generated", "scaffolded",
        "efmigrations", "databasemigrations",
        # Test result artefacts (not test source)
        "testresults", "coverage", ".testresults", "testoutput",
        # Misc transient
        "__pycache__", "temp", "tmp", "cache", ".cache",
        "logs", "log",
        # BA Pipeline's own output dirs (if a previous run wrote into the source tree)
        "da-outputs", "ba_documents", "aa-outputs", "architecture-output",
        "evidence-packs", "llm-stages",
    }

    # Directory name fragments that indicate test projects (lowercased)
    TEST_DIR_FRAGMENTS: Set[str] = {
        "test", "tests", "spec", "specs",
        "unittest", "unittests",
        "integrationtest", "integrationtests",
        "e2etest", "e2etests", "functionaltest",
    }

    # File suffixes / exact names to always exclude
    EXCLUDED_SUFFIXES: Set[str] = {
        # Compiled / binary
        ".exe", ".dll", ".pdb", ".lib", ".obj", ".o", ".a", ".so", ".dylib",
        # Minified web assets
        ".min.js", ".min.css", ".bundle.js",
        # IDE metadata
        ".suo", ".user", ".userosscache", ".userprefs",
        # Lock files (content not useful for BA)
        ".lock",
        # Media / binary assets
        ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".bmp", ".tiff",
        ".pdf", ".docx", ".xlsx", ".pptx",
        # Archives
        ".zip", ".tar", ".gz", ".rar", ".7z",
        # C# generated/designer files
        ".designer.cs", ".g.cs", ".g.i.cs", ".designer.vb",
    }

    EXCLUDED_FILENAMES: Set[str] = {
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "packages.lock.json",
        "composer.lock",
        "Gemfile.lock",
        "desktop.ini",
        "thumbs.db",
        ".ds_store",
    }

    # ── public API ─────────────────────────────────────────────────────────────

    def filter(self, local_path: str, include_tests: bool = False) -> List[str]:
        """
        Walk local_path and return the list of source files that should be
        processed, excluding build artefacts, generated files, IDE metadata,
        and (by default) test projects.
        """
        kept: List[str] = []

        for root, dirs, files in os.walk(local_path):
            dirs[:] = [
                d for d in dirs
                if self._keep_dir(d, include_tests)
            ]

            for fname in files:
                if self._keep_file(fname):
                    kept.append(os.path.join(root, fname))

        return kept

    def filter_by_language(self, files: List[str], language: str) -> List[str]:
        """Return only files that belong to the given language extractor."""
        lang_extensions: dict = {
            "dotnet": {".cs", ".vb"},
            "java": {".java"},
            "python": {".py"},
            "javascript": {".js", ".ts", ".jsx", ".tsx"},
            "cobol": {".cbl", ".cob", ".cpy"},
        }
        exts = lang_extensions.get(language, set())
        return [f for f in files if Path(f).suffix.lower() in exts]

    # ── private helpers ────────────────────────────────────────────────────────

    def _keep_dir(self, name: str, include_tests: bool) -> bool:
        lower = name.lower()

        if lower in self.EXCLUDED_DIRS:
            return False

        if not include_tests:
            for fragment in self.TEST_DIR_FRAGMENTS:
                if fragment in lower:
                    return False

        return True

    def _keep_file(self, fname: str) -> bool:
        lower = fname.lower()

        if lower in self.EXCLUDED_FILENAMES:
            return False

        # Check suffix-based exclusions (longest match wins for compound exts)
        for suffix in self.EXCLUDED_SUFFIXES:
            if lower.endswith(suffix):
                return False

        return True
