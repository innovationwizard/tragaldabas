-- Row Level Security (RLS) Setup for Supabase Auth
-- This is MUCH simpler than custom JWT!

-- ============================================================================
-- 1. Enable RLS on tables
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2. Users Table Policies (using Supabase Auth)
-- ============================================================================

-- Users can view their own data
CREATE POLICY "Users can view own data"
ON users FOR SELECT
USING (auth.uid() = id);

-- Users can update their own data
CREATE POLICY "Users can update own data"
ON users FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- Allow public registration (INSERT)
CREATE POLICY "Allow public registration"
ON users FOR INSERT
WITH CHECK (true);

-- ============================================================================
-- 3. Sessions Table Policies
-- ============================================================================

-- Users can view their own sessions
CREATE POLICY "Users can view own sessions"
ON sessions FOR SELECT
USING (auth.uid() = user_id);

-- Users can delete their own sessions
CREATE POLICY "Users can delete own sessions"
ON sessions FOR DELETE
USING (auth.uid() = user_id);

-- Allow session creation
CREATE POLICY "Allow session creation"
ON sessions FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- 4. Password Reset Tokens (service role only)
-- ============================================================================

-- Only service role can access reset tokens
CREATE POLICY "Service role only for reset tokens"
ON password_reset_tokens FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- 5. Grant permissions
-- ============================================================================

GRANT USAGE ON SEQUENCE users_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE sessions_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE password_reset_tokens_id_seq TO authenticated;

GRANT SELECT, INSERT, UPDATE ON users TO authenticated;
GRANT SELECT, INSERT, DELETE ON sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON password_reset_tokens TO authenticated;

-- ============================================================================
-- Note: With Supabase Auth, you can also use:
-- - auth.email() - Get user's email
-- - auth.jwt() - Get full JWT claims
-- - auth.role() - Get user role
-- ============================================================================

