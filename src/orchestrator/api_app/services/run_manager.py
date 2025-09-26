"""Lifecycle management for orchestrator runs exposed via the API."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx

from ...services import AsyncCallbackManager, AsyncDBConnector, AsyncOrchestrator

STAGES = [
    "ingest_docs",
    "planner",
    "emit_tool_specs",
    "dispatch_tools",
    "substitute_vars",
    "synthesize_artifacts",
    "worker_execute_suite",
    "collect_evidence",
    "resolver",
    "postmortem_and_heal",
    "completed",
]


class RunStatus(str, Enum):
    """Lifecycle states for orchestration runs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


@dataclass(slots=True)
class RunRecord:
    """In-memory representation of an orchestration run."""

    run_id: str
    doc_path: str
    callback_url: Optional[str] = None
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    stages: list[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    callback_error: Optional[str] = None
    task: Optional[asyncio.Task[None]] = None

    def snapshot(self) -> Dict[str, Any]:
        """Return a serialisable summary of the run state."""

        return {
            "run_id": self.run_id,
            "doc_path": self.doc_path,
            "status": self.status.value,
            "stages": list(self.stages),
            "result": self.result,
            "error": self.error,
            "callback_url": self.callback_url,
            "callback_error": self.callback_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RunManager:
    """Coordinates asynchronous orchestrator runs for the FastAPI surface."""

    def __init__(self, *, db: AsyncDBConnector) -> None:
        self._db = db
        self._lock = asyncio.Lock()
        self._runs: Dict[str, RunRecord] = {}

    async def start_run(self, doc_path: str, *, run_id: Optional[str] = None, callback_url: Optional[str] = None) -> RunRecord:
        """Kick off a new orchestrator execution in the background."""

        async with self._lock:
            run_key = run_id or str(uuid4())
            if run_key in self._runs and self._runs[run_key].status not in TERMINAL_STATES:
                raise ValueError(f"run_id '{run_key}' is already active")

            record = RunRecord(run_id=run_key, doc_path=doc_path, callback_url=callback_url)
            self._runs[run_key] = record
            record.task = asyncio.create_task(self._execute_run(record), name=f"run-{run_key}")
            return record

    async def check_run(self, run_id: str) -> RunRecord:
        async with self._lock:
            try:
                return self._runs[run_id]
            except KeyError as exc:
                raise KeyError(f"run_id '{run_id}' not found") from exc

    async def cancel_run(self, run_id: str) -> RunRecord:
        async with self._lock:
            if run_id not in self._runs:
                raise KeyError(f"run_id '{run_id}' not found")

            record = self._runs[run_id]
            if record.status in TERMINAL_STATES:
                return record

            if record.task and not record.task.done():
                record.task.cancel()

            record.status = RunStatus.CANCELLED
            record.updated_at = datetime.utcnow()
            record.error = record.error or "Run cancelled"
            return record

    async def shutdown(self) -> None:
        """Cancel any in-flight runs during application shutdown."""

        async with self._lock:
            tasks = [record.task for record in self._runs.values() if record.task and not record.task.done()]
            for task in tasks:
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_run(self, record: RunRecord) -> None:
        callback_manager = AsyncCallbackManager()

        for stage in STAGES:
            async def _stage_logger(_: Any, stage_name: str = stage) -> None:
                record.stages.append(stage_name)
                record.updated_at = datetime.utcnow()

            await callback_manager.register(stage, _stage_logger)

        orchestrator = AsyncOrchestrator(callbacks=callback_manager, db=self._db)

        record.status = RunStatus.RUNNING
        record.updated_at = datetime.utcnow()

        try:
            outcome = await orchestrator.run(record.doc_path, run_id=record.run_id)
            record.result = outcome.to_dict()
            record.status = RunStatus.COMPLETED
            await self._send_callback(record)
        except asyncio.CancelledError:
            record.status = RunStatus.CANCELLED
            record.error = record.error or "Run cancelled"
            await self._send_callback(record)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            record.status = RunStatus.FAILED
            record.error = str(exc)
            await self._send_callback(record)
            raise
        finally:
            record.updated_at = datetime.utcnow()

    async def _send_callback(self, record: RunRecord) -> None:
        if not record.callback_url:
            return

        payload = {
            "run_id": record.run_id,
            "status": record.status.value,
            "result": record.result,
            "error": record.error,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(record.callback_url, json=payload, timeout=10)
                response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network interactions are non-deterministic
            record.callback_error = str(exc)
