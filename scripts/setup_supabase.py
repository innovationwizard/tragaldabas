#!/usr/bin/env python3
"""
Setup script for Supabase integration

This script helps set up Row Level Security, indexes, and initial configuration
for Tragaldabas on Supabase.

Usage:
    python scripts/setup_supabase.py
    python scripts/setup_supabase.py --enable-rls
    python scripts/setup_supabase.py --create-indexes
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.supabase import SupabaseManager
from config import settings


async def setup_rls(db: SupabaseManager):
    """Enable Row Level Security on auth tables"""
    print("Enabling Row Level Security...")
    
    tables = [
        ("users", "public"),
        ("sessions", "public"),
        ("password_reset_tokens", "public")
    ]
    
    for table, schema in tables:
        try:
            await db.enable_rls(table, schema)
            print(f"  ✓ Enabled RLS on {schema}.{table}")
        except Exception as e:
            print(f"  ✗ Failed to enable RLS on {schema}.{table}: {e}")


async def create_rls_policies(db: SupabaseManager):
    """Create RLS policies for auth tables"""
    print("Creating RLS policies...")
    
    # Users table policies
    policies = [
        {
            "table": "users",
            "name": "Users can view own data",
            "definition": "FOR SELECT USING (auth.uid() = id)"
        },
        {
            "table": "users",
            "name": "Users can update own data",
            "definition": "FOR UPDATE USING (auth.uid() = id)"
        },
        {
            "table": "sessions",
            "name": "Users can view own sessions",
            "definition": "FOR SELECT USING (auth.uid() = user_id)"
        },
        {
            "table": "sessions",
            "name": "Users can delete own sessions",
            "definition": "FOR DELETE USING (auth.uid() = user_id)"
        }
    ]
    
    for policy in policies:
        try:
            await db.create_rls_policy(
                policy["table"],
                policy["name"],
                policy["definition"]
            )
            print(f"  ✓ Created policy: {policy['name']}")
        except Exception as e:
            print(f"  ✗ Failed to create policy {policy['name']}: {e}")


async def create_indexes(db: SupabaseManager):
    """Create performance indexes"""
    print("Creating indexes...")
    
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
    
    for index_sql, description in indexes:
        try:
            await db.execute_write(index_sql)
            print(f"  ✓ Created index: {description}")
        except Exception as e:
            print(f"  ✗ Failed to create index {description}: {e}")


async def check_health(db: SupabaseManager):
    """Check database health"""
    print("Checking database health...")
    
    health = await db.check_connection_health()
    
    if health["status"] == "healthy":
        print(f"  ✓ Database is healthy")
        print(f"    PostgreSQL: {health.get('postgres_version', 'unknown')}")
        print(f"    Database: {health.get('database', 'unknown')}")
        print(f"    User: {health.get('user', 'unknown')}")
        
        if "pool" in health and "size" in health["pool"]:
            pool = health["pool"]
            print(f"    Pool: {pool.get('active', 0)}/{pool.get('size', 0)} connections")
    else:
        print(f"  ✗ Database is unhealthy: {health.get('error', 'unknown error')}")
        return False
    
    return True


async def show_table_sizes(db: SupabaseManager):
    """Show table sizes"""
    print("\nTable Sizes:")
    
    tables = ["users", "sessions", "password_reset_tokens"]
    
    for table in tables:
        try:
            size_info = await db.get_table_size(table)
            if size_info:
                print(f"  {table}:")
                print(f"    Total: {size_info.get('total_size', 'N/A')}")
                print(f"    Rows: {size_info.get('row_count', 'N/A')}")
        except Exception as e:
            print(f"  ✗ Failed to get size for {table}: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Setup Supabase for Tragaldabas"
    )
    parser.add_argument(
        '--enable-rls',
        action='store_true',
        help='Enable Row Level Security'
    )
    parser.add_argument(
        '--create-policies',
        action='store_true',
        help='Create RLS policies'
    )
    parser.add_argument(
        '--create-indexes',
        action='store_true',
        help='Create performance indexes'
    )
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Check database health'
    )
    parser.add_argument(
        '--show-sizes',
        action='store_true',
        help='Show table sizes'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all setup tasks'
    )
    
    args = parser.parse_args()
    
    if not settings.DATABASE_URL:
        print("✗ DATABASE_URL not configured. Set it in .env file")
        return 1
    
    db = SupabaseManager(settings.DATABASE_URL)
    
    try:
        # Health check first
        if args.health_check or args.all:
            healthy = await check_health(db)
            if not healthy:
                return 1
        
        # Setup tasks
        if args.enable_rls or args.all:
            await setup_rls(db)
        
        if args.create_policies or args.all:
            await create_rls_policies(db)
        
        if args.create_indexes or args.all:
            await create_indexes(db)
        
        if args.show_sizes or args.all:
            await show_table_sizes(db)
        
        if not any([args.enable_rls, args.create_policies, args.create_indexes, 
                   args.health_check, args.show_sizes, args.all]):
            parser.print_help()
            return 0
        
        print("\n✓ Setup complete!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(asyncio.run(main()))

