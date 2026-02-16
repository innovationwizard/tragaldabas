-- Disable automatic trigger for local development
-- For production, the trigger can be manually enabled after setting up the edge function URL

DROP TRIGGER IF EXISTS trigger_process_pipeline_job ON pipeline_jobs;

-- Comment: For production, you would enable this trigger with:
-- CREATE TRIGGER trigger_process_pipeline_job
--   AFTER INSERT ON pipeline_jobs
--   FOR EACH ROW
--   WHEN (NEW.status = 'pending')
--   EXECUTE FUNCTION notify_pipeline_job();
--
-- And configure:
-- ALTER DATABASE postgres SET app.settings.edge_function_url = 'https://[PROJECT-REF].supabase.co/functions/v1';
