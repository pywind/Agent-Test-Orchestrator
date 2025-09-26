"""Asynchronous PostgreSQL data store for orchestration runs."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Optional

import asyncpg
from asyncpg import Pool

from .config import DatabaseConfig
from ..services.orchestrator.utils.state import OrchestratorOutcome

logger = logging.getLogger(__name__)


class AsyncDBConnector:
    """PostgreSQL async database connector for orchestrator outcomes."""

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        self.config = config or DatabaseConfig.from_env()
        self._pool: Optional[Pool] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database connection pool and create schema."""
        async with self._lock:
            if self._initialized:
                return
                
            try:
                # Create connection pool
                self._pool = await asyncpg.create_pool(
                    self.config.get_async_url(),
                    min_size=self.config.min_connections,
                    max_size=self.config.max_connections,
                    max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                )
                
                # Initialize database schema
                await self._create_schema()
                self._initialized = True
                logger.info(f"Database connection pool initialized: {self.config.host}:{self.config.port}")
                
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                raise

    async def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        schema_sql = """
        -- Create the orchestrator schema if it doesn't exist
        CREATE SCHEMA IF NOT EXISTS orchestrator;

        -- Create the outcomes table for storing OrchestratorOutcome data
        CREATE TABLE IF NOT EXISTS orchestrator.outcomes (
            id SERIAL PRIMARY KEY,
            key VARCHAR(255) UNIQUE NOT NULL,
            doc_title VARCHAR(255),
            outcome_data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_outcomes_key ON orchestrator.outcomes(key);
        CREATE INDEX IF NOT EXISTS idx_outcomes_doc_title ON orchestrator.outcomes(doc_title);
        CREATE INDEX IF NOT EXISTS idx_outcomes_created_at ON orchestrator.outcomes(created_at);

        -- Create updated_at trigger function
        CREATE OR REPLACE FUNCTION orchestrator.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        -- Create trigger
        DROP TRIGGER IF EXISTS update_outcomes_updated_at ON orchestrator.outcomes;
        CREATE TRIGGER update_outcomes_updated_at 
            BEFORE UPDATE ON orchestrator.outcomes 
            FOR EACH ROW EXECUTE FUNCTION orchestrator.update_updated_at_column();
        """
        
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self._pool.acquire() as conn:
            await conn.execute(schema_sql)

    async def save_outcome(self, key: str, outcome: OrchestratorOutcome) -> None:
        """Save an orchestrator outcome to the database."""
        await self._ensure_initialized()
        
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        # Convert outcome to JSON-serializable format
        outcome_data = outcome.to_dict()
        doc_title = getattr(outcome.doc_pack, 'title', None) if hasattr(outcome, 'doc_pack') else None
        
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO orchestrator.outcomes (key, doc_title, outcome_data)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) 
                DO UPDATE SET 
                    doc_title = EXCLUDED.doc_title,
                    outcome_data = EXCLUDED.outcome_data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                key,
                doc_title,
                json.dumps(outcome_data)
            )
        
        logger.debug(f"Saved outcome for key: {key}")

    async def load_outcome(self, key: str) -> Optional[OrchestratorOutcome]:
        """Load an orchestrator outcome from the database."""
        await self._ensure_initialized()
        
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT outcome_data FROM orchestrator.outcomes WHERE key = $1",
                key
            )
            
            if row is None:
                return None
            
            try:
                outcome_data = json.loads(row['outcome_data'])
                # Note: This would need proper deserialization logic
                # For now, returning None as the OrchestratorOutcome structure
                # would need custom deserialization methods
                logger.warning(f"Loaded outcome data for key {key}, but deserialization not implemented")
                return None  # TODO: Implement proper deserialization
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to deserialize outcome for key {key}: {e}")
                return None

    async def list_keys(self) -> Dict[str, str]:
        """List all stored outcome keys with their document titles."""
        await self._ensure_initialized()
        
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, doc_title FROM orchestrator.outcomes ORDER BY created_at DESC"
            )
            
            return {row['key']: row['doc_title'] or 'Unknown' for row in rows}

    async def delete_outcome(self, key: str) -> bool:
        """Delete an outcome by key. Returns True if deleted, False if not found."""
        await self._ensure_initialized()
        
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM orchestrator.outcomes WHERE key = $1",
                key
            )
            
            # Extract number of affected rows from result
            deleted_count = int(result.split()[-1]) if result else 0
            return deleted_count > 0

    async def get_outcome_stats(self) -> Dict[str, int]:
        """Get statistics about stored outcomes."""
        await self._ensure_initialized()
        
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_outcomes,
                    COUNT(DISTINCT doc_title) as unique_documents
                FROM orchestrator.outcomes
                """
            )
            
            return {
                'total_outcomes': row['total_outcomes'],
                'unique_documents': row['unique_documents']
            }

    async def _ensure_initialized(self) -> None:
        """Ensure the database connection is initialized."""
        if not self._initialized:
            await self.initialize()

    async def close(self) -> None:
        """Close the database connection pool."""
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None
                self._initialized = False
                logger.info("Database connection pool closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
