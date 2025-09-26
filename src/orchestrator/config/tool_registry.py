"""Tool registry loading."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass
class ToolRateLimit:
    calls_per_minute: int
    max_concurrency: int


@dataclass
class ToolMetadata:
    name: str
    description: str
    args_schema: Dict[str, str]
    timeouts: Dict[str, int]
    rate_limit: ToolRateLimit
    resources: List[str]


@dataclass
class ToolRegistry:
    tools: Dict[str, ToolMetadata]

    def get(self, name: str) -> ToolMetadata:
        return self.tools[name]


_DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "tool_registry.yaml"


def load_tool_registry(path: Path | None = None) -> ToolRegistry:
    config_path = path or _DEFAULT_REGISTRY_PATH
    raw = yaml.safe_load(config_path.read_text())
    tools = {}
    for name, entry in raw["tools"].items():
        tools[name] = ToolMetadata(
            name=name,
            description=entry.get("description", ""),
            args_schema=entry.get("args_schema", {}),
            timeouts=entry.get("timeouts", {}),
            rate_limit=ToolRateLimit(
                calls_per_minute=entry.get("rate_limit", {}).get("calls_per_minute", 60),
                max_concurrency=entry.get("rate_limit", {}).get("max_concurrency", 1),
            ),
            resources=entry.get("resources", []),
        )
    return ToolRegistry(tools=tools)

