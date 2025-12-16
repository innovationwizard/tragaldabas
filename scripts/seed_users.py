#!/usr/bin/env python3
"""Seed test users to Supabase Auth"""

import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from config import settings

# Test users to create
TEST_USERS = [
    {"email": "condor@example.com", "password": "x", "username": "condor"},
    {"email": "estefani@example.com", "password": "2122", "username": "estefani"},
    {"email": "marco@example.com", "password": "eltiofavorito", "username": "marco"},
]


def seed_users():
    """Create test users in Supabase"""
    
    # Check if Supabase is configured
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: Supabase credentials not configured")
        print("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file")
        return False
    
    # Initialize Supabase client with service role key (admin access)
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )
    
    print("Creating test users...")
    print("-" * 50)
    
    created_count = 0
    error_count = 0
    
    for user_data in TEST_USERS:
        email = user_data["email"]
        password = user_data["password"]
        username = user_data["username"]
        
        try:
            # Create user using admin API
            response = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,  # Auto-confirm email
                "user_metadata": {
                    "username": username,
                    "full_name": username.capitalize()
                }
            })
            
            if response.user:
                print(f"✅ Created user: {username} ({email})")
                created_count += 1
            else:
                print(f"❌ Failed to create user: {username}")
                error_count += 1
                
        except Exception as e:
            # Check if user already exists
            if "already registered" in str(e).lower() or "already exists" in str(e).lower():
                print(f"⚠️  User already exists: {username} ({email})")
                # Try to update password
                try:
                    # Get user by email
                    users = supabase.auth.admin.list_users()
                    user = None
                    for u in users.users:
                        if u.email == email:
                            user = u
                            break
                    
                    if user:
                        # Update password
                        supabase.auth.admin.update_user_by_id(
                            user.id,
                            {"password": password}
                        )
                        print(f"✅ Updated password for: {username} ({email})")
                        created_count += 1
                    else:
                        print(f"❌ User exists but couldn't update: {username}")
                        error_count += 1
                except Exception as update_error:
                    print(f"❌ Error updating user {username}: {update_error}")
                    error_count += 1
            else:
                print(f"❌ Error creating user {username}: {e}")
                error_count += 1
    
    print("-" * 50)
    print(f"Summary: {created_count} users created/updated, {error_count} errors")
    
    return error_count == 0


if __name__ == "__main__":
    success = seed_users()
    sys.exit(0 if success else 1)

