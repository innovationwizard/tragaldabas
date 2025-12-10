#!/usr/bin/env python3
"""
Test Supabase database connection

Usage:
    python scripts/test_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.supabase import SupabaseManager
from config import settings


async def test_connection():
    """Test database connection"""
    print("Testing Supabase connection...")
    print(f"Connection string: {settings.DATABASE_URL[:50]}..." if settings.DATABASE_URL else "No DATABASE_URL configured")
    print()
    
    if not settings.DATABASE_URL:
        print("✗ DATABASE_URL not configured in .env file")
        print("  Please set DATABASE_URL in your .env file")
        return 1
    
    try:
        db = SupabaseManager(settings.DATABASE_URL)
        
        # Test basic connection
        print("1. Testing basic connection...")
        result = await db.execute_one("SELECT version(), current_database(), current_user, now()")
        
        if result:
            print("   ✓ Connection successful!")
            print(f"   PostgreSQL version: {result[0]}")
            print(f"   Database: {result[1]}")
            print(f"   User: {result[2]}")
            print(f"   Server time: {result[3]}")
        else:
            print("   ✗ Connection failed: No result returned")
            return 1
        
        # Test health check
        print("\n2. Running health check...")
        health = await db.check_connection_health()
        
        if health["status"] == "healthy":
            print("   ✓ Database is healthy")
            if "pool" in health:
                pool = health["pool"]
                if "size" in pool:
                    print(f"   Pool size: {pool.get('size', 'N/A')}")
                    print(f"   Idle connections: {pool.get('idle', 'N/A')}")
                    print(f"   Active connections: {pool.get('active', 'N/A')}")
        else:
            print(f"   ✗ Database health check failed: {health.get('error', 'unknown')}")
            return 1
        
        # Test query execution
        print("\n3. Testing query execution...")
        test_query = "SELECT 1 as test_value, 'Connection test' as message"
        result = await db.execute_one(test_query)
        
        if result and result[0] == 1:
            print("   ✓ Query execution successful")
            print(f"   Result: {result}")
        else:
            print("   ✗ Query execution failed")
            return 1
        
        # Test table existence (check if auth tables exist)
        print("\n4. Checking auth tables...")
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'sessions', 'password_reset_tokens')
            ORDER BY table_name
        """
        tables = await db.execute(tables_query)
        
        if tables:
            print(f"   ✓ Found {len(tables)} auth table(s):")
            for table in tables:
                table_name = table[0] if isinstance(table, tuple) else table.get('table_name', 'unknown')
                print(f"     - {table_name}")
        else:
            print("   ⚠ No auth tables found (this is OK if you haven't run migrations yet)")
        
        # Test connection pool (if using pooling)
        if "pgbouncer" in settings.DATABASE_URL.lower() or "6543" in settings.DATABASE_URL:
            print("\n5. Connection pooling detected (PgBouncer)...")
            print("   ✓ Using connection pooling")
            print("   Note: Some admin operations may require direct connection")
        
        print("\n" + "="*50)
        print("✓ All connection tests passed!")
        print("="*50)
        return 0
        
    except Exception as e:
        print(f"\n✗ Connection test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify DATABASE_URL in .env file")
        print("  2. Check if password is correct")
        print("  3. Verify IP allowlist in Supabase Dashboard")
        print("  4. Check if SSL is required (sslmode=require)")
        print("  5. Ensure project is active in Supabase")
        
        import traceback
        print("\nFull error:")
        traceback.print_exc()
        return 1


def main():
    """Main entry point"""
    try:
        result = asyncio.run(test_connection())
        return result
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

