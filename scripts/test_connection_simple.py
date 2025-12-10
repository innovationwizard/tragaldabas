#!/usr/bin/env python3
"""
Simple connection test - checks .env configuration first

Usage:
    python scripts/test_connection_simple.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def test_env_config():
    """Test environment configuration"""
    print("Testing Supabase connection configuration...")
    print("="*60)
    
    # Check if .env exists
    if not env_path.exists():
        print("✗ .env file not found")
        print(f"  Expected location: {env_path}")
        return 1
    
    print(f"✓ Found .env file: {env_path}")
    
    # Check DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("\n✗ DATABASE_URL not set in .env file")
        print("  Please add: DATABASE_URL=postgresql://...")
        return 1
    
    print(f"\n✓ DATABASE_URL is configured")
    
    # Parse connection string
    print("\nConnection String Analysis:")
    print("-" * 60)
    
    # Check for Supabase indicators
    is_supabase = False
    is_pooling = False
    
    if 'supabase.co' in database_url:
        is_supabase = True
        print("✓ Supabase URL detected")
    
    if 'pgbouncer' in database_url.lower() or ':6543' in database_url:
        is_pooling = True
        print("✓ Connection pooling detected (PgBouncer)")
    
    if ':5432' in database_url and not is_pooling:
        print("⚠ Direct connection (port 5432) - consider using pooling (port 6543)")
    
    # Check SSL
    if 'sslmode' in database_url:
        print("✓ SSL mode specified")
    else:
        print("⚠ SSL mode not specified - Supabase requires SSL")
        print("  Add: ?sslmode=require to connection string")
    
    # Extract connection details (safely, without password)
    try:
        # Parse URL format: postgresql://user:pass@host:port/db
        if '@' in database_url:
            parts = database_url.split('@')
            if len(parts) == 2:
                user_part = parts[0].replace('postgresql://', '')
                host_part = parts[1].split('/')[0]
                
                if ':' in user_part:
                    user = user_part.split(':')[0]
                    print(f"\nUser: {user}")
                
                if ':' in host_part:
                    host, port = host_part.rsplit(':', 1)
                    print(f"Host: {host}")
                    print(f"Port: {port}")
                else:
                    print(f"Host: {host_part}")
                
                if '/' in parts[1]:
                    db = parts[1].split('/')[1].split('?')[0]
                    print(f"Database: {db}")
    except Exception as e:
        print(f"Could not parse connection string: {e}")
    
    # Test if asyncpg is available
    print("\n" + "="*60)
    print("Checking dependencies...")
    
    try:
        import asyncpg
        print("✓ asyncpg is installed")
        
        # Now try actual connection test
        print("\n" + "="*60)
        print("Attempting connection test...")
        return test_actual_connection(database_url)
        
    except ImportError:
        print("✗ asyncpg not installed")
        print("\nTo install dependencies:")
        print("  pip install -r requirements.txt")
        print("\nOr install asyncpg directly:")
        print("  pip install asyncpg")
        print("\nConnection string looks valid, but cannot test without asyncpg.")
        return 0  # Return 0 because config is OK, just missing dependency


async def test_connection_async(database_url):
    """Test actual database connection"""
    import asyncpg
    
    try:
        # Test connection
        conn = await asyncpg.connect(database_url, timeout=10)
        
        # Test query
        result = await conn.fetchrow("SELECT version(), current_database(), current_user, now()")
        
        print("✓ Connection successful!")
        print(f"\nPostgreSQL Version: {result[0]}")
        print(f"Database: {result[1]}")
        print(f"User: {result[2]}")
        print(f"Server Time: {result[3]}")
        
        await conn.close()
        return 0
        
    except asyncpg.InvalidPasswordError:
        print("✗ Authentication failed - check password")
        return 1
    except asyncpg.PostgresConnectionError as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if IP is allowlisted in Supabase Dashboard")
        print("  2. Verify connection string is correct")
        print("  3. Check if project is active")
        return 1
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return 1


def test_actual_connection(database_url):
    """Wrapper for async connection test"""
    import asyncio
    return asyncio.run(test_connection_async(database_url))


def main():
    """Main entry point"""
    try:
        result = test_env_config()
        return result
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

