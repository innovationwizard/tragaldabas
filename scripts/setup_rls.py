"""Setup Row Level Security (RLS) for Supabase"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import DatabaseManager
from config import settings


async def setup_rls():
    """Setup RLS policies for authentication tables"""
    
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL not set in environment")
        return False
    
    db = DatabaseManager(settings.DATABASE_URL)
    
    try:
        print("🔐 Setting up Row Level Security...")
        
        # Enable RLS on tables
        print("  Enabling RLS on users table...")
        await db.execute_write("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
        
        print("  Enabling RLS on sessions table...")
        await db.execute_write("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;")
        
        print("  Enabling RLS on password_reset_tokens table...")
        await db.execute_write("ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;")
        
        # Create simplified policies (service role has full access)
        # Since we're using custom JWT, authorization is handled in application code
        
        print("  Creating RLS policies...")
        
        # Users table policies
        await db.execute_write("""
            DROP POLICY IF EXISTS "Service role full access users" ON users;
            CREATE POLICY "Service role full access users"
            ON users FOR ALL
            USING (true)
            WITH CHECK (true);
        """)
        
        # Sessions table policies
        await db.execute_write("""
            DROP POLICY IF EXISTS "Service role full access sessions" ON sessions;
            CREATE POLICY "Service role full access sessions"
            ON sessions FOR ALL
            USING (true)
            WITH CHECK (true);
        """)
        
        # Password reset tokens policies
        await db.execute_write("""
            DROP POLICY IF EXISTS "Service role full access reset tokens" ON password_reset_tokens;
            CREATE POLICY "Service role full access reset tokens"
            ON password_reset_tokens FOR ALL
            USING (true)
            WITH CHECK (true);
        """)
        
        print("✅ RLS setup complete!")
        print("\nNote: Since you're using custom JWT authentication,")
        print("authorization is handled in your application code.")
        print("RLS policies allow service role (your app) full access.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up RLS: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_rls():
    """Verify RLS is enabled and policies exist"""
    
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return False
    
    db = DatabaseManager(settings.DATABASE_URL)
    
    try:
        print("🔍 Verifying RLS configuration...")
        
        # Check RLS status
        result = await db.execute("""
            SELECT 
                tablename,
                rowsecurity as rls_enabled
            FROM pg_tables
            WHERE tablename IN ('users', 'sessions', 'password_reset_tokens')
            ORDER BY tablename;
        """)
        
        print("\nRLS Status:")
        if result:
            for row in result:
                # asyncpg returns Record objects with attribute access
                table_name = getattr(row, 'tablename', None) or row[0]
                enabled = getattr(row, 'rls_enabled', None) or row[1]
                status = "✅ Enabled" if enabled else "❌ Disabled"
                print(f"  {table_name}: {status}")
        
        # Check policies
        policies = await db.execute("""
            SELECT 
                tablename,
                policyname,
                cmd
            FROM pg_policies
            WHERE tablename IN ('users', 'sessions', 'password_reset_tokens')
            ORDER BY tablename, policyname;
        """)
        
        print("\nRLS Policies:")
        if policies:
            for row in policies:
                table_name = getattr(row, 'tablename', None) or row[0]
                policy_name = getattr(row, 'policyname', None) or row[1]
                cmd = getattr(row, 'cmd', None) or row[2]
                print(f"  {table_name}.{policy_name}: {cmd}")
        else:
            print("  No policies found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying RLS: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Row Level Security for Supabase")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify RLS configuration instead of setting it up"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        success = asyncio.run(verify_rls())
    else:
        success = asyncio.run(setup_rls())
    
    sys.exit(0 if success else 1)

