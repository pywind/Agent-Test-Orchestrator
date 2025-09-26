"""Dependency helpers for exposing the run manager to routers."""
from __future__ import annotations

from fastapi import Request

from ..services import AsyncDBConnector
from ..services.run_manager import RunManager


def provide_run_manager(db: AsyncDBConnector) -> RunManager:
    """Create a RunManager wired to shared infrastructure services."""

    return RunManager(db=db)


def get_run_manager(request: Request) -> RunManager:
    """FastAPI dependency that retrieves the RunManager from the application state."""

    run_manager = getattr(request.app.state, "run_manager", None)
    if not isinstance(run_manager, RunManager):  # pragma: no cover - defensive guard
        raise RuntimeError("Run manager has not been initialised")
    return run_manager
