#!/usr/bin/env python3
"""
Helper script to process pending jobs in local development
In production, the Railway worker does this automatically
"""

import os
import sys
import asyncio
import httpx
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
API_BASE_URL = os.getenv("VITE_BASE_URL", "http://localhost:8000")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def process_pending_jobs():
    """Get all pending jobs and trigger processing"""
    print("🔍 Looking for pending jobs...")

    try:
        # Get all pending jobs
        response = supabase.table("pipeline_jobs")\
            .select("id,filename,status")\
            .eq("status", "pending")\
            .execute()

        jobs = response.data

        if not jobs:
            print("✅ No pending jobs found")
            return

        print(f"📋 Found {len(jobs)} pending job(s)")

        async with httpx.AsyncClient(timeout=300.0) as client:
            for job in jobs:
                job_id = job["id"]
                filename = job["filename"]
                print(f"\n🚀 Processing: {filename} ({job_id})")

                # Call the process endpoint with service role key for authentication
                try:
                    url = f"{API_BASE_URL}/api/pipeline/process/{job_id}"
                    headers = {
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json"
                    }

                    print(f"   Calling: {url}")
                    response = await client.post(url, headers=headers)

                    if response.status_code == 200:
                        print(f"✅ Completed: {filename}")
                    else:
                        print(f"❌ Error processing {filename}: HTTP {response.status_code}")
                        print(f"   Response: {response.text}")

                except Exception as e:
                    print(f"❌ Error processing {filename}: {e}")
                    import traceback
                    traceback.print_exc()

        print(f"\n✅ All jobs processed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("📦 Local Job Processor")
    print("=" * 60)
    asyncio.run(process_pending_jobs())
