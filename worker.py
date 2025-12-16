#!/usr/bin/env python3
"""
Pipeline Worker Service
Deploy this to Railway, Render, or Fly.io with requirements-full.txt
"""

from fastapi import FastAPI, HTTPException
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
    # Verify service role key or user token
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = credentials.credentials
    
    # Check if it's a service role key
    if token != settings.SUPABASE_SERVICE_ROLE_KEY:
        # Could also verify user tokens here if needed
        raise HTTPException(status_code=401, detail="Invalid service key")
    
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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

