# Row Level Security (RLS) Setup Guide

This guide explains how to configure Row Level Security for Tragaldabas on Supabase.

## Overview

Tragaldabas uses **Supabase Auth** for authentication, which integrates seamlessly with Supabase RLS. This allows us to use `auth.uid()` directly in policies, making RLS setup much simpler than custom JWT systems.

## Quick Setup

### Option 1: Using SQL Script (Recommended)

1. **Open Supabase SQL Editor:**
   - Go to Supabase Dashboard → SQL Editor

2. **Run the Supabase Auth RLS script:**
   ```sql
   -- Copy and paste contents of scripts/setup_rls_supabase_auth.sql
   ```

   Or run via command line:
   ```bash
   psql $DATABASE_URL -f scripts/setup_rls_supabase_auth.sql
   ```

### Option 2: Manual Setup via Supabase Dashboard

1. Go to **Database** → **Tables**
2. For each table (`pipeline_jobs`, `users`, etc.):
   - Click on the table
   - Go to **Policies** tab
   - Click **Enable RLS**
   - Create policy: **Users can only access their own data**
     - Using `auth.uid() = user_id` for user-specific tables

## What Gets Configured

### Tables with RLS Enabled

1. **`pipeline_jobs`** - Pipeline execution jobs (user-specific)
2. **`users`** - User accounts (if using custom user table)
3. Any other user-specific tables

### Policies Created

**Supabase Auth Approach:**
- Users can only SELECT/INSERT/UPDATE/DELETE their own rows
- Uses `auth.uid()` to get current authenticated user ID
- Policies automatically apply based on Supabase Auth session

**Example Policy:**
```sql
CREATE POLICY "Users can view own pipeline jobs"
ON pipeline_jobs FOR SELECT
USING (auth.uid() = user_id);
```

**Why this approach?**
- Supabase Auth integrates natively with RLS
- `auth.uid()` automatically extracts user ID from JWT
- No custom functions needed
- More secure and maintainable

## Verification

Check that RLS is enabled:

```sql
-- Check RLS status
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('pipeline_jobs', 'users');

-- List policies
SELECT 
    tablename,
    policyname,
    cmd,
    qual as using_expression
FROM pg_policies
WHERE tablename IN ('pipeline_jobs', 'users');
```

## Policy Examples

### Pipeline Jobs Table

```sql
-- Users can only see their own jobs
CREATE POLICY "Users can view own pipeline jobs"
ON pipeline_jobs FOR SELECT
USING (auth.uid()::text = user_id);

-- Users can only create jobs for themselves
CREATE POLICY "Users can insert own pipeline jobs"
ON pipeline_jobs FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- Users can only update their own jobs
CREATE POLICY "Users can update own pipeline jobs"
ON pipeline_jobs FOR UPDATE
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- Users can only delete their own jobs
CREATE POLICY "Users can delete own pipeline jobs"
ON pipeline_jobs FOR DELETE
USING (auth.uid()::text = user_id);
```

**Note:** The `::text` cast is needed if `user_id` is stored as `text` (UUID string) rather than `uuid` type.

## Security Considerations

1. **Service Role Key:**
   - Keep `SUPABASE_SERVICE_ROLE_KEY` secret
   - Never expose it in client-side code
   - Use it only server-side for admin operations
   - Service role bypasses RLS (use carefully!)

2. **Anon Key:**
   - `SUPABASE_ANON_KEY` is safe for client-side use
   - RLS policies protect your data
   - Users can only access their own data

3. **Authentication:**
   - Always use Supabase Auth for user authentication
   - RLS automatically applies based on auth session
   - No need to manually verify tokens

4. **Database Access:**
   - Use connection pooling (PgBouncer)
   - Limit connection pool size
   - Monitor for connection leaks

## Troubleshooting

### RLS blocking queries?

- Verify user is authenticated: `SELECT auth.uid();`
- Check policies exist: `SELECT * FROM pg_policies WHERE tablename = 'pipeline_jobs';`
- Verify `user_id` column matches `auth.uid()` format (UUID)
- Check Supabase Dashboard → Database → Policies

### Policies not applying?

- Ensure RLS is enabled: `ALTER TABLE pipeline_jobs ENABLE ROW LEVEL SECURITY;`
- Verify policies exist: `SELECT * FROM pg_policies WHERE tablename = 'pipeline_jobs';`
- Check user is authenticated: `SELECT auth.uid();`
- Verify `user_id` column type matches `auth.uid()` (usually `text` or `uuid`)

### User ID mismatch?

If `user_id` is stored as `text` but `auth.uid()` returns `uuid`:
```sql
-- Cast to text in policy
USING (auth.uid()::text = user_id)
```

Or if `user_id` is `uuid`:
```sql
-- Cast to uuid
USING (auth.uid() = user_id::uuid)
```

### Need to disable RLS temporarily?

```sql
ALTER TABLE pipeline_jobs DISABLE ROW LEVEL SECURITY;
```

**⚠️ Warning:** Only disable RLS for testing. Re-enable before production.

## Files

- `scripts/setup_rls_supabase_auth.sql` - RLS setup for Supabase Auth - **Recommended**
- `scripts/setup_rls.sql` - Advanced RLS (for custom JWT - deprecated)
- `scripts/setup_rls_simple.sql` - Simplified RLS (for custom JWT - deprecated)
- `scripts/setup_rls.py` - Python script to setup/verify RLS

## Next Steps

After setting up RLS:

1. ✅ Verify RLS is enabled
2. ✅ Test authentication with Supabase Auth
3. ✅ Test pipeline operations (users should only see their own jobs)
4. ✅ Monitor Supabase Dashboard for any blocked queries
5. ✅ Review logs for RLS violations

## Migration from Custom JWT

If you're migrating from custom JWT auth:

1. Run `scripts/setup_rls_supabase_auth.sql` to create new policies
2. Drop old custom JWT policies (if any)
3. Update `user_id` column to match Supabase Auth UUID format
4. Test authentication flow

See `SUPABASE_AUTH_MIGRATION.md` for full migration guide.
