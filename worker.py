#!/usr/bin/env python3
"""
Pipeline Worker Service
Deploy this to Railway with requirements-full.txt
Rebuild timestamp: 2026-02-03T12:10:00Z
"""

import subprocess
import sys

# Startup debug signal for Railway logs
print("=" * 80, flush=True)
print("🚀 TRAGALDABAS WORKER STARTING", flush=True)
print("=" * 80, flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Rebuild timestamp: 2026-02-03T12:10:00Z", flush=True)

# Log git commit to verify deployment version
try:
    commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                         stderr=subprocess.DEVNULL).decode('utf-8').strip()
    print(f"✅ Git commit: {commit_hash}", flush=True)
except:
    print("⚠️  Git commit hash unavailable", flush=True)

# Verify the generator.py fix is present
try:
    with open('stages/s11_code_generation/generator.py', 'r') as f:
        lines = f.readlines()
        line_1265 = lines[1264].strip() if len(lines) > 1264 else "NOT FOUND"
        line_1266 = lines[1265].strip() if len(lines) > 1265 else "NOT FOUND"
        if 'f"z.object' in line_1265 and 'f"z.object' in line_1266:
            print("✅ GENERATOR.PY FIX VERIFIED - Lines 1265-1266 are correct!", flush=True)
        else:
            print(f"❌ GENERATOR.PY FIX MISSING!", flush=True)
            print(f"   Line 1265: {line_1265}", flush=True)
            print(f"   Line 1266: {line_1266}", flush=True)
except Exception as e:
    print(f"⚠️  Could not verify generator.py fix: {e}", flush=True)

print("=" * 80, flush=True)
print("", flush=True)

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
from typing import Optional
import os
import asyncio

# Import the processing function from web.api
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import config first (lightweight)
try:
    from config import settings
except ImportError as e:
    print(f"❌ Failed to import config: {e}", flush=True)
    import traceback
    print(traceback.format_exc(), flush=True)
    raise

# Lazy import web.api modules (only when needed)
# This prevents startup crashes if web.api has import issues
def get_process_job():
    """Lazy import process_job to avoid startup crashes"""
    try:
        from web.api import process_job
        return process_job
    except ImportError as e:
        print(f"❌ Failed to import process_job: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise


def get_process_etl_job():
    """Lazy import process_etl_job to avoid startup crashes"""
    try:
        from web.api import process_etl_job
        return process_etl_job
    except ImportError as e:
        print(f"❌ Failed to import process_etl_job: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise

def get_job_from_db(job_id: str):
    """Lazy import get_job_from_db"""
    from web.api import get_job_from_db as _get_job_from_db
    return _get_job_from_db(job_id)

def update_job_in_db(job_id: str, updates: dict):
    """Lazy import update_job_in_db"""
    from web.api import update_job_in_db as _update_job_in_db
    return _update_job_in_db(job_id, updates)

app = FastAPI(title="Tragaldabas Pipeline Worker")

# Log deploy metadata if available
print("Worker commit:", os.getenv("RAILWAY_GIT_COMMIT_SHA"), flush=True)

# CORS - allow calls from Vercel and Edge Functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def verify_railway_api_key(authorization: Optional[str] = Header(None)):
    """Verify Railway API key from Authorization header"""
    print(f"AUTH: {authorization}", flush=True)
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format. Expected 'Bearer <token>'")
    
    token = authorization.replace("Bearer ", "").strip()
    expected_key = os.getenv("RAILWAY_API_KEY")
    
    if not expected_key:
        print("❌ RAILWAY_API_KEY not configured", flush=True)
        raise HTTPException(status_code=500, detail="Worker configuration error: RAILWAY_API_KEY not set")
    
    if token != expected_key:
        print(f"❌ API key mismatch. Token length: {len(token)}, Expected length: {len(expected_key)}", flush=True)
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token


@app.get("/health")
async def health():
    """Health check endpoint"""
    health_info = {
        "status": "ok",
        "service": "pipeline-worker",
        "config": {
            "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
            "supabase_service_key_set": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "railway_api_key_set": bool(os.getenv("RAILWAY_API_KEY")),
        }
    }
    
    # Test imports
    try:
        from config import settings
        health_info["config"]["settings_loaded"] = True
    except Exception as e:
        health_info["config"]["settings_loaded"] = False
        health_info["config"]["settings_error"] = str(e)
    
    try:
        from web.api import get_job_from_db
        health_info["imports"]["web_api"] = True
    except Exception as e:
        health_info["imports"] = {"web_api": False, "error": str(e)}
    
    return health_info


@app.get("/test/{job_id}")
async def test_job_access(job_id: str):
    """Test endpoint to debug job access and file download"""
    try:
        print(f"🧪 Testing job access for {job_id}", flush=True)
        
        # Test get_job_from_db
        job = get_job_from_db(job_id)
        if not job:
            return {"error": "Job not found", "job_id": job_id}
        
        print(f"✅ Job found: {job.get('filename')}, storage_path={job.get('storage_path')}", flush=True)
        
        # Test file download
        storage_path = job.get("storage_path")
        if not storage_path:
            return {"error": "storage_path not set", "job": job}
        
        # Try to download file
        from web.api import supabase
        if not supabase:
            return {"error": "Supabase client not initialized"}
        
        print(f"📥 Attempting to download: {storage_path}", flush=True)
        file_data = supabase.storage.from_("uploads").download(storage_path)
        
        if file_data:
            file_size = len(file_data) if isinstance(file_data, bytes) else "unknown"
            return {
                "success": True,
                "job_id": job_id,
                "filename": job.get("filename"),
                "storage_path": storage_path,
                "file_size": file_size,
                "status": job.get("status")
            }
        else:
            return {"error": "File data is None", "storage_path": storage_path}
            
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.post("/process/{job_id}")
async def worker_process(
    job_id: str,
    request: Request,
    api_key: str = Depends(verify_railway_api_key)
):
    """
    Process pipeline job - called by Supabase Edge Function
    This worker has access to all pipeline dependencies
    """
    print(f"✅ Authentication successful for job {job_id}", flush=True)
    
    # Call the process_job function from web.api
    # This will have access to all dependencies
    # Create a mock credentials object for process_job (it needs the service role key)
    from fastapi.security import HTTPAuthorizationCredentials
    mock_credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=settings.SUPABASE_SERVICE_ROLE_KEY
    )
    
    # Lazy import process_job
    process_job_func = get_process_job()
    print("process_job_func file:", process_job_func.__code__.co_filename, flush=True)
    print("process_job_func module:", process_job_func.__module__, flush=True)

    # Start processing in background - don't wait for completion
    # This allows long-running genesis jobs to process while we return immediately
    # The frontend will poll for status updates
    async def process_in_background():
        try:
            print(f"🚀 Starting pipeline processing for job {job_id}", flush=True)
            await process_job_func(job_id, request, mock_credentials)
            print(f"✅ Pipeline completed successfully for job {job_id}", flush=True)
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"❌ Worker error processing job {job_id}: {error_msg}", flush=True)
            print(traceback.format_exc(), flush=True)

    # Fire and forget - start processing but return immediately
    asyncio.create_task(process_in_background())

    print(f"✅ Job {job_id} accepted and processing started in background", flush=True)
    return {"message": "Job processing started", "job_id": job_id}


@app.post("/etl/{job_id}")
async def worker_etl(
    job_id: str,
    request: Request,
    api_key: str = Depends(verify_railway_api_key)
):
    """Run ETL-only load for a job."""
    print(f"✅ ETL authentication successful for job {job_id}", flush=True)

    from fastapi.security import HTTPAuthorizationCredentials
    mock_credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=settings.SUPABASE_SERVICE_ROLE_KEY
    )

    # Process ETL in background for consistency
    process_etl_func = get_process_etl_job()

    async def process_etl_in_background():
        try:
            print(f"🚀 Starting ETL processing for job {job_id}", flush=True)
            await process_etl_func(job_id, request, mock_credentials)
            print(f"✅ ETL completed successfully for job {job_id}", flush=True)
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"❌ Worker error processing ETL job {job_id}: {error_msg}", flush=True)
            print(traceback.format_exc(), flush=True)

    # Fire and forget
    asyncio.create_task(process_etl_in_background())

    print(f"✅ ETL job {job_id} accepted and processing started in background", flush=True)
    return {"message": "ETL processing started", "job_id": job_id}


if __name__ == "__main__":
    import uvicorn
    # Railway sets PORT environment variable
    port = int(os.getenv("PORT", 8000))
    # Bind to 0.0.0.0 to accept connections from outside container
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

