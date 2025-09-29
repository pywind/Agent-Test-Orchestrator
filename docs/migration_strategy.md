# Database Migration Strategy & Best Practices

## Overview

This document outlines the comprehensive database migration strategy for the Agent Test Orchestrator, ensuring PostgreSQL synchronization across all environments with zero-downtime deployments and rollback capabilities.

## Architecture Components

### 1. Migration System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Development   │    │     Staging     │    │   Production    │
│                 │    │                 │    │                 │
│ Local Database  │───▶│ Staging Database│───▶│ Prod Database   │
│ Fast Iteration  │    │ Full Testing    │    │ Backup & Safety │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. Migration Flow

```
1. Developer creates migration ─┐
2. Auto-validation (CI/CD) ─────┤
3. Staging deployment ─────────▶│
4. Manual testing ─────────────▶│
5. Production deployment ───────┘
```

## Migration File Conventions

### Naming Convention
- **Pattern**: `V{version}__{description}.sql`
- **Examples**: 
  - `V001__initial_schema.sql`
  - `V002__add_user_roles_table.sql`
  - `V003__update_user_status_field.sql`

### Version Management
- **Sequential numbering**: No gaps allowed (1, 2, 3, ...)
- **Zero-padded**: Use 3 digits (V001, V002, etc.)
- **Immutable**: Never modify applied migrations

## Best Practices

### 1. Migration Development

#### ✅ DO:
```sql
-- Use IF NOT EXISTS for safety
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes explicitly
CREATE INDEX IF NOT EXISTS idx_user_roles_name ON user_roles(name);

-- Use transactions implicitly (our system handles this)
-- Handle data migration safely
UPDATE users SET role = 'user' WHERE role IS NULL;
```

#### ❌ DON'T:
```sql
-- Don't use DROP without IF EXISTS
DROP TABLE user_roles;  -- WRONG

-- Don't hardcode values that may vary between environments
INSERT INTO config VALUES (1, 'localhost:5432');  -- WRONG

-- Don't create migrations with dependencies on external systems
COPY users FROM '/tmp/users.csv';  -- WRONG
```

### 2. Schema Changes

#### Adding Columns
```sql
-- Safe column addition
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Add non-null columns safely
ALTER TABLE users ADD COLUMN created_by VARCHAR(100) DEFAULT 'system';
-- Then later, remove default if needed
ALTER TABLE users ALTER COLUMN created_by DROP DEFAULT;
```

#### Renaming Columns (Multi-step approach)
```sql
-- Step 1: Add new column
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);

-- Step 2: Populate new column
UPDATE users SET full_name = first_name || ' ' || last_name;

-- Step 3: (Next migration) Drop old columns
-- ALTER TABLE users DROP COLUMN first_name;
-- ALTER TABLE users DROP COLUMN last_name;
```

### 3. Data Migrations

#### Safe Data Updates
```sql
-- Use WHERE clauses to limit impact
UPDATE users 
SET status = 'active' 
WHERE status IS NULL 
  AND created_at > '2024-01-01';

-- Use EXISTS for complex conditions
UPDATE runs r1 
SET status = 'completed'
WHERE EXISTS (
    SELECT 1 FROM run_results r2 
    WHERE r2.run_id = r1.id 
    AND r2.success = true
);
```

#### Batch Processing for Large Tables
```sql
-- For very large tables, consider batching
-- This is a template - adjust batch size based on table size
DO $$
DECLARE
    batch_size INTEGER := 1000;
    processed INTEGER := 0;
BEGIN
    LOOP
        UPDATE large_table 
        SET new_column = calculate_value(old_column)
        WHERE new_column IS NULL
        AND id IN (
            SELECT id FROM large_table 
            WHERE new_column IS NULL 
            LIMIT batch_size
        );
        
        GET DIAGNOSTICS processed = ROW_COUNT;
        EXIT WHEN processed < batch_size;
        
        -- Add small delay to avoid overwhelming the database
        PERFORM pg_sleep(0.1);
    END LOOP;
END $$;
```

## Environment-Specific Configurations

### Development Environment
```bash
# Fast iteration, no safety nets
make migrate          # Apply all pending migrations
make migrate-dry      # Test migrations without applying
make db-reset         # Reset entire database (destructive)
```

### Staging Environment
```bash
# Full validation before production
make migrate-validate   # Check migration integrity
make db-backup          # Always backup before changes
make migrate           # Apply migrations
make migrate-status    # Verify successful application
```

### Production Environment
```bash
# Maximum safety protocols
make db-backup BACKUP_NAME=pre-migration-$(date +%Y%m%d)
make migrate-validate   # Validate before applying
make migrate-dry       # Final verification
make migrate           # Apply with monitoring
make migrate-status    # Confirm success
```

## Rollback Strategy

### Automated Rollback (For Data Corruption)
1. **Stop application**: Prevent new writes
2. **Restore from backup**: Use latest clean backup
3. **Apply migrations**: Up to the last known good state
4. **Restart application**: Resume operations

### Manual Rollback (For Schema Issues)
1. **Identify problem migration**: Check migration history
2. **Create rollback migration**: Write explicit rollback SQL
3. **Test rollback**: On staging environment first
4. **Apply rollback**: With full monitoring

## Monitoring and Alerting

### Health Checks
- Database connectivity
- Migration system integrity
- Schema version consistency
- Performance impact monitoring

### Alerting Triggers
- Migration failure
- Long-running migrations (>5 minutes)
- Schema integrity violations
- Rollback events

## CI/CD Integration

### Pre-commit Hooks
```bash
# Validate migration naming
# Check for gaps in version numbers
# Syntax validation
```

### GitHub Actions Pipeline
1. **Validate migrations**: Naming, sequencing, syntax
2. **Test in isolated environment**: Fresh database
3. **Docker integration test**: Full container stack
4. **Approval gates**: For production deployments

### Deployment Strategies

#### Blue-Green Deployment
1. **Blue**: Current production
2. **Green**: New version with migrations applied
3. **Switch**: Atomic cutover after validation
4. **Fallback**: Keep blue environment for rollback

#### Rolling Deployment
1. **Backwards-compatible migrations**: Schema changes that work with both versions
2. **Gradual rollout**: Instance-by-instance deployment
3. **Code deployment**: After schema is fully deployed

## Troubleshooting

### Common Issues

#### Migration Stuck/Hanging
```sql
-- Check for blocking queries
SELECT pid, state, query, query_start 
FROM pg_stat_activity 
WHERE state != 'idle';

-- Kill blocking queries if necessary
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE ...;
```

#### Migration Integrity Issues
```bash
# Check current status
make migrate-status

# Validate integrity
make migrate-validate

# Manual verification
make db-shell
SELECT * FROM schema_migrations ORDER BY version;
```

#### Version Conflicts
```bash
# Check for duplicates
ls -la src/db/migrations/

# Rename conflicting migration
mv V005__conflict.sql V006__resolved_conflict.sql
```

### Recovery Procedures

#### Complete Database Recovery
1. **Stop all services**: `make down`
2. **Restore from backup**: `make db-restore BACKUP_FILE=backup.sql`
3. **Verify restoration**: `make migrate-status`
4. **Restart services**: `make up`

#### Partial Migration Failure
1. **Identify failed migration**: Check logs
2. **Fix migration file**: Correct SQL errors
3. **Mark as failed in database**: Update schema_migrations table
4. **Re-run migrations**: `make migrate`

## Security Considerations

### Access Control
- Migration service runs with limited database privileges
- Production migrations require approval workflow
- All migration activities are logged and audited

### Data Protection
- Automatic backups before each migration
- Sensitive data handling in migrations
- Encryption for data in transit and at rest

## Performance Considerations

### Migration Performance
- **Index creation**: Use `CONCURRENTLY` for production
- **Large data updates**: Batch processing
- **Lock minimization**: Avoid long-running transactions

### Monitoring During Migrations
- CPU and memory usage
- Lock wait times
- Query performance impact
- Connection pool saturation

## Maintenance

### Regular Tasks
- **Weekly**: Validate migration integrity
- **Monthly**: Clean up old backup files
- **Quarterly**: Review and optimize migration performance

### Housekeeping
```bash
# Clean old backups (older than 30 days)
find backups/ -name "*.sql" -mtime +30 -delete

# Vacuum migration tables
make db-shell
VACUUM ANALYZE schema_migrations;
```

---

## Quick Reference

### Daily Commands
```bash
# Check current status
make migrate-status

# Apply pending migrations
make migrate

# Create new migration
python scripts/create_migration.py "your description"
```

### Emergency Commands
```bash
# Immediate backup
make db-backup

# Reset everything (DEV ONLY!)
make db-reset

# Restore from backup
make db-restore BACKUP_FILE=backup.sql
```

This migration strategy ensures database consistency, provides safety mechanisms, and enables confident deployments across all environments.