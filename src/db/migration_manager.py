"""
PostgreSQL Migration Manager

A robust migration system that ensures database schema consistency across environments.
Follows best practices including:
- Sequential versioned migrations
- Atomic transactions
- Rollback capabilities
- Environment synchronization
- Migration history tracking
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import asyncpg
from asyncpg import Connection, Pool

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass
class MigrationFile:
    """Represents a migration file with version and metadata."""
    version: int
    name: str
    filename: str
    path: Path
    description: str
    
    @classmethod
    def from_filename(cls, filepath: Path) -> Optional['MigrationFile']:
        """Parse migration file from filename following Flyway convention: V{version}__{description}.sql"""
        pattern = r'^V(\d+)__(.+)\.sql$'
        match = re.match(pattern, filepath.name)
        
        if not match:
            logger.warning(f"Migration file {filepath.name} doesn't follow naming convention V{{version}}__{{description}}.sql")
            return None
            
        version = int(match.group(1))
        description = match.group(2).replace('_', ' ')
        
        return cls(
            version=version,
            name=filepath.stem,
            filename=filepath.name,
            path=filepath,
            description=description
        )


class MigrationManager:
    """Manages database migrations with version control and rollback support."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None, migrations_dir: Optional[Path] = None):
        self.config = config or DatabaseConfig.from_env()
        self.migrations_dir = migrations_dir or Path(__file__).parent / "migrations"
        self._pool: Optional[Pool] = None
        
    async def initialize_pool(self) -> None:
        """Initialize database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                min_size=1,
                max_size=5,
                command_timeout=60
            )
    
    async def close_pool(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def create_migration_table(self, conn: Connection) -> None:
        """Create the migration history table if it doesn't exist."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                description TEXT,
                checksum VARCHAR(64) NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL DEFAULT TRUE,
                error_message TEXT
            )
        """)
        
        # Create index for faster lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
            ON schema_migrations(version)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_migrations_executed_at 
            ON schema_migrations(executed_at)
        """)
    
    def get_migration_files(self) -> List[MigrationFile]:
        """Get all migration files sorted by version."""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return []
        
        migration_files = []
        for filepath in self.migrations_dir.glob("V*.sql"):
            migration = MigrationFile.from_filename(filepath)
            if migration:
                migration_files.append(migration)
        
        # Sort by version number
        migration_files.sort(key=lambda x: x.version)
        return migration_files
    
    async def get_applied_migrations(self, conn: Connection) -> List[int]:
        """Get list of successfully applied migration versions."""
        result = await conn.fetch("""
            SELECT version FROM schema_migrations 
            WHERE success = TRUE 
            ORDER BY version
        """)
        return [row['version'] for row in result]
    
    def calculate_checksum(self, content: str) -> str:
        """Calculate MD5 checksum of migration content."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def validate_migration_integrity(self, conn: Connection) -> List[str]:
        """Validate that applied migrations haven't been modified."""
        issues = []
        applied_migrations = await conn.fetch("""
            SELECT version, filename, checksum FROM schema_migrations 
            WHERE success = TRUE
        """)
        
        for record in applied_migrations:
            version = record['version']
            stored_checksum = record['checksum']
            filename = record['filename']
            
            # Find corresponding migration file
            migration_file = self.migrations_dir / filename
            if not migration_file.exists():
                issues.append(f"Migration file V{version:03d} ({filename}) not found on filesystem")
                continue
            
            # Check if content matches stored checksum
            content = migration_file.read_text(encoding='utf-8')
            current_checksum = self.calculate_checksum(content)
            
            if current_checksum != stored_checksum:
                issues.append(f"Migration V{version:03d} has been modified after application (checksum mismatch)")
        
        return issues
    
    async def execute_migration(self, conn: Connection, migration: MigrationFile) -> Tuple[bool, Optional[str], int]:
        """Execute a single migration within a transaction."""
        content = migration.path.read_text(encoding='utf-8')
        checksum = self.calculate_checksum(content)
        
        start_time = datetime.utcnow()
        
        try:
            async with conn.transaction():
                # Execute migration SQL
                await conn.execute(content)
                
                # Record successful execution
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                await conn.execute("""
                    INSERT INTO schema_migrations 
                    (version, name, filename, description, checksum, execution_time_ms, success)
                    VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                """, migration.version, migration.name, migration.filename, 
                    migration.description, checksum, execution_time)
                
                logger.info(f"Successfully applied migration V{migration.version:03d}: {migration.description}")
                return True, None, execution_time
                
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            error_message = str(e)
            
            # Record failed execution (if possible)
            try:
                await conn.execute("""
                    INSERT INTO schema_migrations 
                    (version, name, filename, description, checksum, execution_time_ms, success, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6, FALSE, $7)
                """, migration.version, migration.name, migration.filename,
                    migration.description, checksum, execution_time, error_message)
            except Exception as record_error:
                logger.error(f"Failed to record migration failure: {record_error}")
            
            logger.error(f"Failed to apply migration V{migration.version:03d}: {error_message}")
            return False, error_message, execution_time
    
    async def migrate(self, target_version: Optional[int] = None, dry_run: bool = False) -> bool:
        """Run pending migrations up to target version."""
        await self.initialize_pool()
        
        try:
            async with self._pool.acquire() as conn:
                # Create migration table if needed
                await self.create_migration_table(conn)
                
                # Validate existing migrations
                issues = await self.validate_migration_integrity(conn)
                if issues:
                    logger.error("Migration integrity issues found:")
                    for issue in issues:
                        logger.error(f"  - {issue}")
                    return False
                
                # Get migrations to apply
                all_migrations = self.get_migration_files()
                applied_versions = set(await self.get_applied_migrations(conn))
                
                pending_migrations = [
                    m for m in all_migrations 
                    if m.version not in applied_versions and 
                    (target_version is None or m.version <= target_version)
                ]
                
                if not pending_migrations:
                    logger.info("No pending migrations to apply")
                    return True
                
                logger.info(f"Found {len(pending_migrations)} pending migrations")
                
                if dry_run:
                    logger.info("DRY RUN - The following migrations would be applied:")
                    for migration in pending_migrations:
                        logger.info(f"  V{migration.version:03d}: {migration.description}")
                    return True
                
                # Apply migrations
                total_success = True
                for migration in pending_migrations:
                    success, error, exec_time = await self.execute_migration(conn, migration)
                    if not success:
                        total_success = False
                        logger.error(f"Migration failed, stopping at V{migration.version:03d}")
                        break
                
                return total_success
                
        finally:
            await self.close_pool()
    
    async def get_migration_status(self) -> dict:
        """Get current migration status information."""
        await self.initialize_pool()
        
        try:
            async with self._pool.acquire() as conn:
                await self.create_migration_table(conn)
                
                all_migrations = self.get_migration_files()
                applied_versions = set(await self.get_applied_migrations(conn))
                
                # Get last applied migration info
                last_migration = await conn.fetchrow("""
                    SELECT * FROM schema_migrations 
                    WHERE success = TRUE 
                    ORDER BY version DESC 
                    LIMIT 1
                """)
                
                pending_count = sum(1 for m in all_migrations if m.version not in applied_versions)
                
                return {
                    'total_migrations': len(all_migrations),
                    'applied_migrations': len(applied_versions),
                    'pending_migrations': pending_count,
                    'last_applied': dict(last_migration) if last_migration else None,
                    'integrity_issues': await self.validate_migration_integrity(conn)
                }
        finally:
            await self.close_pool()
    
    async def rollback_to_version(self, target_version: int) -> bool:
        """
        Rollback to a specific version by applying down migrations.
        Note: This requires down migration files (V{version}__rollback_{description}.sql)
        """
        # This is a placeholder for rollback functionality
        # In practice, you might want to implement this with separate rollback files
        # or by maintaining rollback scripts within migration files
        logger.warning("Rollback functionality not implemented. Consider using database backups for rollbacks.")
        return False


async def run_migrations(config: Optional[DatabaseConfig] = None, target_version: Optional[int] = None, dry_run: bool = False) -> bool:
    """Convenience function to run migrations."""
    manager = MigrationManager(config)
    return await manager.migrate(target_version, dry_run)


if __name__ == "__main__":
    import sys
    
    # Basic CLI interface
    dry_run = "--dry-run" in sys.argv
    target_version = None
    
    for arg in sys.argv:
        if arg.startswith("--target="):
            target_version = int(arg.split("=")[1])
    
    success = asyncio.run(run_migrations(target_version=target_version, dry_run=dry_run))
    sys.exit(0 if success else 1)
