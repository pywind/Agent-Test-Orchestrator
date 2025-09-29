# Database Backups Directory

This directory stores database backup files created by the migration system.

## Backup Files

Backup files are automatically named with timestamps:
- `backup-YYYYMMDD-HHMMSS.sql` - Automatic backups
- `pre-migration-YYYYMMDD.sql` - Pre-migration safety backups  
- Custom names can be specified with `make db-backup BACKUP_NAME=custom-name`

## Retention Policy

- Development: 7 days
- Staging: 30 days  
- Production: 90 days (with archive to long-term storage)

## Usage

```bash
# Create backup
make db-backup

# Create named backup
make db-backup BACKUP_NAME=before-major-change

# Restore from backup
make db-restore BACKUP_FILE=backups/backup-20240929-143022.sql
```

## Security

- Backup files may contain sensitive data
- Ensure appropriate file permissions (600)
- Do not commit backup files to version control
- Use encrypted storage for production backups