-- Create pipeline_jobs table
CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
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
    error TEXT,
    storage_path TEXT,
    app_generation BOOLEAN DEFAULT FALSE,
    batch_id TEXT,
    batch_order INTEGER,
    batch_total INTEGER,
    etl_status TEXT,
    etl_target_db_url TEXT,
    etl_error TEXT,
    etl_result JSONB,
    etl_started_at TIMESTAMP,
    etl_completed_at TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_user_id ON pipeline_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status ON pipeline_jobs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_created_at ON pipeline_jobs(created_at);

-- Enable RLS
ALTER TABLE pipeline_jobs ENABLE ROW LEVEL SECURITY;

-- Create policies (for now, allow all - adjust based on your auth setup)
CREATE POLICY "Enable all operations for authenticated users"
ON pipeline_jobs
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

CREATE POLICY "Enable all operations for anon users"
ON pipeline_jobs
FOR ALL
TO anon
USING (true)
WITH CHECK (true);
