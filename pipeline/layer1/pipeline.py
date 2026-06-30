from typing import Optional

from .input_resolver import InputResolver
from .language_detector import LanguageDetector
from .file_filter import FileFilter
from .extractors.dotnet_extractor import DotNetExtractor
from .extractors.java_extractor import JavaExtractor
from .extractors.python_extractor import PythonExtractor
from .extractors.javascript_extractor import JavaScriptExtractor
from .database_extractor import DatabaseExtractor
from .config_extractor import ConfigExtractor
from .log_extractor import LogExtractor
from .cleaner import Cleaner
from .output_saver import OutputSaver

EXTRACTOR_MAP = {
    "dotnet": DotNetExtractor,
    "java": JavaExtractor,
    "python": PythonExtractor,
    "javascript": JavaScriptExtractor,
}


class Layer1Pipeline:

    def __init__(
        self,
        source: str,
        output_dir: str = "output",
        git_token: Optional[str] = None,
        app_url: Optional[str] = None,
    ):
        self.source = source
        self.output_dir = output_dir
        self.git_token = git_token
        self.app_url = app_url

    def run(self, keep_source: bool = False) -> dict:
        resolved = None
        try:
            resolved, result = self._execute()
            return result
        except Exception as e:
            if resolved and resolved.get("temp_dir"):
                InputResolver().cleanup(resolved)
            return {"success": False, "error": str(e)}
        finally:
            # When keep_source=True the caller is responsible for cleanup
            if not keep_source and resolved and resolved.get("temp_dir"):
                InputResolver().cleanup(resolved)

    def _execute(self):
        # ── Step 0: Resolve input ─────────────────────────────────────────────
        print("[Step 0] Resolving input source...")
        resolver = InputResolver()
        resolved = resolver.resolve(self.source, self.git_token)
        local_path = resolved["local_path"]
        print(f"         source_type : {resolved['source_type']}")
        print(f"         local_path  : {local_path}")

        # ── Step 1: Detect language ───────────────────────────────────────────
        print("\n[Step 1] Detecting language(s)...")
        detector = LanguageDetector()
        detection = detector.detect(local_path)
        primary_language = detection["primary_language"]
        print(f"         primary     : {primary_language}")
        print(f"         all found   : {detection['languages']}")
        print(f"         extractors  : {detection['extractors_to_use']}")

        # ── Step 2: Filter files ──────────────────────────────────────────────
        print("\n[Step 2] Filtering files...")
        file_filter = FileFilter()
        all_files = file_filter.filter(local_path)
        print(f"         files kept  : {len(all_files)}")

        # ── Step 3: Extract source code ───────────────────────────────────────
        print("\n[Step 3] Extracting source code...")
        all_source_artifacts = []

        for lang in detection["extractors_to_use"]:
            extractor_class = EXTRACTOR_MAP.get(lang)
            if not extractor_class:
                print(f"         no extractor for: {lang} - skipping")
                continue

            lang_files = file_filter.filter_by_language(all_files, lang)
            print(f"         {lang}: {len(lang_files)} files to parse")

            extractor = extractor_class()
            artifacts = extractor.extract_all(lang_files)
            all_source_artifacts.extend(artifacts)

            business_count = sum(1 for a in artifacts if a.get("is_business_artifact"))
            print(f"         {lang}: {len(artifacts)} artifacts ({business_count} business)")

        # ── Step 4: Extract database ──────────────────────────────────────────
        print("\n[Step 4] Extracting database objects...")
        db_extractor = DatabaseExtractor()
        db_results = db_extractor.extract(all_files, local_path)
        print(f"         tables      : {len(db_results.get('tables', []))}")
        print(f"         procedures  : {len(db_results.get('stored_procedures', []))}")
        print(f"         triggers    : {len(db_results.get('triggers', []))}")
        print(f"         views       : {len(db_results.get('views', []))}")
        print(f"         EF entities : {len(db_results.get('ef_entities', []))}")

        # ── Step 5: Extract config ────────────────────────────────────────────
        print("\n[Step 5] Extracting configuration parameters...")
        config_extractor = ConfigExtractor()
        config_results = config_extractor.extract(all_files)
        print(f"         all params       : {len(config_results.get('all_params', []))}")
        print(f"         business params  : {len(config_results.get('business_params', []))}")
        print(f"         feature flags    : {len(config_results.get('feature_flags', []))}")
        print(f"         conn strings     : {len(config_results.get('connection_strings', []))}")

        # ── Step 6: Extract logs ──────────────────────────────────────────────
        print("\n[Step 6] Extracting logs & reports...")
        log_extractor = LogExtractor()
        log_results = log_extractor.extract(all_files, local_path)
        print(f"         log files        : {len(log_results.get('log_files_found', []))}")
        print(f"         business events  : {len(log_results.get('business_events', []))}")
        print(f"         process sequences: {len(log_results.get('process_sequences', []))}")

        # ── Step 7: Clean & normalize ─────────────────────────────────────────
        print("\n[Step 7] Cleaning and normalizing...")
        cleaner = Cleaner()
        raw_results = {
            "source_code": all_source_artifacts,
            "database": db_results,
            "config": config_results,
            "logs": log_results,
        }
        cleaned_data = cleaner.clean_and_tag(raw_results, local_path, primary_language)
        cleaned_source = cleaned_data.get("source_code", [])
        print(f"         artifacts after clean : {len(cleaned_source)}")

        # ── Step 8: Save to files ─────────────────────────────────────────────
        print(f"\n[Step 8] Saving to {self.output_dir}/...")
        saver = OutputSaver()
        metadata = {
            "original_source": self.source,
            "source_type": resolved["source_type"],
            "language": primary_language,
        }
        save_result = saver.save(cleaned_data, self.output_dir, metadata)

        return resolved, {
            "success": True,
            "output_dir": self.output_dir,
            "summary": save_result["summary"],
            "local_path": str(local_path),
            "temp_dir": resolved.get("temp_dir"),
        }
