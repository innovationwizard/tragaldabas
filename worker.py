#!/usr/bin/env python3
"""
Pipeline Worker Service
Deploy this to Railway, Render, or Fly.io with requirements-full.txt
"""

from fastapi import FastAPI, HTTPException, Depends, Header
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


def verify_railway_api_key(authorization: Optional[str] = Header(None)):
    """Verify Railway API key from Authorization header"""
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
    return {"status": "ok", "service": "pipeline-worker"}


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
    
    try:
        return await process_job(job_id, request, mock_credentials)
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

