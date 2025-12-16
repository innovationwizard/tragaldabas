# Supabase Edge Functions Setup for Pipeline Processing

## Problem

Vercel serverless functions don't support long-running background tasks. When `asyncio.create_task()` is used, the task is killed when the function returns.

## Solution: Supabase Edge Functions

Use Supabase Edge Functions to process pipeline jobs. Edge Functions run in Deno and can make HTTP calls to your Vercel API.

## Setup Steps

### 1. Install Supabase CLI

```bash
npm install -g supabase
```

### 2. Initialize Supabase Functions (if not already done)

```bash
supabase init
```

### 3. Create Edge Function

The Edge Function is already created at `supabase/functions/process-pipeline/index.ts`.

### 4. Deploy Edge Function

```bash
supabase functions deploy process-pipeline
```

### 5. Set Environment Variables

In Supabase Dashboard → Edge Functions → process-pipeline → Settings:

- `VERCEL_API_URL`: Your Vercel API URL (e.g., `https://tragaldabas.vercel.app`)
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key

### 6. Configure Database Trigger (Optional)

The migration file `supabase/migrations/20250101000000_add_pipeline_trigger.sql` creates a trigger that automatically calls the Edge Function when a new job is created.

To use it:

1. Enable pg_net extension:
```sql
CREATE EXTENSION IF NOT EXISTS pg_net;
```

2. Set configuration (or use Supabase Secrets):
```sql
-- Note: These settings need to be configured in Supabase Dashboard
-- Go to Database → Settings → Database Settings
```

3. Run the migration:
```bash
supabase db push
```

### 7. Manual Processing Endpoint

Alternatively, you can manually trigger processing by calling:

```bash
curl -X POST https://[PROJECT-REF].supabase.co/functions/v1/process-pipeline \
  -H "Authorization: Bearer [ANON_KEY]" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "your-job-id"}'
```

## Architecture

```
User Uploads File
    ↓
Vercel API (/api/pipeline/upload)
    ↓
Creates job in Supabase DB (status: pending)
    ↓
[Option 1] Database Trigger → Supabase Edge Function
[Option 2] Manual Call → Supabase Edge Function
    ↓
Edge Function calls Vercel API (/api/pipeline/process/{job_id})
    ↓
Vercel API processes job synchronously
    ↓
Updates job status in Supabase DB
```

## Alternative: Direct Processing in Edge Function

For better performance, you could rewrite the pipeline processing logic in TypeScript/Deno and run it directly in the Edge Function. However, this requires porting the Python code.

## Current Limitations

1. **File Storage**: Files uploaded to Vercel `/tmp` are ephemeral. You need to:
   - Store files in Supabase Storage
   - Download them in the Edge Function or processing endpoint
   - Or use a persistent storage solution

2. **Authentication**: The Edge Function needs to authenticate with Vercel API. Currently using service role key, but you may need to implement proper JWT validation.

3. **Timeout**: Vercel serverless functions have a 10-second timeout on Hobby plan, 60 seconds on Pro. Long-running pipelines may need to be split into smaller chunks or use a different approach.

## Recommended Next Steps

1. **Store files in Supabase Storage** instead of `/tmp`
2. **Update upload endpoint** to upload to Supabase Storage
3. **Update processing endpoint** to download from Supabase Storage
4. **Deploy Edge Function** and test the flow
5. **Set up database trigger** for automatic processing

