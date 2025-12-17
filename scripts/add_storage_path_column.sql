-- Add storage_path column to pipeline_jobs table
-- This column stores the path in Supabase Storage where the uploaded file is stored

ALTER TABLE pipeline_jobs 
ADD COLUMN IF NOT EXISTS storage_path TEXT;

-- Add comment for documentation
COMMENT ON COLUMN pipeline_jobs.storage_path IS 'Path in Supabase Storage bucket "uploads" (e.g., "user_id/job_id/filename")';

