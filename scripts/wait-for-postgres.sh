#!/bin/bash
set -e

# PostgreSQL connection parameters
PGHOST=${POSTGRES_HOST:-localhost}
PGPORT=${POSTGRES_PORT:-5432}
PGUSER=${POSTGRES_USER:-agent}
PGPASSWORD=${POSTGRES_PASSWORD:-password}
PGDATABASE=${POSTGRES_DB:-agent_orchestrator}

# Export for psql commands
export PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE

echo "Waiting for PostgreSQL to be ready..."

# Function to check if PostgreSQL is ready
check_postgres() {
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "SELECT 1" > /dev/null 2>&1
}

# Wait for PostgreSQL to be available
until check_postgres; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "PostgreSQL is up and running!"

# Check if target database exists, create if not
DB_EXISTS=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$PGDATABASE'")
if [[ -z "$DB_EXISTS" ]]; then
    echo "Creating database $PGDATABASE..."
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "CREATE DATABASE $PGDATABASE;"
fi

echo "PostgreSQL is ready for connections!"
