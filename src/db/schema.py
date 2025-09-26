"""Database schema definitions for the Agent Test Orchestrator."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


# Stage definitions for orchestrator workflow
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


# Terminal states that indicate a run is finished
TERMINAL_STATES = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


@dataclass
class RunRecord:
    """In-memory representation of an orchestration run.
    
    This dataclass represents the core data structure for managing
    orchestrator runs and their lifecycle. It's designed to be
    persisted to the database and used for API responses.
    """

    run_id: str
    doc_path: str
    callback_url: Optional[str] = None
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stages: list[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    callback_error: Optional[str] = None
    
    # Runtime fields (not persisted to database)
    task: Optional[asyncio.Task[None]] = field(default=None, repr=False)

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable summary of the run state for database storage."""
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

    def update_status(self, status: RunStatus, error: Optional[str] = None) -> None:
        """Update the run status and timestamp."""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if error:
            self.error = error

    def add_stage(self, stage: str) -> None:
        """Add a completed stage to the run record."""
        if stage not in self.stages:
            self.stages.append(stage)
            self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        """Check if the run is in a terminal state."""
        return self.status in TERMINAL_STATES

    def is_active(self) -> bool:
        """Check if the run is currently active (not terminal)."""
        return not self.is_terminal()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunRecord:
        """Create a RunRecord from a dictionary (e.g., from database)."""
        return cls(
            run_id=data["run_id"],
            doc_path=data["doc_path"],
            callback_url=data.get("callback_url"),
            status=RunStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            stages=data.get("stages", []),
            result=data.get("result"),
            error=data.get("error"),
            callback_error=data.get("callback_error"),
        )