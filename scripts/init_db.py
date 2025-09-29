#!/usr/bin/env python3
"""Database initialization script for the Agent Test Orchestrator."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.config import DatabaseConfig
from src.db.db_connector import AsyncDBConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Initialize the database with schema."""
    config = DatabaseConfig.from_env()
    
    logger.info(f"Initializing database at {config.host}:{config.port}/{config.database}")
    
    async with AsyncDBConnector(config) as db:
        logger.info("Database initialized successfully!")
        
        # Test basic operations
        stats = await db.get_outcome_stats()
        logger.info(f"Database stats: {stats}")


async def reset_database() -> None:
    """Reset the database (drop and recreate schema)."""
    config = DatabaseConfig.from_env()
    
    logger.warning(f"Resetting database at {config.host}:{config.port}/{config.database}")
    
    # Create a temporary connector to drop schema
    import asyncpg
    
    conn = await asyncpg.connect(config.get_async_url())
    try:
        await conn.execute("DROP SCHEMA IF EXISTS orchestrator CASCADE")
        logger.info("Dropped existing schema")
    finally:
        await conn.close()
    
    # Reinitialize
    await init_database()


def main() -> None:
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management for Agent Test Orchestrator")
    parser.add_argument(
        "command", 
        choices=["init", "reset"], 
        help="Command to execute"
    )
    
    args = parser.parse_args()
    
    if args.command == "init":
        asyncio.run(init_database())
    elif args.command == "reset":
        asyncio.run(reset_database())


if __name__ == "__main__":
    main()