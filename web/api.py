"""FastAPI application with Supabase Auth"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import asyncio
import uuid
from pathlib import Path
import os
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

# Heavy dependencies imported lazily to reduce serverless function size
# from orchestrator import Orchestrator  # Lazy import
# from ui.progress import ProgressTracker  # Lazy import  
# from ui.prompts import UserPrompt  # Lazy import
from config import settings

# Initialize Supabase client
supabase: Optional[Client] = None
if SUPABASE_AVAILABLE and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")

security = HTTPBearer(auto_error=False)  # Don't auto-raise error, handle manually

app = FastAPI(
    title="Tragaldabas API",
    description="Universal Data Ingestor API",
    version="1.0.0"
)

# CORS middleware
# Allow origins from environment or default to localhost for development
# Also allow Vercel deployment URLs and production URLs
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    cors_origins_str += f",https://{vercel_url}"
# Add production URLs
cors_origins_str += ",https://tragaldabas.app,https://tragaldabas.vercel.app"
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files - serve frontend build
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    # Mount assets directory (Vite outputs JS/CSS here)
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Mount root static files (favicon, logo, etc.)
    # Note: We don't mount "/" here to avoid conflicts with catch-all route

# Helper functions for Supabase database operations
# Note: Supabase Python client is synchronous, so these are sync functions
def get_job_from_db(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job from Supabase database"""
    if not supabase:
        return None
    try:
        response = supabase.table("pipeline_jobs").select("*").eq("id", job_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        print(f"Error fetching job from DB: {e}")
    return None

async def update_job_in_db(job_id: str, updates: Dict[str, Any]) -> None:
    """Update job in Supabase database (async, non-blocking)"""
    if not supabase:
        raise RuntimeError(f"Supabase client not initialized, cannot update job {job_id}")

    updates["updated_at"] = datetime.utcnow().isoformat()
    print(f"💾 Updating job {job_id} with keys: {list(updates.keys())}", flush=True)

    def _do():
        return supabase.table("pipeline_jobs").update(updates).eq("id", job_id).execute()

    res = await asyncio.to_thread(_do)
    
    err = getattr(res, "error", None)
    data = getattr(res, "data", None)

    if err:
        raise RuntimeError(f"Supabase update error: {err}")
    if not data:
        raise RuntimeError(f"Supabase update affected 0 rows for job {job_id}")

    print(f"✅ Job {job_id} updated", flush=True)

def create_job_in_db(job_data: Dict[str, Any]):
    """Create job in Supabase database (synchronous)"""
    if not supabase:
        return
    try:
        supabase.table("pipeline_jobs").insert(job_data).execute()
    except Exception as e:
        print(f"Error creating job in DB: {e}")

def list_user_jobs_from_db(user_id: str) -> List[Dict[str, Any]]:
    """List all jobs for a user from Supabase database (synchronous)"""
    if not supabase:
        return []
    try:
        response = supabase.table("pipeline_jobs").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        print(f"Error listing jobs from DB: {e}")
        return []


# Pydantic models for request validation
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str  # Changed from email to username
    password: str


# Note: WebProgressTracker and WebUserPrompt are defined inside run_pipeline()
# to inherit from ProgressTracker and UserPrompt (lazy imports)

class WebUserPrompt:
    """Web-based user prompt - stores questions in Supabase database"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.pending_questions: List[Dict[str, Any]] = []
    
    async def yes_no(self, question: str) -> bool:
        """Store question and wait for response"""
        question_id = str(uuid.uuid4())
        self.pending_questions.append({
            "id": question_id,
            "type": "yes_no",
            "question": question
        })
        # Update questions in database
        await update_job_in_db(self.job_id, {"questions": self.pending_questions})
        # In real implementation, wait for user response via polling
        # For now, default to yes
        return True
        
    async def select_domain(self):
        """Domain selection"""
        # Would prompt user via polling/API
        from core.enums import Domain
        return Domain.FINANCIAL  # Default


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from Supabase Auth"""
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase Auth not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
        )
    
    token = credentials.credentials
    
    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Convert Supabase User object to dict
        user = user_response.user
        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata or {},
            "created_at": user.created_at,
            "email_confirmed": user.email_confirmed_at is not None
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# Auth endpoints (Supabase Auth)
@app.post("/api/auth/register")
async def register(user_data: RegisterRequest):
    """Register new user via Supabase Auth"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")
    
    try:
        # Register with Supabase Auth
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "username": user_data.username,
                    "full_name": user_data.full_name
                }
            }
        })
        
        if response.user:
            return {
                "message": "User created successfully",
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "email_confirmed": response.user.email_confirmed_at is not None,
                    "user_metadata": response.user.user_metadata
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Username to email mapping for test users
USERNAME_EMAIL_MAP = {
    "condor": "condor@example.com",
    "estefani": "estefani@example.com",
    "marco": "marco@example.com",
}

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Login user via Supabase Auth using username"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")
    
    try:
        # Look up email from username mapping
        user_email = USERNAME_EMAIL_MAP.get(login_data.username.lower())
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Login with Supabase Auth using the found email
        response = supabase.auth.sign_in_with_password({
            "email": user_email,
            "password": login_data.password
        })
        
        if response.user and response.session:
            return JSONResponse({
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {}
                }
            })
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
    except HTTPException:
        raise
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"Login error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/api/auth/logout")
async def logout(user: dict = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user via Supabase Auth"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")
    
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user info from Supabase Auth"""
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "user_metadata": user.get("user_metadata", {}),
        "created_at": user.get("created_at")
    }


# Pipeline endpoints
@app.post("/api/pipeline/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload file and start pipeline"""
    # Lazy import to reduce serverless function size
    from config import settings
    import tempfile
    
    job_id = str(uuid.uuid4())
    user_id = user.get("id")
    
    # Upload file to Supabase Storage (persistent, accessible from Railway worker)
    # Files in Vercel /tmp are ephemeral and not accessible from Railway
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        # Read file content
        content = await file.read()
        
        # Upload to Supabase Storage bucket "uploads"
        storage_path = f"{user_id}/{job_id}/{file.filename}"
        response = supabase.storage.from_("uploads").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": file.content_type or "application/octet-stream", "upsert": "true"}
        )
        
        # Check for upload errors
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Supabase Storage upload error: {response.error}")
        
        print(f"✅ File uploaded to Supabase Storage: {storage_path}", flush=True)
        
    except Exception as e:
        import traceback
        print(f"❌ Error uploading file to Supabase Storage: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    # Initialize job in Supabase database
    job_data = {
        "id": job_id,
        "user_id": user_id,
        "filename": file.filename,
        "status": "pending",
        "current_stage": None,
        "current_stage_name": None,
        "completed_stages": [],
        "questions": [],
        "storage_path": storage_path  # Store the storage path for later retrieval
    }
    
    # Create job in database (synchronous call)
    create_job_in_db(job_data)
    
    # Trigger Edge Function to process the job
    # Note: We await this call (with short timeout) because asyncio.create_task()
    # tasks are killed when Vercel serverless functions return
    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"
    
    try:
        import httpx
        print(f"🚀 Triggering Edge Function for job {job_id}", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:  # Short timeout to avoid blocking
            response = await client.post(
                edge_function_url,
                json={"job_id": job_id},
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
                    "Content-Type": "application/json"
                }
            )
            # Log response for debugging
            if response.status_code != 200:
                error_text = await response.text()
                print(f"❌ Edge Function error ({response.status_code}): {error_text}", flush=True)
            else:
                print(f"✅ Edge Function called successfully for job {job_id}", flush=True)
    except httpx.TimeoutException:
        # Timeout is OK - Edge Function will still process the job
        print(f"⚠️ Edge Function call timed out (non-critical), job {job_id} will be processed", flush=True)
    except Exception as e:
        print(f"⚠️ Warning: Could not trigger Edge Function: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        # Don't fail the upload if Edge Function call fails - job can be processed manually later
    
    return {"job_id": job_id, "status": "pending", "message": "Job created, processing will start shortly"}


@app.post("/api/pipeline/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """Manually trigger processing for a stuck job"""
    from config import settings
    import httpx
    
    # Get job from database
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify ownership
    if job.get("user_id") != user.get("id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if job can be retried
    if job.get("status") not in ["pending", "failed"]:
        return {
            "message": f"Job is already {job.get('status')}, cannot retry",
            "job_id": job_id,
            "status": job.get("status")
        }
    
    # Trigger Edge Function
    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"
    
    try:
        print(f"🔄 Retrying job {job_id}", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                edge_function_url,
                json={"job_id": job_id},
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code != 200:
                error_text = await response.text()
                print(f"❌ Edge Function error ({response.status_code}): {error_text}", flush=True)
                raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {error_text}")
            else:
                print(f"✅ Edge Function triggered successfully for job {job_id}", flush=True)
                return {
                    "message": "Job processing triggered",
                    "job_id": job_id
                }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Edge Function call timed out")
    except Exception as e:
        print(f"❌ Error retrying job {job_id}: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")


async def run_pipeline(job_id: str, file_path: str, user_id: str):
    """Run pipeline in background - lazy imports to reduce serverless function size"""
    # Lazy import heavy dependencies only when pipeline runs
    from orchestrator import Orchestrator
    from ui.progress import ProgressTracker
    from ui.prompts import UserPrompt
    from config import settings
    
    # Make WebProgressTracker inherit from ProgressTracker
    class WebProgressTracker(ProgressTracker):
        """Polling-based progress tracker - stores progress in Supabase database"""
        
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id
            self.current_stage = None
            self.stage_name = None
        
        async def start_stage(self, stage_num: int, stage_name: str):
            self.current_stage = stage_num
            self.stage_name = stage_name
            # Update job in database for polling
            await update_job_in_db(self.job_id, {
                "current_stage": stage_num,
                "current_stage_name": stage_name
            })
        
        async def complete_stage(self, stage_num: int):
            # Get current completed stages and update
            job = get_job_from_db(self.job_id)
            if job:
                completed = job.get("completed_stages", []) or []
                if stage_num not in completed:
                    completed.append(stage_num)
                    await update_job_in_db(self.job_id, {"completed_stages": completed})
        
        async def fail(self, stage_num: int, error: str):
            # Update job status in database
            await update_job_in_db(self.job_id, {
                "status": "failed",
                "error": error,
                "failed_stage": stage_num
            })
        
        async def complete(self):
            # Update job status in database
            await update_job_in_db(self.job_id, {
                "status": "completed",
                "current_stage": 7,  # Output stage
                "current_stage_name": "Output"
            })
    
    # Make WebUserPrompt inherit from UserPrompt
    class WebUserPrompt(UserPrompt):
        """Web-based user prompt - stores questions in Supabase database"""
        
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id
            self.pending_questions: List[Dict[str, Any]] = []
        
        async def yes_no(self, question: str) -> bool:
            """Store question and wait for response"""
            question_id = str(uuid.uuid4())
            self.pending_questions.append({
                "id": question_id,
                "type": "yes_no",
                "question": question
            })
            # Update questions in database
            await update_job_in_db(self.job_id, {"questions": self.pending_questions})
            # In real implementation, wait for user response via polling
            # For now, default to yes
            return True
        
        async def select_domain(self):
            """Domain selection"""
            # Would prompt user via polling/API
            from core.enums import Domain
            return Domain.FINANCIAL  # Default
    
    try:
        # Update job status to running
        await update_job_in_db(job_id, {"status": "running"})
        
        progress = WebProgressTracker(job_id)
        prompt = WebUserPrompt(job_id)
        
        orchestrator = Orchestrator(
            progress=progress,
            prompt=prompt,
            db_connection_string=settings.DATABASE_URL
        )
        
        ctx = await orchestrator.run(file_path)
        
        # Convert Pydantic models to dict (works for both v1 and v2)
        def to_dict(model):
            if model is None:
                return None
            if hasattr(model, 'model_dump'):
                return model.model_dump()
            elif hasattr(model, 'dict'):
                return model.dict()
            return str(model)
        
        result = {
            "reception": to_dict(ctx.reception),
            "classification": to_dict(ctx.classification),
            "structure": to_dict(ctx.structure),
            "archaeology": to_dict(ctx.archaeology),
            "reconciliation": to_dict(ctx.reconciliation),
            "etl": to_dict(ctx.etl),
            "analysis": to_dict(ctx.analysis),
            "output": to_dict(ctx.output),
        }
        
        # Update job with completed status and result (synchronous call)
        print(f"💾 Updating job {job_id} to completed status", flush=True)
        try:
            success = update_job_in_db(job_id, {
                "status": "completed",
                "result": result
            })
            if not success:
                raise Exception("update_job_in_db returned False")
            
            # Sanity check: verify the update actually persisted
            if supabase:
                check = supabase.table("pipeline_jobs").select("status,current_stage,completed_stages,updated_at").eq("id", job_id).execute()
                check_err = getattr(check, "error", None)
                check_data = getattr(check, "data", None)
                print(f"🔍 DB CHECK after completed update: data={check_data}, error={check_err}", flush=True)
                if check_err:
                    print(f"⚠️ Warning: Sanity check failed with error: {check_err}", flush=True)
                elif not check_data or len(check_data) == 0:
                    print(f"⚠️ Warning: Sanity check found no data for job {job_id}", flush=True)
                elif check_data[0].get("status") != "completed":
                    print(f"⚠️ Warning: Sanity check shows status is '{check_data[0].get('status')}', expected 'completed'", flush=True)
            
            print(f"✅ Job {job_id} status updated to completed", flush=True)
        except Exception as update_error:
            print(f"❌ Failed to update job status: {update_error}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            # Re-raise to ensure error is visible
            raise
        
    except Exception as e:
        # Update job with failed status and error
        error_msg = str(e)
        print(f"❌ Pipeline failed for job {job_id}: {error_msg}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        
        # Try to update status, but don't swallow the original exception
        try:
            await update_job_in_db(job_id, {
                "status": "failed",
                "error": error_msg
            })
            
            # Sanity check: verify the update actually persisted
            if supabase:
                def _check():
                    return supabase.table("pipeline_jobs").select("status,error,updated_at").eq("id", job_id).execute()
                check = await asyncio.to_thread(_check)
                check_err = getattr(check, "error", None)
                check_data = getattr(check, "data", None)
                print(f"🔍 DB CHECK after failed update: data={check_data}, error={check_err}", flush=True)
                if check_err:
                    print(f"⚠️ Warning: Sanity check failed with error: {check_err}", flush=True)
                elif not check_data or len(check_data) == 0:
                    print(f"⚠️ Warning: Sanity check found no data for job {job_id}", flush=True)
                elif check_data[0].get("status") != "failed":
                    print(f"⚠️ Warning: Sanity check shows status is '{check_data[0].get('status')}', expected 'failed'", flush=True)
            
            print(f"✅ Job {job_id} status updated to failed", flush=True)
        except Exception as update_error:
            print(f"❌ Failed to update job status to failed: {update_error}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            # Don't swallow - re-raise the original exception
        raise


@app.post("/api/pipeline/process/{job_id}")
async def process_job(
    job_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Process a pending pipeline job - can be called by Supabase Edge Function or worker"""
    
    # Get job from database
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check authentication - allow service role key from header for Edge Function calls
    user_id = None
    is_service_call = False
    
    if credentials:
        token = credentials.credentials
        # Try to verify as user token first
        try:
            if supabase:
                user_response = supabase.auth.get_user(token)
                if user_response.user:
                    user_id = user_response.user.id
        except:
            # If user auth fails, check if it's service role key
            if token == settings.SUPABASE_SERVICE_ROLE_KEY:
                is_service_call = True
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    else:
        # No credentials provided
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify ownership (skip if called with service key)
    if not is_service_call and user_id and job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already processing or completed
    if job.get("status") not in ["pending", "failed"]:
        return {"message": f"Job already {job.get('status')}", "job_id": job_id}
    
    # Download file from Supabase Storage
    # Files are stored in Supabase Storage, not in local filesystem
    filename = job.get("filename")
    storage_path = job.get("storage_path")
    
    if not filename:
        raise HTTPException(status_code=400, detail="Job filename not found")
    
    if not storage_path:
        # Fallback: reconstruct storage path from job data
        user_id = job.get("user_id")
        storage_path = f"{user_id}/{job_id}/{filename}"
        print(f"⚠️ Storage path not in job data, reconstructing: {storage_path}", flush=True)
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        # Download file from Supabase Storage
        print(f"📥 Downloading file from Supabase Storage: {storage_path}", flush=True)
        print(f"   Bucket: uploads", flush=True)
        print(f"   Full path: {storage_path}", flush=True)
        
        file_response = supabase.storage.from_("uploads").download(storage_path)
        
        if file_response is None:
            raise Exception("File data is None - file may not exist in Storage")
        
        # Handle both bytes and response objects
        if isinstance(file_response, bytes):
            file_data = file_response
        elif hasattr(file_response, 'read'):
            file_data = file_response.read()
        else:
            file_data = file_response
        
        if not file_data:
            raise Exception("File data is empty")
        
        print(f"   Downloaded {len(file_data)} bytes", flush=True)
        
        # Save to local filesystem for processing
        output_dir = settings.OUTPUT_DIR if settings.OUTPUT_DIR.startswith("/tmp") else "/tmp/output"
        local_upload_dir = Path(output_dir) / "uploads" / job_id
        local_upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = local_upload_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        print(f"✅ File downloaded and saved to: {file_path}", flush=True)
        print(f"   File size: {file_path.stat().st_size} bytes", flush=True)
        
    except Exception as e:
        import traceback
        error_msg = f"Failed to download file from Supabase Storage: {str(e)}"
        print(f"❌ {error_msg}", flush=True)
        print(traceback.format_exc(), flush=True)
        await update_job_in_db(job_id, {
            "status": "failed",
            "error": error_msg
        })
        raise HTTPException(status_code=404, detail=error_msg)
    
    # Run pipeline
    # Note: Pipeline processing requires heavy dependencies (pandas, numpy, LLM libraries)
    # which exceed Vercel's 250 MB limit. This endpoint should be called from a separate worker.
    try:
        user_id = job.get("user_id")  # Use job's user_id
        
        # Check if pipeline dependencies are available
        try:
            import pandas
            import numpy
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Pipeline processing unavailable. Heavy dependencies not installed. "
                       "Please use a separate worker service for pipeline processing. "
                       "See docs/DEPLOYMENT.md for options."
            )
        
        await run_pipeline(job_id, str(file_path), user_id)
        return {"message": "Job processed successfully", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error processing job {job_id}: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process job: {error_msg}")


@app.get("/api/pipeline/jobs")
async def list_jobs(user: dict = Depends(get_current_user)):
    """List user's pipeline jobs from Supabase database"""
    user_id = user.get("id")
    jobs = list_user_jobs_from_db(user_id)  # Synchronous call
    # Remove result field for list view (too large)
    user_jobs = [
        {k: v for k, v in job.items() if k != "result"}
        for job in jobs
    ]
    return {"jobs": user_jobs}


@app.get("/api/pipeline/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    """Get pipeline job details from Supabase database"""
    user_id = user.get("id")
    
    job = get_job_from_db(job_id)  # Synchronous call
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return job


@app.get("/api/pipeline/jobs/{job_id}/download/{file_type}")
async def download_output(job_id: str, file_type: str, user: dict = Depends(get_current_user)):
    """Download output files"""
    user_id = user.get("id")
    
    job = get_job_from_db(job_id)  # Synchronous call
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return file based on file_type (pptx, txt, sql, etc.)
    # Implementation depends on output structure
    return {"message": "Download endpoint - implement based on output structure"}


# Polling endpoint for progress updates
@app.get("/api/pipeline/jobs/{job_id}/status")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get current job status for polling from Supabase database"""
    user_id = user.get("id")
    
    job = get_job_from_db(job_id)  # Synchronous call
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "current_stage": job.get("current_stage"),
        "current_stage_name": job.get("current_stage_name"),
        "completed_stages": job.get("completed_stages", []) or [],
        "error": job.get("error"),
        "updated_at": job.get("updated_at")
    }


# Serve frontend (catch-all route for SPA)
# This must be last to catch all non-API routes
# FastAPI matches routes in order, so explicit API routes above will be matched first
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend app - handles all non-API routes"""
    # Note: API routes are matched first by FastAPI, so this only handles non-API routes
    # The check below is just a safety measure
    
    # Check if this is a static file request (JS, CSS, images, etc.)
    # Note: /assets/* requests are handled by StaticFiles mount above
    static_extensions = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", 
                        ".woff", ".woff2", ".ttf", ".eot", ".json", ".map", ".webp")
    if full_path.endswith(static_extensions):
        # Try to serve the actual file from dist root
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # If not found, return 404
        raise HTTPException(status_code=404, detail="File not found")
    
    # Serve index.html for all frontend routes (React Router handles routing)
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend not built. Run 'npm run build' in frontend directory.")

