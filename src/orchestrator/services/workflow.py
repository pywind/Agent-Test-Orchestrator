"""High-level asynchronous orchestration pipeline."""
from __future__ import annotations

import asyncio
from typing import Optional

from ..utils.nodes import summarize_outcome
from ..utils.state import GraphState, OrchestratorOutcome
from .callbacks import AsyncCallbackManager
from .db import AsyncDBConnector
from .task_queue import (
    celery_app,
    dispatch_task,
    evidence_task,
    execution_task,
    ingest_task,
    planner_task,
    postmortem_task,
    resolver_task,
    substitution_task,
    synthesis_task,
    tool_spec_task,
)


class AsyncOrchestrator:
    """Coordinates the Celery-based asynchronous workflow."""

    def __init__(
        self,
        *,
        callbacks: Optional[AsyncCallbackManager] = None,
        db: Optional[AsyncDBConnector] = None,
    ) -> None:
        self.callbacks = callbacks or AsyncCallbackManager()
        self.db = db or AsyncDBConnector()

    async def _dispatch_state_task(self, task, state: GraphState, stage: str) -> GraphState:
        def _invoke() -> GraphState:
            result = task.delay(state)
            return result.get()

        new_state = await asyncio.to_thread(_invoke)
        await self.callbacks.emit(stage, new_state)
        return new_state

    async def run(self, doc_path: str, run_id: Optional[str] = None) -> OrchestratorOutcome:
        run_key = run_id or doc_path

        def _ingest() -> GraphState:
            result = ingest_task.delay(doc_path)
            return result.get()

        state = await asyncio.to_thread(_ingest)
        await self.callbacks.emit("ingest_docs", state)

        for stage, task in [
            ("planner", planner_task),
            ("emit_tool_specs", tool_spec_task),
            ("dispatch_tools", dispatch_task),
            ("substitute_vars", substitution_task),
            ("synthesize_artifacts", synthesis_task),
            ("worker_execute_suite", execution_task),
            ("collect_evidence", evidence_task),
            ("resolver", resolver_task),
            ("postmortem_and_heal", postmortem_task),
        ]:
            state = await self._dispatch_state_task(task, state, stage)

        outcome = summarize_outcome(state)
        await self.db.save_outcome(run_key, outcome)
        await self.callbacks.emit("completed", state)
        return outcome


__all__ = ["AsyncOrchestrator", "celery_app"]
