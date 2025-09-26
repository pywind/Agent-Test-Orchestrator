"""Application factory for the Agent Test Orchestrator FastAPI service."""
from __future__ import annotations

from fastapi import FastAPI

from ..services import AsyncDBConnector
from .dependencies.run_manager import provide_run_manager
from .routers import runs


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    app = FastAPI(title="Agent Test Orchestrator", version="0.3.0")

    run_manager = provide_run_manager(AsyncDBConnector())
    app.state.run_manager = run_manager

    app.include_router(runs.router)

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - exercised via ASGI lifecycle
        await run_manager.shutdown()

    return app
