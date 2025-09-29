-- Migration V001: Initial Schema Setup
-- Description: Create initial database schema for Agent Test Orchestrator
-- Author: System
-- Date: 2024-09-29

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
$$ LANGUAGE plpgsql;

-- Create trigger for automatic updated_at updates
DROP TRIGGER IF EXISTS update_outcomes_updated_at ON orchestrator.outcomes;
CREATE TRIGGER update_outcomes_updated_at 
    BEFORE UPDATE ON orchestrator.outcomes 
    FOR EACH ROW EXECUTE FUNCTION orchestrator.update_updated_at_column();

-- Create extension for better JSONB support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create runs table for test execution tracking
CREATE TABLE IF NOT EXISTS orchestrator.runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    created_by VARCHAR(255),
    tags JSONB DEFAULT '[]'::jsonb
);

-- Create indexes for runs table
CREATE INDEX IF NOT EXISTS idx_runs_workflow_id ON orchestrator.runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON orchestrator.runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON orchestrator.runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_completed_at ON orchestrator.runs(completed_at);
CREATE INDEX IF NOT EXISTS idx_runs_created_by ON orchestrator.runs(created_by);

-- Create GIN index for JSONB columns for better search performance
CREATE INDEX IF NOT EXISTS idx_runs_input_data ON orchestrator.runs USING GIN (input_data);
CREATE INDEX IF NOT EXISTS idx_runs_output_data ON orchestrator.runs USING GIN (output_data);
CREATE INDEX IF NOT EXISTS idx_runs_tags ON orchestrator.runs USING GIN (tags);

-- Create updated_at trigger for runs table
CREATE TRIGGER update_runs_updated_at 
    BEFORE UPDATE ON orchestrator.runs 
    FOR EACH ROW EXECUTE FUNCTION orchestrator.update_updated_at_column();

-- Add updated_at column to runs table
ALTER TABLE orchestrator.runs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
