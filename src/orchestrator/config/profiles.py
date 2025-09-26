"""Environment profile configuration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass
class EnvironmentProfile:
    name: str
    description: str
    browser_matrix: List[str]
    device_matrix: List[str]
    media: Dict[str, bool]
    network: Dict[str, str]
    concurrency_limit: int
    retries: int


@dataclass
class EnvironmentProfiles:
    profiles: Dict[str, EnvironmentProfile]

    def get(self, name: str) -> EnvironmentProfile:
        return self.profiles[name]


_DEFAULT_PROFILE_PATH = Path(__file__).resolve().parent / "profiles.yaml"


def load_environment_profiles(path: Path | None = None) -> EnvironmentProfiles:
    """Load environment profiles from YAML."""

    config_path = path or _DEFAULT_PROFILE_PATH
    raw = yaml.safe_load(config_path.read_text())
    profiles = {
        name: EnvironmentProfile(
            name=name,
            description=entry.get("description", ""),
            browser_matrix=entry.get("browser_matrix", []),
            device_matrix=entry.get("device_matrix", []),
            media=entry.get("media", {}),
            network=entry.get("network", {}),
            concurrency_limit=entry.get("concurrency_limit", 1),
            retries=entry.get("retries", 0),
        )
        for name, entry in raw["profiles"].items()
    }
    return EnvironmentProfiles(profiles=profiles)

