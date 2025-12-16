-- Simplified RLS Setup for Custom JWT Authentication
-- This version bypasses RLS for server-side operations
-- Your application handles authorization via JWT verification

-- ============================================================================
-- Enable RLS
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Policy: Allow all operations for service role
-- ============================================================================
-- Since you're using custom JWT, the service role key bypasses RLS
-- Your application verifies JWT tokens server-side before database operations

-- Users table: Service role has full access
CREATE POLICY "Service role full access users"
ON users FOR ALL
USING (true)
WITH CHECK (true);

-- Sessions table: Service role has full access
CREATE POLICY "Service role full access sessions"
ON sessions FOR ALL
USING (true)
WITH CHECK (true);

-- Password reset tokens: Service role has full access
CREATE POLICY "Service role full access reset tokens"
ON password_reset_tokens FOR ALL
USING (true)
WITH CHECK (true);

-- ============================================================================
-- Alternative: Disable RLS if using application-level authorization
-- ============================================================================
-- If you prefer to handle all authorization in your application code:

-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE password_reset_tokens DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Grant permissions
-- ============================================================================

GRANT USAGE ON SEQUENCE users_id_seq TO postgres, authenticated, anon;
GRANT USAGE ON SEQUENCE sessions_id_seq TO postgres, authenticated, anon;
GRANT USAGE ON SEQUENCE password_reset_tokens_id_seq TO postgres, authenticated, anon;

GRANT ALL ON users TO postgres, authenticated;
GRANT ALL ON sessions TO postgres, authenticated;
GRANT ALL ON password_reset_tokens TO postgres, authenticated;

