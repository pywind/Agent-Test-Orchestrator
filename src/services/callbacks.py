"""Asynchronous callback utilities for orchestration stages."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List

from .orchestrator.utils.state import GraphState


Callback = Callable[[GraphState], Awaitable[None]]


class AsyncCallbackManager:
    """Registry for async callbacks triggered after each orchestration stage."""

    def __init__(self) -> None:
        self._callbacks: Dict[str, List[Callback]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def register(self, event: str, callback: Callback) -> None:
        """Register a callback to execute after a stage."""

        async with self._lock:
            self._callbacks[event].append(callback)

    async def emit(self, event: str, state: GraphState) -> None:
        """Invoke callbacks registered for *event* sequentially."""

        async with self._lock:
            callbacks = list(self._callbacks.get(event, ()))
        for cb in callbacks:
            await cb(state)

    async def clear(self) -> None:
        """Remove all registered callbacks."""

        async with self._lock:
            self._callbacks.clear()
