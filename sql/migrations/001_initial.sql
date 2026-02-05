-- =============================================================================
-- Migration 001: Initial Schema
-- =============================================================================
-- Created: 2025-01-01
-- Description: Initial database schema for accounting automation system
-- =============================================================================

-- This migration creates the initial schema.
-- The full schema is in ../schema.sql and is loaded automatically
-- by docker-compose on first run.

-- This file serves as documentation of the initial state and can be used
-- for manual deployments or migrations from scratch.

-- Migration tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(50) PRIMARY KEY,
    applied_at  TIMESTAMP DEFAULT NOW(),
    description TEXT
);

-- Record this migration
INSERT INTO schema_migrations (version, description)
VALUES ('001_initial', 'Initial schema creation')
ON CONFLICT (version) DO NOTHING;

-- =============================================================================
-- Verification Queries
-- =============================================================================
-- Run these to verify the schema was created correctly:

-- Check all tables exist
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'transactions',
        'merchant_lookup',
        'budgets',
        'budget_alerts',
        'approval_log',
        'audit_log',
        'claude_api_log',
        'file_uploads'
    ];
    tbl TEXT;
    missing_tables TEXT[] := '{}';
BEGIN
    FOREACH tbl IN ARRAY expected_tables LOOP
        IF NOT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = tbl
        ) THEN
            missing_tables := array_append(missing_tables, tbl);
        END IF;
    END LOOP;

    IF array_length(missing_tables, 1) > 0 THEN
        RAISE WARNING 'Missing tables: %', missing_tables;
    ELSE
        RAISE NOTICE 'All expected tables exist';
    END IF;
END $$;

-- Check indexes exist
DO $$
DECLARE
    idx_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE schemaname = 'public';

    RAISE NOTICE 'Total indexes created: %', idx_count;
END $$;

-- Check views exist
DO $$
DECLARE
    view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public';

    RAISE NOTICE 'Total views created: %', view_count;
END $$;
