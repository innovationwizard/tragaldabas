#!/usr/bin/env python3
"""
Pipeline Worker Service
Deploy this to Railway, Render, or Fly.io with requirements-full.txt
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
from typing import Optional
import os

# Import the processing function from web.api
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import web.api modules - handle import errors gracefully
try:
    from web.api import process_job, get_job_from_db, update_job_in_db
    from config import settings
except ImportError as e:
    print(f"Warning: Could not import web.api: {e}")
    print("Make sure all dependencies are installed from requirements-full.txt")
    raise

app = FastAPI(title="Tragaldabas Pipeline Worker")

# CORS - allow calls from Vercel and Edge Functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "pipeline-worker"}


@app.post("/process/{job_id}")
async def worker_process(
    job_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Process pipeline job - called by Supabase Edge Function or Vercel API
    This worker has access to all pipeline dependencies
    """
    import sys
    print(f"🔵 Worker received request for job {job_id}", flush=True)
    print(f"🔵 Credentials present: {credentials is not None}", flush=True)
    
    # Verify service role key or user token
    if not credentials:
        print("❌ No credentials provided", flush=True)
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = credentials.credentials
    print(f"🔵 Token received, length: {len(token) if token else 0}", flush=True)
    
    # Check if SUPABASE_SERVICE_ROLE_KEY is set
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("❌ SUPABASE_SERVICE_ROLE_KEY not configured in worker", flush=True)
        raise HTTPException(status_code=500, detail="Worker configuration error: SUPABASE_SERVICE_ROLE_KEY not set")
    
    print(f"🔵 Expected key length: {len(settings.SUPABASE_SERVICE_ROLE_KEY)}", flush=True)
    
    # Check if it's a service role key
    if token != settings.SUPABASE_SERVICE_ROLE_KEY:
        print(f"❌ Token mismatch!", flush=True)
        print(f"   Received token length: {len(token)}, Expected length: {len(settings.SUPABASE_SERVICE_ROLE_KEY)}", flush=True)
        print(f"   Token starts with: {token[:20] if len(token) > 20 else token}...", flush=True)
        print(f"   Expected starts with: {settings.SUPABASE_SERVICE_ROLE_KEY[:20] if len(settings.SUPABASE_SERVICE_ROLE_KEY) > 20 else settings.SUPABASE_SERVICE_ROLE_KEY}...", flush=True)
        raise HTTPException(status_code=401, detail="Invalid service key - token does not match SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"✅ Authentication successful for job {job_id}", flush=True)
    
    # Call the process_job function from web.api
    # This will have access to all dependencies
    try:
        return await process_job(job_id, request, credentials)
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Worker error processing job {job_id}: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process job: {error_msg}")


if __name__ == "__main__":
    import uvicorn
    # Railway/Render set PORT environment variable
    port = int(os.getenv("PORT", 8000))
    # Bind to 0.0.0.0 to accept connections from outside container
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

