-- Row Level Security (RLS) Setup for Supabase Auth
-- This script sets up RLS for application tables used with Supabase Auth

-- ============================================================================
-- 1. Create pipeline_jobs table (if it doesn't exist)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,  -- Supabase Auth UUID (text format)
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_stage INTEGER,
    current_stage_name TEXT,
    completed_stages INTEGER[] DEFAULT '{}',
    failed_stage INTEGER,
    questions JSONB,
    result JSONB,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_user_id ON pipeline_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status ON pipeline_jobs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_created_at ON pipeline_jobs(created_at);

-- ============================================================================
-- 2. Enable RLS on pipeline_jobs
-- ============================================================================

ALTER TABLE pipeline_jobs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 3. Pipeline Jobs Policies (using Supabase Auth)
-- ============================================================================

-- Users can view their own pipeline jobs
CREATE POLICY "Users can view own pipeline jobs"
ON pipeline_jobs FOR SELECT
USING (auth.uid()::text = user_id);

-- Users can create pipeline jobs for themselves
CREATE POLICY "Users can insert own pipeline jobs"
ON pipeline_jobs FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- Users can update their own pipeline jobs
CREATE POLICY "Users can update own pipeline jobs"
ON pipeline_jobs FOR UPDATE
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- Users can delete their own pipeline jobs
CREATE POLICY "Users can delete own pipeline jobs"
ON pipeline_jobs FOR DELETE
USING (auth.uid()::text = user_id);

-- ============================================================================
-- 4. Grant permissions
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON pipeline_jobs TO authenticated;

-- ============================================================================
-- Note: With Supabase Auth, you can use:
-- - auth.uid() - Get current user's UUID
-- - auth.email() - Get user's email
-- - auth.jwt() - Get full JWT claims
-- - auth.role() - Get user role ('authenticated', 'anon', 'service_role')
--
-- The ::text cast is needed because Supabase Auth UUIDs are stored as text
-- ============================================================================
