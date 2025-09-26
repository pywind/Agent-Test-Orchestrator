"""Application factory for the Agent Test Orchestrator FastAPI service."""
from __future__ import annotations

from fastapi import FastAPI

from .exceptions import register_exception_handlers
from .lifespan import create_lifespan
from .routers import runs
from .security import create_api_key_middleware


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    app = FastAPI(
        title="Agent Test Orchestrator", 
        version="0.3.0",
        lifespan=create_lifespan
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Add API key middleware
    app.middleware("http")(create_api_key_middleware())

    # Include routers
    app.include_router(runs.router)

    return app
