"""Core detection logic: match git diff against metadata to find triggered playbooks."""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def get_changed_files(start: str, end: str, repo_dir: str = ".") -> list[str]:
    """Return list of files changed between two git refs."""
    # Mark the repo as safe to avoid "dubious ownership" errors in containers
    abs_repo = str(Path(repo_dir).resolve())
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", abs_repo],
        capture_output=True,
        check=False,
    )
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{start}...{end}"],
        capture_output=True,
        text=True,
        cwd=repo_dir,
        check=True,
    )
    return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]


def load_metadata(path: str) -> dict[str, Any]:
    """Load a .metadata.yml file.

    Expected format:
        playbook_name:
          stage: 1
          depends_on: []
          paths:
            - "ansible/roles/my_role/**"
            - "ansible/inventory/*/group_vars/**"
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or {}


def match_paths(changed_files: list[str], patterns: list[str]) -> bool:
    """Check if any changed file matches any of the glob patterns."""
    for changed in changed_files:
        for pattern in patterns:
            if fnmatch.fnmatch(changed, pattern):
                return True
    return False


def detect_changes(
    start: str,
    end: str,
    metadata_files: list[str],
    repo_dir: str = ".",
) -> dict[str, Any]:
    """Run change detection and return playbook trigger map.

    Returns a dict like:
        {
            "playbook_name": {
                "triggered": true,
                "stage": 1,
                "depends_on": [],
                "matched_files": ["path/to/file"]
            }
        }
    """
    changed_files = get_changed_files(start, end, repo_dir)

    result: dict[str, Any] = {}

    for meta_path in metadata_files:
        metadata = load_metadata(meta_path)

        for playbook_name, config in metadata.items():
            if not isinstance(config, dict):
                continue

            patterns = config.get("paths", [])
            stage = config.get("stage", 0)
            depends_on = config.get("depends_on", [])

            matched = [
                f for f in changed_files
                if any(fnmatch.fnmatch(f, p) for p in patterns)
            ]

            triggered = len(matched) > 0

            if playbook_name in result:
                if triggered:
                    result[playbook_name]["triggered"] = True
                    result[playbook_name]["matched_files"].extend(matched)
            else:
                result[playbook_name] = {
                    "triggered": triggered,
                    "stage": stage,
                    "depends_on": depends_on,
                    "matched_files": matched,
                }

    # Propagate triggers through dependencies
    changed = True
    while changed:
        changed = False
        for name, info in result.items():
            if info["triggered"]:
                continue
            for dep in info["depends_on"]:
                if dep in result and result[dep]["triggered"]:
                    info["triggered"] = True
                    changed = True
                    break

    return result
