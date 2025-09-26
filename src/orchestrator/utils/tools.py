"""MCP tool stubs used by the LangGraph orchestrator."""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class MCPToolResult:
    data: Dict[str, Any]
    logs: str = ""
    screenshot: str | None = None
    video: str | None = None


class MCPTool:
    """Lightweight base class for MCP-style tools."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, **kwargs: Any) -> MCPToolResult:  # pragma: no cover - interface
        raise NotImplementedError


class FilesystemTool(MCPTool):
    def __init__(self, root: Path | None = None) -> None:
        super().__init__("filesystem.fetch_doc")
        self.root = root or Path.cwd()

    def execute(self, **kwargs: Any) -> MCPToolResult:
        rel_path = kwargs.get("path")
        if not rel_path:
            raise ValueError("path argument is required")
        target = self.root / rel_path
        text = target.read_text()
        logs = f"Loaded document {rel_path}"
        return MCPToolResult(data={"value": text}, logs=logs)


class ArtifactStoreTool(MCPTool):
    def __init__(self) -> None:
        super().__init__("artifact_store.persist")

    def execute(self, **kwargs: Any) -> MCPToolResult:
        return MCPToolResult(data={"uri": "artifacts/run.json"}, logs="Persisted artifact")


class PlaywrightNavigator(MCPTool):
    def __init__(self) -> None:
        super().__init__("playwright.navigate")

    def execute(self, **kwargs: Any) -> MCPToolResult:
        url = kwargs.get("url", "http://example.com")
        wait_for = kwargs.get("wait_for", "#root")
        logs = f"Navigated to {url} and waited for {wait_for}"
        return MCPToolResult(data={"value": f"path:{url}->{wait_for}"}, logs=logs, screenshot="screens/nav.png")


class PlaywrightSelectorProbe(MCPTool):
    def __init__(self) -> None:
        super().__init__("playwright.selector_probe")

    def execute(self, **kwargs: Any) -> MCPToolResult:
        base_selector = kwargs.get("selector_hint", "button.primary")
        variants = [
            base_selector,
            base_selector + " >> text='Submit'",
            base_selector + "[data-qa='submit']",
        ]
        random.shuffle(variants)
        logs = f"Probed selector variants for {base_selector}"
        return MCPToolResult(data={"selectors": variants}, logs=logs, screenshot="screens/selector.png")


class AppiumNavigator(MCPTool):
    def __init__(self) -> None:
        super().__init__("appium.navigate")

    def execute(self, **kwargs: Any) -> MCPToolResult:
        screen = kwargs.get("screen", "home")
        logs = f"Navigated to mobile screen {screen}"
        return MCPToolResult(data={"value": f"screen:{screen}"}, logs=logs, video="videos/navigate.mp4")


class AppiumSelectorProbe(MCPTool):
    def __init__(self) -> None:
        super().__init__("appium.selector_probe")

    def execute(self, **kwargs: Any) -> MCPToolResult:
        hint = kwargs.get("selector_hint", "~loginButton")
        variants = [hint, f"accessibility_id={hint}", f"xpath=//button[@name='{hint}']"]
        random.shuffle(variants)
        logs = f"Generated Appium selector variants for {hint}"
        return MCPToolResult(data={"selectors": variants}, logs=logs, screenshot="screens/mobile.png")


DEFAULT_TOOL_REGISTRY: Dict[str, MCPTool] = {
    "playwright.navigate": PlaywrightNavigator(),
    "playwright.selector_probe": PlaywrightSelectorProbe(),
    "appium.navigate": AppiumNavigator(),
    "appium.selector_probe": AppiumSelectorProbe(),
    "filesystem.fetch_doc": FilesystemTool(),
    "artifact_store.persist": ArtifactStoreTool(),
}
