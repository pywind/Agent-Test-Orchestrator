"""Asynchronous orchestration entry points for the ReWOO testing workflow."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from .services import AsyncCallbackManager, AsyncDBConnector, AsyncOrchestrator
from .services.workflow import celery_app
from .utils.state import OrchestratorOutcome


async def async_run_orchestrator(
    doc_path: str,
    *,
    callbacks: Optional[AsyncCallbackManager] = None,
    db: Optional[AsyncDBConnector] = None,
    run_id: Optional[str] = None,
) -> OrchestratorOutcome:
    orchestrator = AsyncOrchestrator(callbacks=callbacks, db=db)
    return await orchestrator.run(doc_path, run_id=run_id)


def run_orchestrator(doc_path: str) -> OrchestratorOutcome:
    """Run the orchestrator synchronously for compatibility with existing tests."""

    return asyncio.run(async_run_orchestrator(doc_path))


def run_cli(doc: str) -> OrchestratorOutcome:
    resolved_path = str(Path(doc))
    return run_orchestrator(resolved_path)


__all__ = [
    "async_run_orchestrator",
    "run_cli",
    "run_orchestrator",
    "celery_app",
]
