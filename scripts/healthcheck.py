#!/usr/bin/env python3
"""
Database Health Check Script

Verifies that the database is accessible and migration system is working.
Used for Docker health checks and CI/CD pipeline validation.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from db.config import DatabaseConfig
    from db.migration_manager import MigrationManager
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)


async def check_database_connection(config: DatabaseConfig) -> bool:
    """Check if database is accessible."""
    try:
        import asyncpg
        
        conn = await asyncpg.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            timeout=10
        )
        
        # Simple query to verify connection
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        return result == 1
    
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return False


async def check_migration_system(config: DatabaseConfig) -> bool:
    """Check if migration system is functional."""
    try:
        manager = MigrationManager(config)
        status = await manager.get_migration_status()
        
        # Basic checks
        return (
            isinstance(status, dict) and
            'total_migrations' in status and
            'applied_migrations' in status and
            'pending_migrations' in status
        )
    
    except Exception as e:
        logging.error(f"Migration system check failed: {e}")
        return False


async def main() -> int:
    """Main health check function."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        config = DatabaseConfig.from_env()
        
        # Check database connection
        db_healthy = await check_database_connection(config)
        if not db_healthy:
            print("❌ Database connection failed")
            return 1
        
        print("✅ Database connection successful")
        
        # Check migration system
        migration_healthy = await check_migration_system(config)
        if not migration_healthy:
            print("❌ Migration system check failed")
            return 1
        
        print("✅ Migration system healthy")
        print("🎉 All health checks passed")
        return 0
    
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))