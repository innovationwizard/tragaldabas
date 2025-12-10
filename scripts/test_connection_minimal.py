#!/usr/bin/env python3
"""
Minimal connection test - no dependencies required
Just validates .env configuration

Usage:
    python scripts/test_connection_minimal.py
"""

import re
from pathlib import Path

def load_env_file(env_path):
    """Load .env file manually"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

def test_connection_string(url):
    """Validate connection string format"""
    print("Validating connection string format...")
    print("-" * 60)
    
    issues = []
    warnings = []
    
    # Check format
    if not url.startswith('postgresql://'):
        issues.append("Connection string should start with 'postgresql://'")
    
    # Check for Supabase
    if 'supabase.co' in url:
        print("✓ Supabase URL detected")
    else:
        warnings.append("URL doesn't appear to be Supabase")
    
    # Check for pooling
    if 'pgbouncer' in url.lower() or ':6543' in url:
        print("✓ Connection pooling detected (PgBouncer - recommended)")
    elif ':5432' in url:
        warnings.append("Using direct connection (port 5432). Consider pooling (port 6543)")
    
    # Check SSL
    if 'sslmode' in url:
        if 'sslmode=require' in url or 'sslmode=prefer' in url:
            print("✓ SSL mode configured")
        else:
            warnings.append("SSL mode set but not 'require' - Supabase requires SSL")
    else:
        warnings.append("SSL mode not specified - add ?sslmode=require")
    
    # Check for password
    if '@' in url:
        parts = url.split('@')
        if len(parts) >= 2:
            user_part = parts[0]
            if ':' in user_part:
                user, password = user_part.replace('postgresql://', '').split(':', 1)
                if not password or password == '[YOUR-PASSWORD]':
                    issues.append("Password appears to be placeholder - update with actual password")
                else:
                    print("✓ Password configured (hidden for security)")
    
    # Extract connection info (safely)
    try:
        match = re.search(r'@([^:]+):(\d+)/([^?]+)', url)
        if match:
            host = match.group(1)
            port = match.group(2)
            database = match.group(3)
            print(f"\nConnection Details:")
            print(f"  Host: {host}")
            print(f"  Port: {port}")
            print(f"  Database: {database}")
    except:
        pass
    
    return issues, warnings

def main():
    """Main test function"""
    print("="*60)
    print("Supabase Connection Test (Minimal)")
    print("="*60)
    print()
    
    # Find .env file
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print(f"✗ .env file not found at: {env_path}")
        print("\nCreate a .env file with:")
        print("  DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require")
        return 1
    
    print(f"✓ Found .env file: {env_path}")
    
    # Load environment variables
    env_vars = load_env_file(env_path)
    
    # Check DATABASE_URL
    database_url = env_vars.get('DATABASE_URL')
    
    if not database_url:
        print("\n✗ DATABASE_URL not found in .env file")
        print("\nAdd to .env:")
        print("  DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require")
        return 1
    
    print(f"\n✓ DATABASE_URL found in .env")
    
    # Validate connection string
    print()
    issues, warnings = test_connection_string(database_url)
    
    # Report issues
    if issues:
        print("\n" + "="*60)
        print("✗ Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    
    # Report warnings
    if warnings:
        print("\n" + "="*60)
        print("⚠ Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Summary
    print("\n" + "="*60)
    print("✓ Connection string format is valid!")
    print("="*60)
    
    print("\nTo test actual connection, install dependencies:")
    print("  pip install asyncpg python-dotenv")
    print("\nThen run:")
    print("  python scripts/test_connection.py")
    
    return 0

if __name__ == '__main__':
    exit(main())

