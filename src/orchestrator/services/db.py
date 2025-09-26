"""Simple asynchronous in-memory data store for orchestration runs."""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

from ..utils.state import OrchestratorOutcome


class AsyncDBConnector:
    """An in-memory DB connector that mimics async persistence semantics."""

    def __init__(self) -> None:
        self._storage: Dict[str, OrchestratorOutcome] = {}
        self._lock = asyncio.Lock()

    async def save_outcome(self, key: str, outcome: OrchestratorOutcome) -> None:
        async with self._lock:
            self._storage[key] = outcome

    async def load_outcome(self, key: str) -> Optional[OrchestratorOutcome]:
        async with self._lock:
            return self._storage.get(key)

    async def list_keys(self) -> Dict[str, str]:
        async with self._lock:
            return {key: outcome.doc_pack.title for key, outcome in self._storage.items()}
