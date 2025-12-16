# Edge Function Setup Complete ✅

## Deployment Status

✅ **Edge Function deployed successfully!**
- Function: `process-pipeline`
- Project: `ncrgbzxypujhzhbhzvbv`
- Dashboard: https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv/functions

## Next Steps

### 1. Set Environment Variables in Supabase Dashboard

Go to: **Edge Functions** → **process-pipeline** → **Settings** → **Secrets**

Add these three secrets:

1. **VERCEL_API_URL**
   ```
   https://tragaldabas.vercel.app
   ```
   (Or your Vercel deployment URL)

2. **SUPABASE_URL**
   ```
   https://ncrgbzxypujhzhbhzvbv.supabase.co
   ```
   (Your Supabase project URL)

3. **SUPABASE_SERVICE_ROLE_KEY**
   ```
   [Your service role key from .env file]
   ```
   (Get this from your `.env` file: `SUPABASE_SERVICE_ROLE_KEY`)

### 2. Test the Function

You can test the Edge Function with:

```bash
curl -X POST https://ncrgbzxypujhzhbhzvbv.supabase.co/functions/v1/process-pipeline \
  -H 'Authorization: Bearer YOUR_ANON_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"job_id": "your-job-id"}'
```

### 3. How It Works

1. **User uploads file** → Creates job in database with status `pending`
2. **Edge Function is triggered** (manually or via database trigger)
3. **Edge Function calls** `/api/pipeline/process/{job_id}` on Vercel
4. **Vercel API processes** the pipeline job
5. **Job status updates** in Supabase database

### 4. Automatic Processing (Optional)

To automatically process jobs when created, set up the database trigger:

```sql
-- Enable pg_net extension
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Run the migration
-- See: supabase/migrations/20250101000000_add_pipeline_trigger.sql
```

Or manually trigger processing after upload by calling the Edge Function.

## Current Flow

```
Upload File
    ↓
Create Job (status: pending)
    ↓
[Manual] Call Edge Function OR [Auto] Database Trigger
    ↓
Edge Function → Vercel API (/api/pipeline/process/{job_id})
    ↓
Pipeline Processing
    ↓
Job Status Updated (running → completed/failed)
```

## Troubleshooting

### Function returns 401
- Check that `SUPABASE_SERVICE_ROLE_KEY` is set correctly in Edge Function secrets
- Verify the key matches your `.env` file

### Function returns 404
- Make sure the job_id exists in the database
- Check that the job status is `pending` or `failed`

### Function returns 500
- Check Vercel logs for processing errors
- Verify file exists (files in `/tmp` are ephemeral - consider using Supabase Storage)

## File Storage Note

⚠️ **Important**: Files uploaded to Vercel's `/tmp` directory are ephemeral and will be lost when the function terminates. For production:

1. **Store files in Supabase Storage** during upload
2. **Download files** in the processing endpoint before running pipeline
3. **Update upload endpoint** to use Supabase Storage

See `docs/SUPABASE_EDGE_FUNCTIONS.md` for more details.

