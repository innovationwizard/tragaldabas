# Deploy Supabase Edge Function

## Quick Deploy

### Option 1: Using the Script

```bash
./scripts/deploy_edge_function.sh
```

### Option 2: Manual Steps

1. **Login to Supabase**:
   ```bash
   supabase login
   ```
   This will open a browser for authentication.

2. **Link Your Project** (if not already linked):
   ```bash
   supabase link --project-ref YOUR_PROJECT_REF
   ```
   You can find your project ref in your Supabase Dashboard URL or in your `.env` file's `SUPABASE_URL`.

3. **Deploy the Function**:
   ```bash
   supabase functions deploy process-pipeline --no-verify-jwt
   ```

4. **Set Environment Variables**:
   Go to Supabase Dashboard → Edge Functions → `process-pipeline` → Settings → Secrets:
   
   - `VERCEL_API_URL`: `https://tragaldabas.vercel.app` (or your Vercel URL)
   - `SUPABASE_URL`: Your Supabase project URL (from `.env`)
   - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key (from `.env`)

## Verify Deployment

Test the function:

```bash
curl -X POST https://YOUR_PROJECT_REF.supabase.co/functions/v1/process-pipeline \
  -H 'Authorization: Bearer YOUR_ANON_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"job_id": "test-job-id"}'
```

## Troubleshooting

### "Access token not provided"
- Run `supabase login` first
- Or set `SUPABASE_ACCESS_TOKEN` environment variable

### "Project not linked"
- Run `supabase link --project-ref YOUR_PROJECT_REF`
- Or create a `supabase/config.toml` file (auto-generated when linking)

### Function not found
- Make sure the function exists at `supabase/functions/process-pipeline/index.ts`
- Check that you're in the project root directory

## Next Steps

After deploying:
1. ✅ Set environment variables in Supabase Dashboard
2. ✅ Test the function with a test job
3. ✅ (Optional) Set up database trigger for automatic processing (see `supabase/migrations/20250101000000_add_pipeline_trigger.sql`)

