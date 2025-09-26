"""Application lifespan management."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from ..db.config import DatabaseConfig
from ..services import AsyncDBConnector
from ..dependencies.run_manager import provide_run_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting Agent Test Orchestrator application")
    
    # Initialize database with configuration
    db_config = DatabaseConfig.from_env()
    db_connector = AsyncDBConnector(db_config)
    
    # Initialize database connection and schema
    await db_connector.initialize()
    
    run_manager = provide_run_manager(db_connector)
    app.state.run_manager = run_manager
    app.state.db_connector = db_connector
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Test Orchestrator application")
    await run_manager.shutdown()
    await db_connector.close()