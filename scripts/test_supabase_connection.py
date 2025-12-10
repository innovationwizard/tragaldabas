#!/usr/bin/env python3
"""
Standalone Supabase connection test
Tests the connection string from .env file

Usage:
    python scripts/test_supabase_connection.py
"""

import asyncio
import re
import sys
from pathlib import Path

def load_env():
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

async def test_connection(database_url):
    """Test database connection"""
    try:
        import asyncpg
    except ImportError:
        print("✗ asyncpg not installed")
        print("  Install with: pip install asyncpg")
        return False
    
    print("Testing connection...")
    print(f"URL: {database_url[:50]}...")
    print()
    
    try:
        # Add SSL if not present
        if 'sslmode' not in database_url:
            separator = '&' if '?' in database_url else '?'
            database_url = f"{database_url}{separator}sslmode=require"
            print("Added sslmode=require to connection string")
        
        # Connect with timeout
        print("Connecting to database...")
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url, timeout=10),
            timeout=15
        )
        
        print("✓ Connected successfully!")
        print()
        
        # Test query
        print("Running test query...")
        result = await conn.fetchrow(
            "SELECT version(), current_database(), current_user, now()"
        )
        
        print("✓ Query executed successfully!")
        print()
        print("Database Information:")
        print(f"  PostgreSQL Version: {result[0]}")
        print(f"  Database Name: {result[1]}")
        print(f"  Current User: {result[2]}")
        print(f"  Server Time: {result[3]}")
        print()
        
        # Check if auth tables exist
        print("Checking for auth tables...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'sessions', 'password_reset_tokens')
            ORDER BY table_name
        """)
        
        if tables:
            print(f"✓ Found {len(tables)} auth table(s):")
            for table in tables:
                print(f"    - {table['table_name']}")
        else:
            print("  No auth tables found (run migrations if needed)")
        
        await conn.close()
        print()
        print("="*60)
        print("✓ Connection test PASSED!")
        print("="*60)
        return True
        
    except asyncio.TimeoutError:
        print("✗ Connection timeout")
        print("  Check your network connection and Supabase project status")
        return False
    except asyncpg.InvalidPasswordError:
        print("✗ Authentication failed")
        print("  Check your password in the connection string")
        return False
    except asyncpg.PostgresConnectionError as e:
        print(f"✗ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify connection string in .env file")
        print("  2. Check IP allowlist in Supabase Dashboard")
        print("  3. Ensure project is active")
        print("  4. Verify password is correct")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    print("="*60)
    print("Supabase Connection Test")
    print("="*60)
    print()
    
    # Load connection string
    database_url = load_env()
    
    if not database_url:
        print("Please set DATABASE_URL in .env file")
        print("\nExample:")
        print("  DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require")
        return 1
    
    # Validate format
    if not database_url.startswith('postgresql://'):
        print("✗ Invalid connection string format")
        print("  Should start with: postgresql://")
        return 1
    
    # Test connection
    try:
        success = asyncio.run(test_connection(database_url))
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    exit(main())

