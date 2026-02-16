#!/usr/bin/env python3
"""Test local Supabase connection"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("=" * 60)
print("🧪 Testing Local Supabase Connection")
print("=" * 60)
print(f"URL: {SUPABASE_URL}")
print(f"Key: {SUPABASE_KEY[:20]}..." if SUPABASE_KEY else "Key: Not set")
print()

try:
    # Create Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client created successfully")

    # Test table access
    response = supabase.table("pipeline_jobs").select("*").execute()
    print(f"✅ Table access successful - {len(response.data)} rows found")

    # Test insert
    test_job = {
        "id": "test-123",
        "user_id": "test-user",
        "filename": "test.xlsx",
        "status": "pending"
    }

    insert_response = supabase.table("pipeline_jobs").insert(test_job).execute()
    print(f"✅ Insert successful - created job with id: {insert_response.data[0]['id']}")

    # Test update
    update_response = supabase.table("pipeline_jobs").update({"status": "completed"}).eq("id", "test-123").execute()
    print(f"✅ Update successful - updated {len(update_response.data)} row(s)")

    # Test delete
    delete_response = supabase.table("pipeline_jobs").delete().eq("id", "test-123").execute()
    print(f"✅ Delete successful - deleted {len(delete_response.data)} row(s)")

    print()
    print("=" * 60)
    print("🎉 All tests passed! Local Supabase is ready.")
    print("=" * 60)
    print()
    print("📋 Next steps:")
    print("1. Start your development server")
    print("2. Your app will now use local Supabase")
    print("3. Access Supabase Studio: http://127.0.0.1:54323")
    print("4. To stop: supabase stop")
    print("5. To restart: supabase start")
    print()
    print("💡 To switch back to production:")
    print("   - Edit .env and uncomment production Supabase credentials")
    print("   - Comment out the LOCAL SUPABASE section")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
