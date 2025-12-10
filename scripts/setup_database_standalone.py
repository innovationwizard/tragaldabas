#!/usr/bin/env python3
"""
Standalone database setup script
Creates auth tables, indexes, and RLS policies

Usage:
    python scripts/setup_database_standalone.py
"""

import asyncio
import asyncpg
import re
from pathlib import Path


def load_database_url():
    """Load DATABASE_URL from .env file"""
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print(f"✗ .env file not found at: {env_path}")
        return None
    
    database_url = None
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('DATABASE_URL='):
                database_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                break
    
    return database_url


async def setup_tables(conn):
    """Create authentication tables"""
    print("Creating authentication tables...")
    
    tables_sql = [
        # Users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            role VARCHAR(20) DEFAULT 'user',
            status VARCHAR(20) DEFAULT 'pending_verification',
            email_verified BOOLEAN DEFAULT FALSE,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            password_changed_at TIMESTAMP
        );
        """,
        
        # Sessions table
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            device_info VARCHAR(255),
            ip_address VARCHAR(45),
            user_agent TEXT,
            expires_at TIMESTAMP NOT NULL,
            refresh_expires_at TIMESTAMP NOT NULL,
            revoked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        # Password reset tokens table
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
    
    for sql in tables_sql:
        try:
            await conn.execute(sql)
            print("  ✓ Table created/verified")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
    
    return True


async def create_indexes(conn):
    """Create performance indexes"""
    print("\nCreating indexes...")
    
    indexes = [
        ("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)", "users.email"),
        ("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)", "users.username"),
        ("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)", "sessions.user_id"),
        ("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)", "sessions.token"),
        ("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)", "sessions.expires_at"),
        ("CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens(token)", "password_reset_tokens.token"),
        ("CREATE INDEX IF NOT EXISTS idx_reset_tokens_user_id ON password_reset_tokens(user_id)", "password_reset_tokens.user_id"),
        ("""
         CREATE INDEX IF NOT EXISTS idx_sessions_active 
         ON sessions(user_id, expires_at) 
         WHERE revoked = FALSE AND expires_at > NOW()
         """, "sessions.active")
    ]
    
    success_count = 0
    for index_sql, description in indexes:
        try:
            await conn.execute(index_sql)
            print(f"  ✓ {description}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {description}: {e}")
    
    return success_count == len(indexes)


async def enable_rls(conn):
    """Enable Row Level Security"""
    print("\nEnabling Row Level Security...")
    
    tables = ["users", "sessions", "password_reset_tokens"]
    success_count = 0
    
    for table in tables:
        try:
            await conn.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            print(f"  ✓ Enabled RLS on {table}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed on {table}: {e}")
    
    return success_count == len(tables)


async def create_rls_policies(conn):
    """Create RLS policies (optional - may require Supabase auth extension)"""
    print("\nCreating RLS policies...")
    print("  Note: Policies may require Supabase auth extension")
    
    policies = [
        {
            "table": "users",
            "name": "Users can view own data",
            "sql": "FOR SELECT USING (auth.uid() = id)"
        },
        {
            "table": "users",
            "name": "Users can update own data",
            "sql": "FOR UPDATE USING (auth.uid() = id)"
        },
        {
            "table": "sessions",
            "name": "Users can view own sessions",
            "sql": "FOR SELECT USING (auth.uid() = user_id)"
        },
        {
            "table": "sessions",
            "name": "Users can delete own sessions",
            "sql": "FOR DELETE USING (auth.uid() = user_id)"
        }
    ]
    
    success_count = 0
    for policy in policies:
        try:
            sql = f'CREATE POLICY "{policy["name"]}" ON {policy["table"]} {policy["sql"]};'
            await conn.execute(sql)
            print(f"  ✓ {policy['name']}")
            success_count += 1
        except Exception as e:
            # RLS policies may fail if auth extension not available
            # This is OK for standalone setup
            print(f"  ⚠ {policy['name']}: {e}")
            print("     (This is OK if Supabase auth extension is not enabled)")
    
    return True  # Don't fail if policies can't be created


async def verify_setup(conn):
    """Verify tables were created"""
    print("\nVerifying setup...")
    
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('users', 'sessions', 'password_reset_tokens')
        ORDER BY table_name
    """)
    
    if len(tables) == 3:
        print("  ✓ All 3 auth tables exist")
        for table in tables:
            print(f"    - {table['table_name']}")
        return True
    else:
        print(f"  ⚠ Found {len(tables)} tables (expected 3)")
        return False


async def main():
    """Main setup function"""
    print("="*60)
    print("Database Setup - Tragaldabas")
    print("="*60)
    print()
    
    # Load connection string
    database_url = load_database_url()
    
    if not database_url:
        print("Please set DATABASE_URL in .env file")
        return 1
    
    # Add SSL if not present
    if 'sslmode' not in database_url:
        separator = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{separator}sslmode=require"
    
    try:
        print("Connecting to database...")
        conn = await asyncpg.connect(database_url, timeout=10)
        print("✓ Connected\n")
        
        # Run setup steps
        success = True
        
        if not await setup_tables(conn):
            success = False
        
        if not await create_indexes(conn):
            success = False
        
        if not await enable_rls(conn):
            success = False
        
        await create_rls_policies(conn)  # Don't fail on this
        
        if not await verify_setup(conn):
            success = False
        
        await conn.close()
        
        print("\n" + "="*60)
        if success:
            print("✓ Database setup completed successfully!")
            print("="*60)
            print("\nNext steps:")
            print("  1. Test authentication: python main.py auth register")
            print("  2. Check Supabase Dashboard for tables")
            return 0
        else:
            print("⚠ Setup completed with warnings")
            print("="*60)
            return 0  # Still return 0 as tables are created
        
    except asyncpg.InvalidPasswordError:
        print("✗ Authentication failed - check password")
        return 1
    except asyncpg.PostgresConnectionError as e:
        print(f"✗ Connection failed: {e}")
        return 1
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    try:
        exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\nSetup interrupted")
        exit(1)

