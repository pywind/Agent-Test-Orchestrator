#!/usr/bin/env python3
"""
Migration File Generator

Creates new migration files with proper naming convention and structure.

Usage:
    python scripts/create_migration.py "description of migration"
    python scripts/create_migration.py "add user roles table" --template=table
"""

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


MIGRATION_TEMPLATES = {
    'basic': '''-- Migration V{version:03d}: {description}
-- Description: {description}
-- Author: {author}
-- Date: {date}

-- Add your SQL statements here
-- Example:
-- CREATE TABLE IF NOT EXISTS example (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );

-- Remember to:
-- 1. Use IF NOT EXISTS for CREATE statements
-- 2. Add appropriate indexes
-- 3. Consider data migration if needed
-- 4. Test thoroughly before applying
''',

    'table': '''-- Migration V{version:03d}: {description}
-- Description: Create new table: {table_name}
-- Author: {author}
-- Date: {date}

-- Create {table_name} table
CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Add your columns here
    -- name VARCHAR(255) NOT NULL,
    -- status VARCHAR(50) DEFAULT 'active',
    -- data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_{table_name}_created_at ON {schema_name}.{table_name}(created_at);
-- CREATE INDEX IF NOT EXISTS idx_{table_name}_status ON {schema_name}.{table_name}(status);

-- Create updated_at trigger
CREATE TRIGGER update_{table_name}_updated_at 
    BEFORE UPDATE ON {schema_name}.{table_name} 
    FOR EACH ROW EXECUTE FUNCTION {schema_name}.update_updated_at_column();
''',

    'alter': '''-- Migration V{version:03d}: {description}
-- Description: Alter existing table or structure
-- Author: {author}
-- Date: {date}

-- Add new columns
-- ALTER TABLE {schema_name}.existing_table 
-- ADD COLUMN IF NOT EXISTS new_column VARCHAR(255);

-- Modify existing columns
-- ALTER TABLE {schema_name}.existing_table 
-- ALTER COLUMN existing_column TYPE TEXT;

-- Add constraints
-- ALTER TABLE {schema_name}.existing_table 
-- ADD CONSTRAINT constraint_name CHECK (condition);

-- Create new indexes
-- CREATE INDEX IF NOT EXISTS idx_new_index ON {schema_name}.existing_table(column_name);

-- Update existing data (if needed)
-- UPDATE {schema_name}.existing_table SET new_column = 'default_value' WHERE new_column IS NULL;
''',

    'data': '''-- Migration V{version:03d}: {description}
-- Description: Data migration or update
-- Author: {author}
-- Date: {date}

-- Insert new data
-- INSERT INTO {schema_name}.table_name (column1, column2) VALUES 
-- ('value1', 'value2'),
-- ('value3', 'value4')
-- ON CONFLICT (unique_column) DO NOTHING;

-- Update existing data
-- UPDATE {schema_name}.table_name 
-- SET column1 = 'new_value'
-- WHERE condition = 'some_value';

-- Delete obsolete data
-- DELETE FROM {schema_name}.table_name 
-- WHERE condition = 'obsolete_value';
'''
}


def get_next_version(migrations_dir: Path) -> int:
    """Get the next migration version number."""
    if not migrations_dir.exists():
        return 1
    
    versions = []
    for file in migrations_dir.glob("V*.sql"):
        match = re.match(r'^V(\d+)__.*\.sql$', file.name)
        if match:
            versions.append(int(match.group(1)))
    
    return max(versions) + 1 if versions else 1


def sanitize_description(description: str) -> str:
    """Sanitize description for use in filename."""
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[^\w\s-]', '', description)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized.lower().strip('_')


def extract_table_name(description: str) -> str:
    """Try to extract table name from description."""
    # Look for patterns like "add users table", "create user_roles", etc.
    patterns = [
        r'(?:add|create|alter)\s+(\w+)\s+table',
        r'table\s+(\w+)',
        r'(\w+)\s+table'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description.lower())
        if match:
            return match.group(1)
    
    # Fallback: use first word
    words = description.split()
    return words[0].lower() if words else 'example'


def create_migration_file(
    description: str,
    template: str = 'basic',
    author: Optional[str] = None,
    migrations_dir: Optional[Path] = None
) -> Path:
    """Create a new migration file."""
    
    if migrations_dir is None:
        migrations_dir = Path(__file__).parent.parent / 'src' / 'db' / 'migrations'
    
    # Ensure migrations directory exists
    migrations_dir.mkdir(parents=True, exist_ok=True)
    
    # Get next version and sanitize description
    version = get_next_version(migrations_dir)
    sanitized_desc = sanitize_description(description)
    
    # Create filename
    filename = f"V{version:03d}__{sanitized_desc}.sql"
    filepath = migrations_dir / filename
    
    # Prepare template variables
    template_vars = {
        'version': version,
        'description': description,
        'author': author or 'Developer',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'schema_name': 'orchestrator',
        'table_name': extract_table_name(description)
    }
    
    # Get template content
    if template not in MIGRATION_TEMPLATES:
        print(f"⚠️  Unknown template '{template}', using 'basic'")
        template = 'basic'
    
    content = MIGRATION_TEMPLATES[template].format(**template_vars)
    
    # Write migration file
    filepath.write_text(content, encoding='utf-8')
    
    return filepath


def main():
    """Main function for migration generator."""
    parser = argparse.ArgumentParser(
        description="Generate new database migration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/create_migration.py "add user roles table"
    python scripts/create_migration.py "update user status field" --template=alter
    python scripts/create_migration.py "seed initial data" --template=data --author="John Doe"

Available templates:
    basic  - Empty migration with comments
    table  - Create new table with common patterns
    alter  - Alter existing table structure
    data   - Data migration or updates
        """
    )
    
    parser.add_argument(
        'description',
        help='Description of the migration (used in filename and comments)'
    )
    
    parser.add_argument(
        '--template', '-t',
        choices=list(MIGRATION_TEMPLATES.keys()),
        default='basic',
        help='Template to use for the migration file (default: basic)'
    )
    
    parser.add_argument(
        '--author', '-a',
        help='Author name for the migration (default: Developer)'
    )
    
    parser.add_argument(
        '--migrations-dir',
        type=Path,
        help='Path to migrations directory (default: src/db/migrations)'
    )
    
    args = parser.parse_args()
    
    try:
        filepath = create_migration_file(
            args.description,
            args.template,
            args.author,
            args.migrations_dir
        )
        
        print(f"✅ Created migration file: {filepath}")
        print(f"📝 Template: {args.template}")
        print(f"📄 Edit the file to add your SQL statements")
        print(f"🚀 Run 'make migrate-dry' to test before applying")
        
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())