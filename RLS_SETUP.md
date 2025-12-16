# Row Level Security (RLS) Setup Guide

This guide explains how to configure Row Level Security for Tragaldabas on Supabase.

## Overview

Since Tragaldabas uses **custom JWT authentication** (not Supabase Auth), RLS is configured to allow service role (your application) full access, while your application handles authorization via JWT verification.

## Quick Setup

### Option 1: Using SQL Script (Recommended)

1. **Open Supabase SQL Editor:**
   - Go to Supabase Dashboard → SQL Editor

2. **Run the simplified RLS script:**
   ```sql
   -- Copy and paste contents of scripts/setup_rls_simple.sql
   ```

   Or run via command line:
   ```bash
   psql $DATABASE_URL -f scripts/setup_rls_simple.sql
   ```

### Option 2: Using Python Script

```bash
python scripts/setup_rls.py
```

### Option 3: Manual Setup via Supabase Dashboard

1. Go to **Database** → **Tables**
2. For each table (`users`, `sessions`, `password_reset_tokens`):
   - Click on the table
   - Go to **Policies** tab
   - Click **Enable RLS**
   - Create policy: **Service role full access** (allow all operations)

## What Gets Configured

### Tables with RLS Enabled

1. **`users`** - User accounts
2. **`sessions`** - Active sessions
3. **`password_reset_tokens`** - Password reset tokens

### Policies Created

**Simplified Approach (Recommended):**
- Service role has full access to all tables
- Your application verifies JWT tokens before database operations
- Authorization is handled in application code, not at database level

**Why this approach?**
- Your custom JWT system doesn't integrate with Supabase's `auth.uid()`
- Application-level authorization is more flexible
- Service role key bypasses RLS (as intended)

## Verification

Check that RLS is enabled:

```bash
python scripts/setup_rls.py --verify
```

Or run SQL directly:

```sql
-- Check RLS status
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE tablename IN ('users', 'sessions', 'password_reset_tokens');

-- List policies
SELECT 
    tablename,
    policyname,
    cmd
FROM pg_policies
WHERE tablename IN ('users', 'sessions', 'password_reset_tokens');
```

## Advanced: User-Specific RLS

If you want to implement user-specific RLS policies (users can only see their own data), you'll need to:

1. **Create a function to extract user_id from JWT:**
   ```sql
   CREATE OR REPLACE FUNCTION get_current_user_id()
   RETURNS INTEGER AS $$
   BEGIN
       -- Extract user_id from JWT claim
       -- Adjust based on your JWT structure
       RETURN (current_setting('request.jwt.claims', true)::json->>'user_id')::INTEGER;
   END;
   $$ LANGUAGE plpgsql SECURITY DEFINER;
   ```

2. **Create user-specific policies:**
   ```sql
   CREATE POLICY "Users can view own data"
   ON users FOR SELECT
   USING (id = get_current_user_id());
   ```

3. **Set JWT claims in your application:**
   - When making database queries, set the JWT claims
   - This requires modifying your database connection to include JWT

**Note:** For most use cases, application-level authorization (current approach) is simpler and sufficient.

## Security Considerations

1. **Service Role Key:**
   - Keep `SUPABASE_SERVICE_ROLE_KEY` secret
   - Never expose it in client-side code
   - Use it only server-side

2. **JWT Verification:**
   - Always verify JWT tokens in your application before database operations
   - Check token expiration
   - Validate user permissions

3. **Database Access:**
   - Use connection pooling (PgBouncer)
   - Limit connection pool size
   - Monitor for connection leaks

## Troubleshooting

### RLS blocking queries?

- Check if service role key is being used
- Verify policies are created correctly
- Check Supabase Dashboard → Database → Policies

### Policies not applying?

- Ensure RLS is enabled: `ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;`
- Verify policies exist: `SELECT * FROM pg_policies WHERE tablename = 'table_name';`
- Check policy conditions match your use case

### Need to disable RLS temporarily?

```sql
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens DISABLE ROW LEVEL SECURITY;
```

**⚠️ Warning:** Only disable RLS for testing. Re-enable before production.

## Files

- `scripts/setup_rls.sql` - Full RLS setup with user-specific policies
- `scripts/setup_rls_simple.sql` - Simplified RLS (service role only) - **Recommended**
- `scripts/setup_rls.py` - Python script to setup/verify RLS

## Next Steps

After setting up RLS:

1. ✅ Verify RLS is enabled
2. ✅ Test authentication endpoints
3. ✅ Test pipeline operations
4. ✅ Monitor Supabase Dashboard for any blocked queries
5. ✅ Review logs for RLS violations

