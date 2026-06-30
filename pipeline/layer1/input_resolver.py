import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Optional


class InputResolver:

    # Patterns that identify a git remote URL by provider
    _GIT_PROVIDERS = {
        "github": re.compile(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+"),
        "gitlab": re.compile(r"https?://gitlab\.com/[\w\-\.]+/[\w\-\.]+"),
        "bitbucket": re.compile(r"https?://bitbucket\.org/[\w\-\.]+/[\w\-\.]+"),
        "azure_devops": re.compile(
            r"https?://dev\.azure\.com/[\w\-\.]+/[\w\-\.]+/_git/[\w\-\.]+"
        ),
    }

    def resolve(self, source: str, git_token: Optional[str] = None) -> dict:
        """
        Accepts a git URL, local folder path, or .zip path.
        Returns a dict with keys:
            local_path   – where the code lives on disk
            source_type  – 'github' | 'gitlab' | 'bitbucket' | 'azure_devops'
                           | 'git' | 'local' | 'zip'
            original_source – the raw string the user gave
            temp_dir     – temp directory created (caller must call cleanup()),
                           or None if we used an existing path
        """
        source = source.strip()

        provider = self._detect_provider(source)
        if provider:
            return self._clone_repo(source, provider, git_token)

        if source.lower().endswith(".zip") and os.path.isfile(source):
            return self._extract_zip(source)

        if os.path.isdir(source):
            return {
                "local_path": str(Path(source).resolve()),
                "source_type": "local",
                "original_source": source,
                "temp_dir": None,
            }

        raise ValueError(
            f"Cannot resolve source: '{source}'\n"
            "Expected: a git URL, a local folder path, or a .zip file path."
        )

    # ── private helpers ────────────────────────────────────────────────────────

    def _detect_provider(self, source: str) -> Optional[str]:
        for provider, pattern in self._GIT_PROVIDERS.items():
            if pattern.match(source):
                return provider
        # Catch generic HTTPS git URLs (self-hosted GitLab, Gitea, etc.)
        if source.startswith(("http://", "https://")) and "/" in source.split("://", 1)[1]:
            return "git"
        return None

    def _clone_repo(self, url: str, provider: str, git_token: Optional[str]) -> dict:
        temp_dir = tempfile.mkdtemp(prefix="ba_pipeline_")

        clone_url = url
        if git_token and url.startswith("https://"):
            clone_url = url.replace("https://", f"https://oauth2:{git_token}@")

        print(f"         cloning [{provider}] -> {temp_dir}")

        result = subprocess.run(
            ["git", "clone", "--depth=1", clone_url, temp_dir],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"git clone failed:\n{result.stderr.strip()}")

        return {
            "local_path": temp_dir,
            "source_type": provider,
            "original_source": url,
            "temp_dir": temp_dir,
        }

    def _extract_zip(self, zip_path: str) -> dict:
        temp_dir = tempfile.mkdtemp(prefix="ba_pipeline_")
        print(f"         extracting zip -> {temp_dir}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        # If zip has a single root folder, descend into it
        contents = os.listdir(temp_dir)
        if len(contents) == 1 and os.path.isdir(os.path.join(temp_dir, contents[0])):
            actual_path = os.path.join(temp_dir, contents[0])
        else:
            actual_path = temp_dir

        return {
            "local_path": actual_path,
            "source_type": "zip",
            "original_source": zip_path,
            "temp_dir": temp_dir,
        }

    def cleanup(self, resolved: dict):
        if resolved.get("temp_dir"):
            shutil.rmtree(resolved["temp_dir"], ignore_errors=True)
