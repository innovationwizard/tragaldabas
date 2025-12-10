#!/usr/bin/env python3
"""
Check setup status and dependencies

Usage:
    python scripts/check_setup.py
"""

import importlib
import sys
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("="*60)
    print("Dependency Check")
    print("="*60)
    
    required = {
        'Core': ['pydantic', 'pydantic_settings'],
        'Data Processing': ['pandas', 'numpy', 'openpyxl', 'docx'],
        'LLM Providers': ['anthropic', 'openai', 'google.generativeai'],
        'Database': ['asyncpg'],
        'Authentication': ['bcrypt', 'argon2', 'jwt'],
        'Utilities': ['rapidfuzz', 'chardet', 'dateutil'],
        'Output': ['pptx'],
        'CLI': ['click', 'colorama', 'tabulate'],
        'Configuration': ['dotenv']
    }
    
    all_installed = True
    missing = {}
    
    for category, modules in required.items():
        cat_missing = []
        for mod in modules:
            try:
                importlib.import_module(mod)
            except ImportError:
                cat_missing.append(mod)
                all_installed = False
        if cat_missing:
            missing[category] = cat_missing
    
    if missing:
        print("\n✗ Missing Dependencies:")
        for cat, mods in missing.items():
            print(f"  {cat}:")
            for mod in mods:
                print(f"    - {mod}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("\n✓ All required dependencies installed")
        return True


def check_database_setup():
    """Check database setup status"""
    print("\n" + "="*60)
    print("Database Setup Status")
    print("="*60)
    
    try:
        import asyncio
        import asyncpg
        from pathlib import Path
        
        async def check():
            env_path = Path('.env')
            if not env_path.exists():
                print("\n✗ .env file not found")
                return False
            
            database_url = None
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        database_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
            
            if not database_url:
                print("\n✗ DATABASE_URL not configured")
                return False
            
            if 'sslmode' not in database_url:
                separator = '&' if '?' in database_url else '?'
                database_url = f"{database_url}{separator}sslmode=require"
            
            conn = await asyncpg.connect(database_url, timeout=10)
            
            # Check tables
            tables = await conn.fetch('''
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'sessions', 'password_reset_tokens')
                ORDER BY table_name
            ''')
            
            # Check indexes
            indexes = await conn.fetch('''
                SELECT COUNT(*) as count
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename IN ('users', 'sessions', 'password_reset_tokens')
            ''')
            
            # Check RLS
            rls = await conn.fetch('''
                SELECT tablename, rowsecurity 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename IN ('users', 'sessions', 'password_reset_tokens')
                ORDER BY tablename
            ''')
            
            await conn.close()
            
            print(f"\nTables: {len(tables)}/3")
            if len(tables) == 3:
                for table in tables:
                    print(f"  ✓ {table['table_name']} ({table['column_count']} columns)")
            else:
                print("  ✗ Missing tables")
                return False
            
            print(f"\nIndexes: {indexes[0]['count']} created")
            if indexes[0]['count'] >= 7:
                print("  ✓ Sufficient indexes")
            else:
                print("  ⚠ Some indexes may be missing")
            
            print(f"\nRLS Status:")
            all_rls_enabled = True
            for r in rls:
                status = '✓' if r['rowsecurity'] else '✗'
                print(f"  {status} {r['tablename']}")
                if not r['rowsecurity']:
                    all_rls_enabled = False
            
            if len(tables) == 3 and all_rls_enabled:
                print("\n✓ Database setup is COMPLETE")
                return True
            else:
                print("\n⚠ Database setup incomplete")
                return False
        
        return asyncio.run(check())
        
    except ImportError:
        print("\n⚠ Cannot check database (asyncpg not installed)")
        return None
    except Exception as e:
        print(f"\n✗ Database check failed: {e}")
        return False


def check_env_config():
    """Check environment configuration"""
    print("\n" + "="*60)
    print("Environment Configuration")
    print("="*60)
    
    env_path = Path('.env')
    if not env_path.exists():
        print("\n✗ .env file not found")
        return False
    
    print(f"\n✓ .env file exists: {env_path}")
    
    required_vars = ['DATABASE_URL']
    optional_vars = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY', 'JWT_SECRET_KEY']
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    print("\nRequired variables:")
    all_required = True
    for var in required_vars:
        if var in content:
            print(f"  ✓ {var}")
        else:
            print(f"  ✗ {var} (MISSING)")
            all_required = False
    
    print("\nOptional variables (at least one LLM key recommended):")
    has_llm_key = False
    for var in optional_vars:
        if var in content and 'your-' not in content.lower():
            print(f"  ✓ {var}")
            if 'API_KEY' in var:
                has_llm_key = True
        else:
            print(f"  - {var} (not set)")
    
    if not all_required:
        return False
    
    if not has_llm_key:
        print("\n⚠ No LLM API keys configured (needed for pipeline stages)")
    
    return True


def main():
    """Main check function"""
    print("\n" + "="*60)
    print("Tragaldabas Setup Status Check")
    print("="*60)
    
    deps_ok = check_dependencies()
    env_ok = check_env_config()
    db_ok = check_database_setup()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    status = []
    if deps_ok:
        status.append("✓ Dependencies")
    else:
        status.append("✗ Dependencies")
    
    if env_ok:
        status.append("✓ Environment")
    else:
        status.append("✗ Environment")
    
    if db_ok is True:
        status.append("✓ Database")
    elif db_ok is False:
        status.append("✗ Database")
    else:
        status.append("⚠ Database (cannot check)")
    
    for s in status:
        print(f"  {s}")
    
    print("\n" + "="*60)
    
    if deps_ok and env_ok and db_ok:
        print("✓ Setup is COMPLETE - Ready to use!")
        return 0
    else:
        print("⚠ Setup incomplete - See details above")
        return 1


if __name__ == '__main__':
    exit(main())

