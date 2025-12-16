-- Row Level Security (RLS) Setup for Tragaldabas
-- Run this script in Supabase SQL Editor or via psql

-- ============================================================================
-- 1. Enable RLS on all tables
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2. Create helper function to get current user ID from JWT
-- ============================================================================
-- Note: This assumes you're using Supabase's built-in JWT or a custom claim
-- For custom JWT, you may need to adjust this function

CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS INTEGER AS $$
DECLARE
    user_id INTEGER;
BEGIN
    -- Try to get user_id from JWT claim (adjust claim name as needed)
    -- For custom JWT, you might store user_id in a different claim
    SELECT (current_setting('request.jwt.claims', true)::json->>'user_id')::INTEGER INTO user_id;
    
    -- If not found, try 'sub' claim (Supabase Auth standard)
    IF user_id IS NULL THEN
        SELECT (current_setting('request.jwt.claims', true)::json->>'sub')::INTEGER INTO user_id;
    END IF;
    
    RETURN user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 3. Users Table Policies
-- ============================================================================

-- Policy: Users can view their own data
CREATE POLICY "Users can view own data"
ON users FOR SELECT
USING (id = get_current_user_id());

-- Policy: Users can update their own data (except sensitive fields)
CREATE POLICY "Users can update own data"
ON users FOR UPDATE
USING (id = get_current_user_id())
WITH CHECK (
    id = get_current_user_id()
    -- Prevent users from changing their own role or status
    AND (role = (SELECT role FROM users WHERE id = get_current_user_id()))
    AND (status = (SELECT status FROM users WHERE id = get_current_user_id()))
);

-- Policy: Service role has full access (for server-side operations)
CREATE POLICY "Service role full access"
ON users FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role')
WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Policy: Allow public registration (INSERT only)
CREATE POLICY "Allow public registration"
ON users FOR INSERT
WITH CHECK (true);

-- ============================================================================
-- 4. Sessions Table Policies
-- ============================================================================

-- Policy: Users can view their own sessions
CREATE POLICY "Users can view own sessions"
ON sessions FOR SELECT
USING (user_id = get_current_user_id());

-- Policy: Users can delete their own sessions (logout)
CREATE POLICY "Users can delete own sessions"
ON sessions FOR DELETE
USING (user_id = get_current_user_id());

-- Policy: Service role has full access
CREATE POLICY "Service role full access sessions"
ON sessions FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role')
WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Policy: Allow session creation (INSERT) - needed for login
CREATE POLICY "Allow session creation"
ON sessions FOR INSERT
WITH CHECK (true);

-- ============================================================================
-- 5. Password Reset Tokens Table Policies
-- ============================================================================

-- Policy: Users cannot view their own reset tokens (security)
-- Only service role can access these
CREATE POLICY "Service role only for reset tokens"
ON password_reset_tokens FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role')
WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- ============================================================================
-- 6. Alternative: Simplified RLS for Custom JWT System
-- ============================================================================
-- If the above doesn't work with your custom JWT, use this simpler approach:

-- Drop existing policies if needed
-- DROP POLICY IF EXISTS "Users can view own data" ON users;
-- DROP POLICY IF EXISTS "Users can update own data" ON users;
-- DROP POLICY IF EXISTS "Service role full access" ON users;
-- DROP POLICY IF EXISTS "Allow public registration" ON users;
-- DROP POLICY IF EXISTS "Users can view own sessions" ON sessions;
-- DROP POLICY IF EXISTS "Users can delete own sessions" ON sessions;
-- DROP POLICY IF EXISTS "Service role full access sessions" ON sessions;
-- DROP POLICY IF EXISTS "Allow session creation" ON sessions;
-- DROP POLICY IF EXISTS "Service role only for reset tokens" ON password_reset_tokens;

-- Simplified: Allow all operations for authenticated users
-- (Your application will handle authorization via JWT verification)
-- CREATE POLICY "Authenticated users full access"
-- ON users FOR ALL
-- USING (get_current_user_id() IS NOT NULL)
-- WITH CHECK (get_current_user_id() IS NOT NULL);

-- ============================================================================
-- 7. Grant necessary permissions
-- ============================================================================

-- Grant usage on sequences
GRANT USAGE ON SEQUENCE users_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE sessions_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE password_reset_tokens_id_seq TO authenticated;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE ON users TO authenticated;
GRANT SELECT, INSERT, DELETE ON sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON password_reset_tokens TO authenticated;

-- ============================================================================
-- 8. Verify RLS is enabled
-- ============================================================================

-- Check RLS status
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE tablename IN ('users', 'sessions', 'password_reset_tokens')
ORDER BY tablename;

-- List all policies
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename IN ('users', 'sessions', 'password_reset_tokens')
ORDER BY tablename, policyname;

