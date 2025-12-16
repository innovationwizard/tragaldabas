-- Database trigger to automatically process pipeline jobs
-- This creates a function that calls the Supabase Edge Function when a job is created

-- Create a function to notify about new jobs
CREATE OR REPLACE FUNCTION notify_pipeline_job()
RETURNS TRIGGER AS $$
BEGIN
  -- Use pg_net to call the Edge Function
  -- Note: This requires pg_net extension to be enabled
  PERFORM
    net.http_post(
      url := current_setting('app.settings.edge_function_url', true) || '/process-pipeline',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key', true)
      ),
      body := jsonb_build_object('job_id', NEW.id)
    );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on pipeline_jobs table
DROP TRIGGER IF EXISTS trigger_process_pipeline_job ON pipeline_jobs;
CREATE TRIGGER trigger_process_pipeline_job
  AFTER INSERT ON pipeline_jobs
  FOR EACH ROW
  WHEN (NEW.status = 'pending')
  EXECUTE FUNCTION notify_pipeline_job();

-- Note: For this to work, you need to:
-- 1. Enable pg_net extension: CREATE EXTENSION IF NOT EXISTS pg_net;
-- 2. Set app.settings.edge_function_url: ALTER DATABASE postgres SET app.settings.edge_function_url = 'https://[PROJECT-REF].supabase.co/functions/v1';
-- 3. Set app.settings.service_role_key (or use a safer method)

