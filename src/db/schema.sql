"""Database schema definitions for PostgreSQL."""

# SQL schema for the orchestrator database
CREATE_SCHEMA_SQL = """
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

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION orchestrator.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS update_outcomes_updated_at 
    BEFORE UPDATE ON orchestrator.outcomes 
    FOR EACH ROW EXECUTE FUNCTION orchestrator.update_updated_at_column();

-- Create extension for better JSONB support if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
"""

# SQL for dropping the schema (useful for testing/cleanup)
DROP_SCHEMA_SQL = """
DROP SCHEMA IF EXISTS orchestrator CASCADE;
"""