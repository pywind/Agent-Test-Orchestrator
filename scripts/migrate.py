#!/usr/bin/env python3
"""
Database Migration Script

This script handles database migrations for the Agent Test Orchestrator.
It ensures that database schema changes are applied consistently across all environments.

Usage:
    python scripts/migrate.py [OPTIONS]

Options:
    --dry-run           Show pending migrations without applying them
    --target=VERSION    Migrate to a specific version (default: latest)
    --status            Show current migration status
    --validate          Validate migration integrity
    --help              Show this help message

Examples:
    python scripts/migrate.py                    # Apply all pending migrations
    python scripts/migrate.py --dry-run          # Show what would be migrated
    python scripts/migrate.py --target=5         # Migrate up to version 5
    python scripts/migrate.py --status           # Show migration status
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from db.migration_manager import MigrationManager, run_migrations
from db.config import DatabaseConfig


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for migration script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Database Migration Manager for Agent Test Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show pending migrations without applying them'
    )
    
    parser.add_argument(
        '--target',
        type=int,
        help='Target migration version (default: latest)'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show current migration status'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate migration file integrity'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--migrations-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'migrations',
        help='Path to migrations directory (default: migrations)'
    )
    
    return parser


async def show_status(manager: MigrationManager) -> None:
    """Display current migration status."""
    status = await manager.get_migration_status()
    
    print("\n=== Migration Status ===")
    print(f"Total migrations: {status['total_migrations']}")
    print(f"Applied migrations: {status['applied_migrations']}")
    print(f"Pending migrations: {status['pending_migrations']}")
    
    if status['last_applied']:
        last = status['last_applied']
        print(f"Last applied: V{last['version']:03d} - {last['description']}")
        print(f"Applied at: {last['executed_at']}")
        print(f"Execution time: {last['execution_time_ms']}ms")
    
    if status['integrity_issues']:
        print("\n⚠️  Integrity Issues:")
        for issue in status['integrity_issues']:
            print(f"  - {issue}")
    else:
        print("\n✅ No integrity issues found")


async def validate_migrations(manager: MigrationManager) -> bool:
    """Validate migration file integrity."""
    await manager.initialize_pool()
    
    try:
        async with manager._pool.acquire() as conn:
            await manager.create_migration_table(conn)
            issues = await manager.validate_migration_integrity(conn)
            
            if issues:
                print("❌ Migration integrity validation failed:")
                for issue in issues:
                    print(f"  - {issue}")
                return False
            else:
                print("✅ All migrations validated successfully")
                return True
                
    finally:
        await manager.close_pool()


async def main() -> int:
    """Main migration script entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize migration manager
        config = DatabaseConfig.from_env()
        manager = MigrationManager(config, args.migrations_dir)
        
        # Handle different commands
        if args.status:
            await show_status(manager)
            return 0
        
        if args.validate:
            success = await validate_migrations(manager)
            return 0 if success else 1
        
        # Run migrations
        logger.info("Starting database migration process...")
        logger.info(f"Database: {config.database}")
        logger.info(f"Host: {config.host}:{config.port}")
        
        if args.dry_run:
            logger.info("Running in DRY-RUN mode")
        
        success = await run_migrations(
            config=config,
            target_version=args.target,
            dry_run=args.dry_run
        )
        
        if success:
            logger.info("✅ Migration completed successfully")
            return 0
        else:
            logger.error("❌ Migration failed")
            return 1
    
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        return 130
    
    except Exception as e:
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
