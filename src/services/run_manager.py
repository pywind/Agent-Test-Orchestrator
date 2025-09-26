"""Lifecycle management for orchestrator runs exposed via the API."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx

from . import AsyncCallbackManager, AsyncDBConnector, AsyncOrchestrator
from ..db.schema import STAGES, RunRecord, RunStatus, TERMINAL_STATES


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
            if run_key in self._runs and self._runs[run_key].is_active():
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
            if record.is_terminal():
                return record

            if record.task and not record.task.done():
                record.task.cancel()

            record.update_status(RunStatus.CANCELLED, "Run cancelled")
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
                record.add_stage(stage_name)

            await callback_manager.register(stage, _stage_logger)

        orchestrator = AsyncOrchestrator(callbacks=callback_manager, db=self._db)

        record.update_status(RunStatus.RUNNING)

        try:
            outcome = await orchestrator.run(record.doc_path, run_id=record.run_id)
            record.result = outcome.to_dict()
            record.update_status(RunStatus.COMPLETED)
            await self._send_callback(record)
        except asyncio.CancelledError:
            record.update_status(RunStatus.CANCELLED, record.error or "Run cancelled")
            await self._send_callback(record)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            record.update_status(RunStatus.FAILED, str(exc))
            await self._send_callback(record)
            raise

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
