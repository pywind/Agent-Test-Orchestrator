"""Database configuration for PostgreSQL connection."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Configuration for PostgreSQL database connection."""
    
    host: str = "localhost"
    port: int = 5432
    database: str = "orchestrator"
    username: str = "postgres"
    password: Optional[str] = None
    schema: str = "orchestrator"
    
    # Connection pool settings
    min_connections: int = 1
    max_connections: int = 10
    max_inactive_connection_lifetime: float = 300.0  # 5 minutes
    
    # SSL settings
    ssl_mode: str = "prefer"
    
    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost")),
            port=int(os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432"))),
            database=os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "agent_orchestrator")),
            username=os.getenv("POSTGRES_USER", os.getenv("DB_USER", "agent")),
            password=os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "password")),
            schema=os.getenv("DB_SCHEMA", "orchestrator"),
            min_connections=int(os.getenv("DB_MIN_CONNECTIONS", "1")),
            max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "10")),
            max_inactive_connection_lifetime=float(
                os.getenv("DB_MAX_INACTIVE_LIFETIME", "300")
            ),
            ssl_mode=os.getenv("DB_SSL_MODE", "prefer"),
        )
    
    def get_dsn(self) -> str:
        """Get PostgreSQL connection DSN."""
        dsn_parts = [
            f"host={self.host}",
            f"port={self.port}",
            f"dbname={self.database}",
            f"user={self.username}",
        ]
        
        if self.password:
            dsn_parts.append(f"password={self.password}")
            
        if self.ssl_mode:
            dsn_parts.append(f"sslmode={self.ssl_mode}")
        
        return " ".join(dsn_parts)
    
    def get_async_url(self) -> str:
        """Get asyncpg connection URL."""
        password_part = f":{self.password}" if self.password else ""
        return f"postgresql://{self.username}{password_part}@{self.host}:{self.port}/{self.database}"