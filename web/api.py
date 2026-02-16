"""FastAPI application with Supabase Auth"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request, status
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
import re
import logging
import httpx
import json

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

bearer = HTTPBearer(auto_error=False)

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
        print(f"⚠️ Supabase client not initialized, cannot fetch job {job_id}", flush=True)
        return None
    try:
        response = supabase.table("pipeline_jobs").select("*").eq("id", job_id).execute()
        
        # Check for errors in response
        if hasattr(response, 'error') and response.error:
            print(f"❌ Supabase error fetching job {job_id}: {response.error}", flush=True)
            return None
        
        if response.data and len(response.data) > 0:
            print(f"✅ Found job {job_id} in database: status={response.data[0].get('status')}", flush=True)
            return response.data[0]
        else:
            print(f"⚠️ Job {job_id} not found in database (no rows returned)", flush=True)
            return None
    except Exception as e:
        print(f"❌ Exception fetching job {job_id} from DB: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
    return None

async def update_job_in_db(job_id: str, updates: Dict[str, Any]) -> None:
    """Update job in Supabase database (async, non-blocking)"""
    if not supabase:
        raise RuntimeError(f"Supabase client not initialized, cannot update job {job_id}")

    updates["updated_at"] = datetime.utcnow().isoformat()
    print(f"💾 Updating job {job_id} with keys: {list(updates.keys())}", flush=True)

    def _do():
        return supabase.table("pipeline_jobs").update(updates).eq("id", job_id).execute()

    res = None
    last_err = None
    for attempt in range(3):
        try:
            res = await asyncio.to_thread(_do)
            last_err = None
            break
        except (httpx.HTTPError, OSError, RuntimeError) as exc:
            last_err = exc
            await asyncio.sleep(0.3 * (attempt + 1))
    if last_err:
        raise last_err
    
    err = getattr(res, "error", None)
    data = getattr(res, "data", None)

    if err:
        raise RuntimeError(f"Supabase update error: {err}")
    if not data:
        raise RuntimeError(f"Supabase update affected 0 rows for job {job_id}")

    print(f"✅ Job {job_id} updated", flush=True)

async def promote_batch_to_awaiting_genesis(batch_id: Optional[str]) -> bool:
    """Move all app_generation jobs in a batch to awaiting_genesis together."""
    if not batch_id or not supabase:
        return False
    response = (
        supabase.table("pipeline_jobs")
        .select("id,status,app_generation")
        .eq("batch_id", batch_id)
        .execute()
    )
    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Supabase error fetching batch {batch_id}: {response.error}")
    jobs = response.data or []
    app_jobs = [job for job in jobs if job.get("app_generation")]
    if not app_jobs:
        return False
    if not all(job.get("status") == "ready_for_genesis" for job in app_jobs):
        return False
    for job in app_jobs:
        await update_job_in_db(job["id"], {"status": "awaiting_genesis"})
    return True

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


def serialize_model(model):
    """Convert pipeline models to JSON-serializable structures."""
    if model is None:
        return None

    from datetime import datetime, date
    import math
    import pandas as pd
    import numpy as np

    if isinstance(model, (datetime, date)):
        return model.isoformat()

    if isinstance(model, float):
        if math.isnan(model):
            return None
        if math.isinf(model):
            return "infinity" if model > 0 else "-infinity"
        return model

    if isinstance(model, pd.DataFrame):
        sample_data = []
        if len(model) > 0:
            sample_df = model.head(10)
            sample_dicts = sample_df.to_dict(orient='records')
            for row in sample_dicts:
                cleaned_row = {}
                for key, value in row.items():
                    if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
                        cleaned_row[key] = None
                    elif isinstance(value, float) and math.isinf(value):
                        cleaned_row[key] = "infinity" if value > 0 else "-infinity"
                    else:
                        cleaned_row[key] = serialize_model(value)
                sample_data.append(cleaned_row)
        return {
            "_type": "DataFrame",
            "shape": model.shape,
            "columns": model.columns.tolist(),
            "sample": sample_data
        }

    if isinstance(model, dict):
        result = {}
        for key, value in model.items():
            if isinstance(value, pd.DataFrame):
                sample_data = []
                if len(value) > 0:
                    sample_df = value.head(10)
                    sample_dicts = sample_df.to_dict(orient='records')
                    for row in sample_dicts:
                        cleaned_row = {}
                        for k, v in row.items():
                            if pd.isna(v) or (isinstance(v, float) and math.isnan(v)):
                                cleaned_row[k] = None
                            elif isinstance(v, float) and math.isinf(v):
                                cleaned_row[k] = "infinity" if v > 0 else "-infinity"
                            else:
                                cleaned_row[k] = serialize_model(v)
                        sample_data.append(cleaned_row)
                result[key] = {
                    "_type": "DataFrame",
                    "shape": value.shape,
                    "columns": value.columns.tolist(),
                    "sample": sample_data
                }
            elif isinstance(value, (datetime, date)):
                result[key] = value.isoformat()
            elif isinstance(value, float):
                if math.isnan(value):
                    result[key] = None
                elif math.isinf(value):
                    result[key] = "infinity" if value > 0 else "-infinity"
                else:
                    result[key] = value
            else:
                result[key] = serialize_model(value)
        return result

    if isinstance(model, list):
        return [serialize_model(item) for item in model]

    if hasattr(model, 'model_dump'):
        dumped = model.model_dump()
        return serialize_model(dumped)
    if hasattr(model, 'dict'):
        dumped = model.dict()
        return serialize_model(dumped)

    return model


def _ensure_storage_path_prefix(user_id: str, job_id: str, path: str) -> str:
    if path.startswith(f"{user_id}/{job_id}/"):
        return path
    return f"{user_id}/{job_id}/{path.lstrip('/')}"


def upload_json_to_storage(user_id: str, job_id: str, storage_path: str, payload: Dict[str, Any]) -> str:
    """Upload a JSON payload to Supabase Storage and return the path."""
    import json
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    full_path = _ensure_storage_path_prefix(user_id, job_id, storage_path)
    data = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    supabase.storage.from_("uploads").upload(
        path=full_path,
        file=data,
        file_options={"content-type": "application/json", "upsert": "true"},
    )
    return full_path


def load_json_from_storage(storage_path: str) -> Optional[Dict[str, Any]]:
    """Load a JSON payload from Supabase Storage."""
    import json
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    file_data = supabase.storage.from_("uploads").download(storage_path)
    if file_data is None:
        return None
    content = file_data if isinstance(file_data, bytes) else file_data.read()
    if not content:
        return None
    return json.loads(content.decode("utf-8"))


# Pydantic models for request validation
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str  # Changed from email to username
    password: str


class GenesisRequest(BaseModel):
    confirmation: str


class QuestionAnswer(BaseModel):
    answer: Dict[str, Any]


class BatchEtlRequest(BaseModel):
    database_url: str


# Note: WebProgressTracker and WebUserPrompt are defined inside run_pipeline()
# to inherit from ProgressTracker and UserPrompt (lazy imports)

class WebUserPrompt:
    """Web-based user prompt - stores questions in Supabase database"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.pending_questions: List[Dict[str, Any]] = []

    async def _store_question(self, question: Dict[str, Any]) -> None:
        self.pending_questions.append(question)
        await update_job_in_db(self.job_id, {"questions": self.pending_questions})

    async def _wait_for_answer(self, question_id: str, timeout_seconds: int = 600) -> Optional[Dict[str, Any]]:
        waited = 0
        while waited < timeout_seconds:
            job = get_job_from_db(self.job_id) or {}
            questions = job.get("questions", []) or []
            for q in questions:
                if q.get("id") == question_id and q.get("answer") is not None:
                    return q.get("answer")
            await asyncio.sleep(2)
            waited += 2
        return None

    async def yes_no(self, question: str) -> bool:
        """Store question and wait for response"""
        question_id = str(uuid.uuid4())
        await self._store_question({
            "id": question_id,
            "type": "yes_no",
            "question": question
        })
        return True

    async def confirm_language(self, detected: str):
        question_id = str(uuid.uuid4())
        await self._store_question({
            "id": question_id,
            "type": "confirm_language",
            "question": "Detected transcript language. Is this correct?",
            "detected_language": detected,
        })
        answer = await self._wait_for_answer(question_id)
        if not isinstance(answer, dict):
            return detected, True
        if answer.get("confirm"):
            return detected, True
        language = (answer.get("language") or "").strip()
        if language:
            return language, True
        return None, False
        
    async def select_domain(self):
        """Domain selection"""
        # Would prompt user via polling/API
        from core.enums import Domain
        return Domain.FINANCIAL  # Default


logger = logging.getLogger(__name__)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    """Get current user from Supabase Auth"""
    logger.error(f"Credentials type: {type(credentials)}, value: {credentials}")
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    token = credentials.credentials
    
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase Auth not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
        )
    
    user_response = supabase.auth.get_user(token)
    if not user_response.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    u = user_response.user
    return {"id": u.id, "email": u.email, "user_metadata": u.user_metadata or {}}


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
    "condor": "condor@local.com",
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
async def logout(user: dict = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(bearer)):
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
    files: List[UploadFile] = File(None),
    file: UploadFile = File(None),
    app_generation: bool = Form(False),
    user: dict = Depends(get_current_user)
):
    """Upload file and start pipeline"""
    # Lazy import to reduce serverless function size
    from config import settings
    import tempfile
    
    user_id = user.get("id")

    upload_files = files or ([] if file is None else [file])
    if not upload_files:
        raise HTTPException(status_code=400, detail="No files provided")

    job_ids: List[str] = []
    batch_id = str(uuid.uuid4()) if len(upload_files) > 1 else None
    
    # Upload file to Supabase Storage (persistent, accessible from Railway worker)
    # Files in Vercel /tmp are ephemeral and not accessible from Railway
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    for index, upload_file in enumerate(upload_files):
        job_id = str(uuid.uuid4())
        try:
            content = await upload_file.read()

            storage_path = f"{user_id}/{job_id}/{upload_file.filename}"
            response = supabase.storage.from_("uploads").upload(
                path=storage_path,
                file=content,
                file_options={"content-type": upload_file.content_type or "application/octet-stream", "upsert": "true"}
            )

            if hasattr(response, 'error') and response.error:
                raise Exception(f"Supabase Storage upload error: {response.error}")

            print(f"✅ File uploaded to Supabase Storage: {storage_path}", flush=True)
        except Exception as e:
            import traceback
            print(f"❌ Error uploading file to Supabase Storage: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

        is_excel = bool(re.search(r"\.(xlsx|xls)$", upload_file.filename, re.IGNORECASE))
        job_data = {
            "id": job_id,
            "user_id": user_id,
            "filename": upload_file.filename,
            "status": "pending",
            "current_stage": None,
            "current_stage_name": None,
            "completed_stages": [],
            "questions": [],
            "storage_path": storage_path,
            "app_generation": bool(app_generation and is_excel),
            "batch_id": batch_id,
            "batch_order": index if batch_id else None,
            "batch_total": len(upload_files) if batch_id else None,
        }

        create_job_in_db(job_data)
        job_ids.append(job_id)
    
    # Trigger Edge Function to process the job(s)
    # Note: We await this call (with short timeout) because asyncio.create_task()
    # tasks are killed when Vercel serverless functions return
    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"
    
    try:
        import httpx
        print(f"🚀 Triggering Edge Function for {len(job_ids)} job(s)", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:  # Short timeout to avoid blocking
            tasks = []
            for created_job_id in job_ids:
                tasks.append(client.post(
                    edge_function_url,
                    json={"job_id": created_job_id},
                    headers={
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json"
                    }
                ))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for created_job_id, response in zip(job_ids, responses):
                if isinstance(response, Exception):
                    print(f"❌ Edge Function error: {response}", flush=True)
                    continue
                if response.status_code != 200:
                    error_text = response.text
                    print(f"❌ Edge Function error ({response.status_code}): {error_text}", flush=True)
                else:
                    print(f"✅ Edge Function called successfully for job {created_job_id}", flush=True)
    except httpx.TimeoutException:
        # Timeout is OK - Edge Function will still process the job
        print("⚠️ Edge Function call timed out (non-critical), jobs will be processed", flush=True)
    except Exception as e:
        print(f"⚠️ Warning: Could not trigger Edge Function: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        # Don't fail the upload if Edge Function call fails - job can be processed manually later
    
    response_payload = {
        "job_ids": job_ids,
        "status": "pending",
        "message": "Jobs created, processing will start shortly"
    }
    if len(job_ids) == 1:
        response_payload["job_id"] = job_ids[0]
    if batch_id:
        response_payload["batch_id"] = batch_id
    return response_payload


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
    if job.get("status") not in ["pending", "failed", "pending_genesis"]:
        return {
            "message": f"Job is already {job.get('status')}, cannot retry",
            "job_id": job_id,
            "status": job.get("status")
        }
    
    # Try Edge Function first
    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"

    try:
        print(f"🔄 Retrying job {job_id} via Edge Function", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                edge_function_url,
                json={"job_id": job_id},
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Edge Function error ({response.status_code}): {error_text}", flush=True)
                print(f"⚠️ Falling back to direct process endpoint call", flush=True)
                # Fallback: call process endpoint directly
                raise Exception("Edge Function failed, trying direct call")
            else:
                print(f"✅ Edge Function triggered successfully for job {job_id}", flush=True)
                return {
                    "message": "Job processing triggered",
                    "job_id": job_id
                }
    except httpx.TimeoutException:
        print(f"⚠️ Edge Function timeout, falling back to direct process endpoint", flush=True)
    except Exception as e:
        print(f"⚠️ Edge Function error: {e}, falling back to direct process endpoint", flush=True)

    # Fallback: call Railway worker directly
    try:
        if settings.WORKER_URL:
            print(f"🔄 Calling Railway worker directly for job {job_id}", flush=True)
            # Call Railway worker's process endpoint
            worker_url = settings.WORKER_URL.rstrip("/")
            process_url = f"{worker_url}/process/{job_id}"

            if not settings.RAILWAY_API_KEY:
                raise HTTPException(status_code=500, detail="RAILWAY_API_KEY not configured")

            # Use longer timeout for genesis processing (can take minutes)
            # But we only wait for Railway to accept, not complete
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    process_url,
                    headers={
                        "Authorization": f"Bearer {settings.RAILWAY_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    print(f"✅ Railway worker accepted job {job_id}", flush=True)
                    return {
                        "message": "Job processing triggered via Railway worker",
                        "job_id": job_id
                    }
                else:
                    error_text = response.text
                    print(f"❌ Railway worker error ({response.status_code}): {error_text}", flush=True)
                    raise HTTPException(status_code=500, detail=f"Railway worker error: {error_text}")
        else:
            raise HTTPException(
                status_code=500,
                detail="Cannot retry job: Edge Function unavailable and WORKER_URL not configured. "
                       "Please set WORKER_URL and RAILWAY_API_KEY environment variables in Vercel, "
                       "or deploy the Supabase Edge Function."
            )
    except httpx.TimeoutException:
        # Timeout is OK - Railway worker is processing in background
        print(f"⚠️ Railway worker call timed out for job {job_id}, but processing continues in background", flush=True)
        return {
            "message": "Job processing started (Railway worker timeout, but processing continues)",
            "job_id": job_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ All retry methods failed for job {job_id}: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")


@app.get("/api/pipeline/batches/{batch_id}")
async def get_batch(batch_id: str, user: dict = Depends(get_current_user)):
    """Get ordered jobs for a batch."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    response = (
        supabase.table("pipeline_jobs")
        .select("*")
        .eq("user_id", user.get("id"))
        .eq("batch_id", batch_id)
        .order("batch_order", desc=False)
        .execute()
    )
    if hasattr(response, "error") and response.error:
        raise HTTPException(status_code=500, detail=str(response.error))
    return {"jobs": response.data or []}


@app.post("/api/pipeline/batches/{batch_id}/etl")
async def trigger_batch_etl(
    batch_id: str,
    payload: BatchEtlRequest,
    user: dict = Depends(get_current_user)
):
    """Trigger ETL load for a batch in order."""
    from config import settings
    import httpx

    if not payload.database_url or not payload.database_url.strip():
        raise HTTPException(status_code=400, detail="Database URL is required")

    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    response = (
        supabase.table("pipeline_jobs")
        .select("*")
        .eq("user_id", user.get("id"))
        .eq("batch_id", batch_id)
        .order("batch_order", desc=False)
        .execute()
    )
    if hasattr(response, "error") and response.error:
        raise HTTPException(status_code=500, detail=str(response.error))

    jobs = response.data or []
    if not jobs:
        raise HTTPException(status_code=404, detail="Batch not found")

    for job in jobs:
        status = job.get("status")
        if status not in {"completed", "awaiting_genesis"}:
            raise HTTPException(status_code=409, detail=f"Job {job.get('id')} not ready for ETL")

    for job in jobs:
        await update_job_in_db(job["id"], {
            "etl_status": "pending",
            "etl_error": None,
            "etl_target_db_url": payload.database_url.strip(),
        })

    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"
    try:
        import httpx
        print(f"🧪 Triggering ETL for batch {batch_id}", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:
            for job in jobs:
                response = await client.post(
                    edge_function_url,
                    json={"job_id": job["id"], "mode": "etl"},
                    headers={
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code != 200:
                    error_text = response.text
                    raise HTTPException(status_code=500, detail=f"Failed to trigger ETL: {error_text}")
        return {"message": "ETL triggered", "batch_id": batch_id, "job_ids": [job["id"] for job in jobs]}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Edge Function call timed out")
    except Exception as e:
        print(f"❌ Error triggering ETL for batch {batch_id}: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger ETL: {str(e)}")


@app.post("/api/pipeline/jobs/{job_id}/genesis")
async def trigger_genesis(
    job_id: str,
    payload: GenesisRequest,
    user: dict = Depends(get_current_user)
):
    """Trigger app generation stages after stage 7."""
    from config import settings
    import httpx

    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("user_id") != user.get("id"):
        raise HTTPException(status_code=403, detail="Access denied")

    if job.get("status") != "awaiting_genesis":
        raise HTTPException(
            status_code=409,
            detail=f"Job status {job.get('status')} does not allow genesis"
        )

    confirmation = (payload.confirmation or "").strip().lower()
    if confirmation not in {"y", "yes"}:
        raise HTTPException(status_code=400, detail="Confirmation must be 'y' or 'yes'")

    batch_id = job.get("batch_id")
    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"

    if batch_id:
        response = (
            supabase.table("pipeline_jobs")
            .select("*")
            .eq("user_id", user.get("id"))
            .eq("batch_id", batch_id)
            .order("batch_order", desc=False)
            .execute()
        )
        if hasattr(response, "error") and response.error:
            raise HTTPException(status_code=500, detail=str(response.error))
        jobs = response.data or []
        app_jobs = [j for j in jobs if j.get("app_generation")]
        if not app_jobs:
            raise HTTPException(status_code=409, detail="No app generation jobs in this batch")
        if not all(j.get("status") == "awaiting_genesis" for j in app_jobs):
            raise HTTPException(status_code=409, detail="Batch not ready for genesis")
        for j in app_jobs:
            await update_job_in_db(j["id"], {"status": "pending_genesis", "error": None})
        try:
            print(f"🧬 Triggering Genesis for batch {batch_id}", flush=True)
            async with httpx.AsyncClient(timeout=5.0) as client:
                tasks = [
                    client.post(
                        edge_function_url,
                        json={"job_id": j["id"]},
                        headers={
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                            "Content-Type": "application/json"
                        }
                    )
                    for j in app_jobs
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for j, response in zip(app_jobs, responses):
                    if isinstance(response, Exception):
                        print(f"❌ Edge Function error for job {j['id']}: {response}", flush=True)
                        continue
                    if response.status_code != 200:
                        error_text = response.text
                        raise HTTPException(status_code=500, detail=f"Failed to trigger genesis: {error_text}")
            return {"message": "Genesis triggered", "job_ids": [j["id"] for j in app_jobs], "batch_id": batch_id}
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Edge Function call timed out")
        except Exception as e:
            print(f"❌ Error triggering genesis for batch {batch_id}: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            raise HTTPException(status_code=500, detail=f"Failed to trigger genesis: {str(e)}")

    await update_job_in_db(job_id, {
        "status": "pending_genesis",
        "error": None
    })

    try:
        print(f"🧬 Triggering Genesis for job {job_id}", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                edge_function_url,
                json={"job_id": job_id},
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Edge Function error ({response.status_code}): {error_text}", flush=True)
                raise HTTPException(status_code=500, detail=f"Failed to trigger genesis: {error_text}")
            print(f"✅ Genesis triggered successfully for job {job_id}", flush=True)
            return {"message": "Genesis triggered", "job_id": job_id}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Edge Function call timed out")
    except Exception as e:
        print(f"❌ Error triggering genesis for job {job_id}: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger genesis: {str(e)}")


@app.post("/api/pipeline/jobs/{job_id}/genesis/retry")
async def retry_genesis(
    job_id: str,
    payload: GenesisRequest,
    user: dict = Depends(get_current_user)
):
    """Retry app generation stages (8-12) without re-running stages 1-7."""
    from config import settings
    import httpx

    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("user_id") != user.get("id"):
        raise HTTPException(status_code=403, detail="Access denied")

    confirmation = (payload.confirmation or "").strip().lower()
    if confirmation not in {"y", "yes"}:
        raise HTTPException(status_code=400, detail="Confirmation must be 'y' or 'yes'")

    def _ready_for_genesis(candidate: Dict[str, Any]) -> bool:
        if candidate.get("status") in {"awaiting_genesis", "ready_for_genesis"}:
            return True
        completed = candidate.get("completed_stages", []) or []
        if 7 in completed:
            return True
        if candidate.get("current_stage") == 7:
            return True
        return False

    batch_id = job.get("batch_id")
    edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-pipeline"

    if batch_id:
        response = (
            supabase.table("pipeline_jobs")
            .select("*")
            .eq("user_id", user.get("id"))
            .eq("batch_id", batch_id)
            .order("batch_order", desc=False)
            .execute()
        )
        if hasattr(response, "error") and response.error:
            raise HTTPException(status_code=500, detail=str(response.error))
        jobs = response.data or []
        app_jobs = [j for j in jobs if j.get("app_generation")]
        if not app_jobs:
            raise HTTPException(status_code=409, detail="No app generation jobs in this batch")
        if not all(_ready_for_genesis(j) for j in app_jobs):
            raise HTTPException(status_code=409, detail="Batch not ready for genesis retry")
        for j in app_jobs:
            if j.get("status") not in {"failed", "awaiting_genesis", "ready_for_genesis", "pending_genesis", "genesis_running"}:
                raise HTTPException(status_code=409, detail=f"Job {j.get('id')} not eligible for genesis retry")
        for j in app_jobs:
            await update_job_in_db(j["id"], {"status": "pending_genesis", "error": None})
        try:
            print(f"🧬 Retrying Genesis for batch {batch_id}", flush=True)
            async with httpx.AsyncClient(timeout=5.0) as client:
                tasks = [
                    client.post(
                        edge_function_url,
                        json={"job_id": j["id"]},
                        headers={
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                            "Content-Type": "application/json"
                        }
                    )
                    for j in app_jobs
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for j, response in zip(app_jobs, responses):
                    if isinstance(response, Exception):
                        print(f"❌ Edge Function error for job {j['id']}: {response}", flush=True)
                        continue
                    if response.status_code != 200:
                        error_text = response.text
                        raise HTTPException(status_code=500, detail=f"Failed to retry genesis: {error_text}")
            return {"message": "Genesis retry triggered", "job_ids": [j["id"] for j in app_jobs], "batch_id": batch_id}
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Edge Function call timed out")
        except Exception as e:
            print(f"❌ Error retrying genesis for batch {batch_id}: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            raise HTTPException(status_code=500, detail=f"Failed to retry genesis: {str(e)}")

    if job.get("status") not in {"failed", "awaiting_genesis", "ready_for_genesis", "pending_genesis", "genesis_running"}:
        raise HTTPException(status_code=409, detail=f"Job status {job.get('status')} does not allow genesis retry")
    if not _ready_for_genesis(job):
        raise HTTPException(status_code=409, detail="Job not ready for genesis retry")

    await update_job_in_db(job_id, {"status": "pending_genesis", "error": None})

    try:
        print(f"🧬 Retrying Genesis for job {job_id}", flush=True)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                edge_function_url,
                json={"job_id": job_id},
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Edge Function error ({response.status_code}): {error_text}", flush=True)
                raise HTTPException(status_code=500, detail=f"Failed to retry genesis: {error_text}")
            print(f"✅ Genesis retry triggered successfully for job {job_id}", flush=True)
            return {"message": "Genesis retry triggered", "job_id": job_id}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Edge Function call timed out")
    except Exception as e:
        print(f"❌ Error retrying genesis for job {job_id}: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to retry genesis: {str(e)}")


async def run_pipeline(job_id: str, file_path: str, user_id: str, app_generation: bool):
    """Run pipeline in background - lazy imports to reduce serverless function size"""
    print(f"🎯 run_pipeline() CALLED for job {job_id}, file: {file_path}", flush=True)
    # Lazy import heavy dependencies only when pipeline runs
    from orchestrator import Orchestrator
    from ui.progress import ProgressTracker
    from ui.prompts import UserPrompt
    from config import settings
    
    # Make WebProgressTracker inherit from ProgressTracker
    class WebProgressTracker(ProgressTracker):
        """Polling-based progress tracker - stores progress in Supabase database"""
        
        def __init__(
            self,
            job_id: str,
            final_stage: int,
            completion_status: str = "completed",
            completion_stage_name: Optional[str] = None,
        ):
            super().__init__()
            self.job_id = job_id
            self.current_stage = None
            self.stage_name = None
            self.final_stage = final_stage
            self.completion_status = completion_status
            self.completion_stage_name = completion_stage_name
        
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
            print(f"🔔 WebProgressTracker.complete() called for job {self.job_id}", flush=True)
            try:
                stage_name = self.completion_stage_name
                if not stage_name:
                    stage_name = "Output" if self.final_stage == 7 else "Scaffold & Deploy"
                await update_job_in_db(self.job_id, {
                    "status": self.completion_status,
                    "current_stage": self.final_stage,
                    "current_stage_name": stage_name
                })
                print(f"✅ WebProgressTracker.complete() finished for job {self.job_id}", flush=True)
            except Exception as e:
                print(f"❌ WebProgressTracker.complete() failed for job {self.job_id}: {e}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
                raise
    
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
        
        settings.EXCEL_APP_GENERATION_ENABLED = False
        final_stage = 7
        completion_status = "ready_for_genesis" if app_generation else "completed"
        progress = WebProgressTracker(
            job_id,
            final_stage,
            completion_status=completion_status,
            completion_stage_name="Output",
        )
        prompt = WebUserPrompt(job_id)
        
        orchestrator = Orchestrator(
            progress=progress,
            prompt=prompt,
            db_connection_string=settings.DATABASE_URL
        )
        
        print(f"🚀 Calling orchestrator.run() for job {job_id}", flush=True)
        ctx = await orchestrator.run(file_path)
        print(f"✅ orchestrator.run() completed for job {job_id}", flush=True)
        
        # Upload output files to Supabase Storage before converting to dict
        output_storage_paths = {}
        if ctx.output and supabase:
            print(f"📤 Uploading output files to Supabase Storage for job {job_id}", flush=True)
            try:
                # Upload text file
                if ctx.output.text_file_path:
                    text_path = Path(ctx.output.text_file_path)
                    if text_path.exists():
                        with open(text_path, 'rb') as f:
                            text_content = f.read()
                        storage_path_txt = f"{user_id}/{job_id}/outputs/{text_path.name}"
                        supabase.storage.from_("uploads").upload(
                            path=storage_path_txt,
                            file=text_content,
                            file_options={"content-type": "text/plain", "upsert": "true"}
                        )
                        output_storage_paths["text_file_storage_path"] = storage_path_txt
                        print(f"✅ Uploaded text file to: {storage_path_txt}", flush=True)
                
                # Upload markdown file
                if ctx.output.markdown_file_path:
                    md_path = Path(ctx.output.markdown_file_path)
                    if md_path.exists():
                        with open(md_path, 'rb') as f:
                            md_content = f.read()
                        storage_path_md = f"{user_id}/{job_id}/outputs/{md_path.name}"
                        supabase.storage.from_("uploads").upload(
                            path=storage_path_md,
                            file=md_content,
                            file_options={"content-type": "text/markdown", "upsert": "true"}
                        )
                        output_storage_paths["markdown_file_storage_path"] = storage_path_md
                        print(f"✅ Uploaded markdown file to: {storage_path_md}", flush=True)
                
                # Upload PowerPoint file
                if ctx.output.pptx_file_path:
                    pptx_path = Path(ctx.output.pptx_file_path)
                    if pptx_path.exists():
                        with open(pptx_path, 'rb') as f:
                            pptx_content = f.read()
                        storage_path_pptx = f"{user_id}/{job_id}/outputs/{pptx_path.name}"
                        supabase.storage.from_("uploads").upload(
                            path=storage_path_pptx,
                            file=pptx_content,
                            file_options={"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation", "upsert": "true"}
                        )
                        output_storage_paths["pptx_file_storage_path"] = storage_path_pptx
                        print(f"✅ Uploaded PowerPoint file to: {storage_path_pptx}", flush=True)
                
            except Exception as e:
                import traceback
                print(f"⚠️ Warning: Failed to upload output files to Storage: {e}", flush=True)
                print(traceback.format_exc(), flush=True)
                # Don't fail the job if upload fails - files are still available locally
        
        # Convert output to dict and add storage paths
        output_dict = serialize_model(ctx.output)
        if output_dict and output_storage_paths:
            output_dict.update(output_storage_paths)
        
        result = {
            "reception": serialize_model(ctx.reception),
            "classification": serialize_model(ctx.classification),
            "structure": serialize_model(ctx.structure),
            "archaeology": serialize_model(ctx.archaeology),
            "reconciliation": serialize_model(ctx.reconciliation),
            "etl": serialize_model(ctx.etl),
            "analysis": serialize_model(ctx.analysis),
            "output": output_dict,
            "cell_classification": serialize_model(ctx.cell_classification),
            "dependency_graph": serialize_model(ctx.dependency_graph),
            "logic_extraction": serialize_model(ctx.logic_extraction),
            "generated_project": serialize_model(ctx.generated_project),
            "scaffold": serialize_model(ctx.scaffold),
        }
        
        # Update job with completed status and result (stored in object storage)
        status_value = "ready_for_genesis" if app_generation else "completed"
        print(f"💾 Updating job {job_id} to completed status with result", flush=True)
        try:
            result_path = upload_json_to_storage(user_id, job_id, "results/result.json", result)
            await update_job_in_db(job_id, {
                "status": status_value,
                "result": {"storage_path": result_path}
            })
            print(f"✅ Successfully updated job {job_id} to {status_value}", flush=True)
        except Exception as update_error:
            print(f"❌ CRITICAL: Failed to update job {job_id} to completed: {update_error}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            raise
        
        # Sanity check: verify the update actually persisted
        if supabase:
            def _check():
                return supabase.table("pipeline_jobs").select("status,current_stage,completed_stages,updated_at").eq("id", job_id).execute()
            check = await asyncio.to_thread(_check)
            check_err = getattr(check, "error", None)
            check_data = getattr(check, "data", None)
            print(f"🔍 DB CHECK after completed update: data={check_data}, error={check_err}", flush=True)
            if check_err:
                print(f"⚠️ Warning: Sanity check failed with error: {check_err}", flush=True)
            elif not check_data or len(check_data) == 0:
                print(f"⚠️ Warning: Sanity check found no data for job {job_id}", flush=True)
            elif check_data[0].get("status") != status_value:
                print(f"⚠️ Warning: Sanity check shows status is '{check_data[0].get('status')}', expected '{status_value}'", flush=True)
        
        if app_generation:
            # Fetch job to check for batch_id
            if supabase:
                def _get_job():
                    return supabase.table("pipeline_jobs").select("batch_id").eq("id", job_id).execute()
                job_data = await asyncio.to_thread(_get_job)
                job = job_data.data[0] if job_data.data else {}
            else:
                job = {}

            if job.get("batch_id"):
                await promote_batch_to_awaiting_genesis(job.get("batch_id"))
            else:
                await update_job_in_db(job_id, {"status": "awaiting_genesis"})
        print(f"✅ Job {job_id} status updated to completed", flush=True)
        
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


async def run_genesis_pipeline(job_id: str, file_path: str, user_id: str):
    """Run app generation stages (8-12) after user confirmation."""
    print(f"🧬 run_genesis_pipeline() CALLED for job {job_id}, file: {file_path}", flush=True)
    from orchestrator import Orchestrator
    from ui.progress import ProgressTracker
    from ui.prompts import UserPrompt
    from config import settings
    from orchestrator import PipelineContext
    from core.models import (
        CellClassificationResult,
        DependencyGraph,
        LogicExtractionResult,
        GeneratedProject,
        ScaffoldResult,
        AppGenerationContext,
    )

    class WebProgressTracker(ProgressTracker):
        """Polling-based progress tracker for genesis stages."""

        def __init__(self, job_id: str, final_stage: int):
            super().__init__()
            self.job_id = job_id
            self.current_stage = None
            self.stage_name = None
            self.final_stage = final_stage

        async def start_stage(self, stage_num: int, stage_name: str):
            self.current_stage = stage_num
            self.stage_name = stage_name
            await update_job_in_db(self.job_id, {
                "current_stage": stage_num,
                "current_stage_name": stage_name
            })

        async def complete_stage(self, stage_num: int):
            job = get_job_from_db(self.job_id)
            if job:
                completed = job.get("completed_stages", []) or []
                if stage_num not in completed:
                    completed.append(stage_num)
                    await update_job_in_db(self.job_id, {"completed_stages": completed})

        async def fail(self, stage_num: int, error: str):
            await update_job_in_db(self.job_id, {
                "status": "failed",
                "error": error,
                "failed_stage": stage_num
            })

        async def complete(self):
            print(f"🔔 WebProgressTracker.complete() called for genesis job {self.job_id}", flush=True)
            await update_job_in_db(self.job_id, {
                "status": "completed",
                "current_stage": self.final_stage,
                "current_stage_name": "Scaffold & Deploy"
            })

    class WebUserPrompt(UserPrompt):
        """Placeholder prompt for app generation stages."""

        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id

        async def yes_no(self, question: str) -> bool:
            return True

        async def select_domain(self):
            from core.enums import Domain
            return Domain.FINANCIAL

    def _coerce_model(cls, data):
        if data is None:
            return None
        if hasattr(cls, "model_validate"):
            return cls.model_validate(data)
        return cls(**data)

    try:
        await update_job_in_db(job_id, {"status": "genesis_running", "error": None})

        progress = WebProgressTracker(job_id, 12)
        prompt = WebUserPrompt(job_id)
        orchestrator = Orchestrator(
            progress=progress,
            prompt=prompt,
            db_connection_string=settings.DATABASE_URL
        )

        existing = get_job_from_db(job_id) or {}
        base_result = existing.get("result") if isinstance(existing, dict) else {}
        if not isinstance(base_result, dict):
            base_result = {}

        # If result contains storage_path, download the actual result from Supabase Storage
        if base_result.get("storage_path") and supabase:
            storage_path = base_result.get("storage_path")
            print(f"📥 Downloading result from storage: {storage_path}", flush=True)
            try:
                result_data = supabase.storage.from_("uploads").download(storage_path)
                if result_data:
                    import json
                    base_result = json.loads(result_data)
                    print(f"✅ Result loaded from storage ({len(str(base_result))} bytes)", flush=True)
            except Exception as e:
                print(f"⚠️ Could not load result from storage: {e}", flush=True)
                base_result = {}

        completed_raw = existing.get("completed_stages", []) or []
        completed = []
        for value in completed_raw:
            try:
                completed.append(int(value))
            except (TypeError, ValueError):
                continue

        ctx = PipelineContext(file_path=file_path)
        ctx.cell_classification = _coerce_model(
            CellClassificationResult, base_result.get("cell_classification")
        )
        ctx.dependency_graph = _coerce_model(
            DependencyGraph, base_result.get("dependency_graph")
        )
        ctx.logic_extraction = _coerce_model(
            LogicExtractionResult, base_result.get("logic_extraction")
        )
        ctx.generated_project = _coerce_model(
            GeneratedProject, base_result.get("generated_project")
        )
        ctx.scaffold = _coerce_model(ScaffoldResult, base_result.get("scaffold"))

        async def _persist_stage_result():
            base_result.update({
                "cell_classification": serialize_model(ctx.cell_classification),
                "dependency_graph": serialize_model(ctx.dependency_graph),
                "logic_extraction": serialize_model(ctx.logic_extraction),
                "generated_project": serialize_model(ctx.generated_project),
                "scaffold": serialize_model(ctx.scaffold),
            })
            result_path = upload_json_to_storage(user_id, job_id, "results/result.json", base_result)
            await update_job_in_db(job_id, {"result": {"storage_path": result_path}})

        def _needs_stage(stage_num: int) -> bool:
            if stage_num == 8 and ctx.cell_classification is None:
                return True
            if stage_num == 9 and ctx.dependency_graph is None:
                return True
            if stage_num == 10 and ctx.logic_extraction is None:
                return True
            if stage_num == 11 and ctx.generated_project is None:
                return True
            if stage_num == 12 and ctx.scaffold is None:
                return True
            return stage_num not in completed

        if _needs_stage(8):
            ctx.cell_classification = await orchestrator._execute_stage(8, ctx.file_path)
            await _persist_stage_result()
        if _needs_stage(9):
            ctx.dependency_graph = await orchestrator._execute_stage(9, ctx.cell_classification)
            await _persist_stage_result()
        if _needs_stage(10):
            ctx.logic_extraction = await orchestrator._execute_stage(10, ctx.dependency_graph)
            await _persist_stage_result()
        if _needs_stage(11):
            ctx.generated_project = await orchestrator._execute_stage(
                11,
                AppGenerationContext(
                    cell_classification=ctx.cell_classification,
                    logic_extraction=ctx.logic_extraction,
                    dependency_graph=ctx.dependency_graph,
                ),
            )
            await _persist_stage_result()
        if _needs_stage(12):
            ctx.scaffold = await orchestrator._execute_stage(12, ctx.generated_project)
            await _persist_stage_result()

        result_path = upload_json_to_storage(user_id, job_id, "results/result.json", base_result)
        await update_job_in_db(job_id, {"status": "completed", "result": {"storage_path": result_path}})
        print(f"✅ Job {job_id} updated with genesis results", flush=True)

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Genesis pipeline failed for job {job_id}: {error_msg}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        try:
            await update_job_in_db(job_id, {
                "status": "failed",
                "error": error_msg
            })
        except Exception:
            pass
        raise


async def run_etl_job(job_id: str, file_path: str, user_id: str):
    """Run ETL-only pipeline to populate app database."""
    print(f"🧪 run_etl_job() CALLED for job {job_id}, file: {file_path}", flush=True)
    from orchestrator import Orchestrator
    from ui.progress import ProgressTracker
    from ui.prompts import UserPrompt
    from config import settings

    if not supabase:
        raise RuntimeError("Supabase client not initialized")

    job = get_job_from_db(job_id) or {}
    target_db_url = job.get("etl_target_db_url")
    if not target_db_url:
        raise RuntimeError("Missing ETL target database URL")

    batch_id = job.get("batch_id")
    batch_order = job.get("batch_order")
    if batch_id and isinstance(batch_order, int) and batch_order > 0:
        while True:
            response = (
                supabase.table("pipeline_jobs")
                .select("id,etl_status,etl_error,batch_order")
                .eq("batch_id", batch_id)
                .lt("batch_order", batch_order)
                .execute()
            )
            prev_jobs = response.data or []
            if any(prev.get("etl_status") == "failed" for prev in prev_jobs):
                raise RuntimeError("Previous ETL job in batch failed")
            if all(prev.get("etl_status") == "completed" for prev in prev_jobs):
                break
            await asyncio.sleep(2)

    class WebProgressTracker(ProgressTracker):
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id
            self.current_stage = None
            self.stage_name = None

        async def start_stage(self, stage_num: int, stage_name: str):
            self.current_stage = stage_num
            self.stage_name = stage_name
            await update_job_in_db(self.job_id, {
                "etl_status": "running",
                "etl_started_at": datetime.utcnow().isoformat(),
            })

        async def complete_stage(self, stage_num: int):
            return

        async def fail(self, stage_num: int, error: str):
            await update_job_in_db(self.job_id, {
                "etl_status": "failed",
                "etl_error": error
            })

        async def complete(self):
            await update_job_in_db(self.job_id, {
                "etl_status": "completed",
                "etl_completed_at": datetime.utcnow().isoformat()
            })

    class WebUserPrompt(UserPrompt):
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id

        async def yes_no(self, question: str) -> bool:
            return True

        async def select_domain(self):
            from core.enums import Domain
            return Domain.FINANCIAL

    previous_etl_flag = settings.ETL_INPUTS_ONLY
    settings.ETL_INPUTS_ONLY = True
    try:
        progress = WebProgressTracker(job_id)
        prompt = WebUserPrompt(job_id)
        orchestrator = Orchestrator(
            progress=progress,
            prompt=prompt,
            db_connection_string=target_db_url
        )
        ctx = await orchestrator.run_etl_only(file_path)
        etl_payload = serialize_model(ctx.etl) or {}
        etl_path = upload_json_to_storage(user_id, job_id, "etl/etl_result.json", etl_payload)
        await update_job_in_db(job_id, {"etl_result": {"storage_path": etl_path}})
    except Exception as e:
        error_msg = str(e)
        await update_job_in_db(job_id, {
            "etl_status": "failed",
            "etl_error": error_msg
        })
        raise
    finally:
        settings.ETL_INPUTS_ONLY = previous_etl_flag


@app.post("/api/pipeline/process/{job_id}")
async def process_job(
    job_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)
):
    """Process a pending pipeline job - can be called by Supabase Edge Function or worker"""
    
    # Get job from database
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check authentication - allow service role key from header for Edge Function calls
    user_id = None
    is_service_call = False
    
    if credentials and hasattr(credentials, 'credentials') and credentials.credentials:
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
    if job.get("status") not in ["pending", "failed", "pending_genesis"]:
        print(f"⏭️ Skipping job {job_id}: status={job.get('status')}", flush=True)
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
        
        is_genesis = job.get("status") == "pending_genesis"
        if is_genesis:
            print(f"📞 process_job() calling run_genesis_pipeline() for job {job_id}", flush=True)
            await run_genesis_pipeline(job_id, str(file_path), user_id)
            print(f"✅ process_job() run_genesis_pipeline() returned for job {job_id}", flush=True)
        else:
            print(f"📞 process_job() calling run_pipeline() for job {job_id}", flush=True)
            app_generation = bool(job.get("app_generation", False))
            await run_pipeline(job_id, str(file_path), user_id, app_generation)
            print(f"✅ process_job() run_pipeline() returned for job {job_id}", flush=True)
        return {"message": "Job processed successfully", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error processing job {job_id}: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process job: {error_msg}")


@app.post("/api/pipeline/etl/{job_id}")
async def process_etl_job(
    job_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)
):
    """Process ETL job to load original Excel data into app database."""
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    user_id = None
    is_service_call = False

    if credentials and hasattr(credentials, 'credentials') and credentials.credentials:
        token = credentials.credentials
        try:
            if supabase:
                user_response = supabase.auth.get_user(token)
                if user_response.user:
                    user_id = user_response.user.id
        except Exception:
            if token == settings.SUPABASE_SERVICE_ROLE_KEY:
                is_service_call = True
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not is_service_call and user_id and job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if job.get("etl_status") in {"running", "completed"}:
        return {"message": f"ETL already {job.get('etl_status')}", "job_id": job_id}

    if not job.get("etl_target_db_url"):
        raise HTTPException(status_code=400, detail="Missing ETL target database URL")

    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    filename = job.get("filename")
    storage_path = job.get("storage_path")

    if not filename:
        raise HTTPException(status_code=400, detail="Job filename not found")

    if not storage_path:
        job_user_id = job.get("user_id")
        storage_path = f"{job_user_id}/{job_id}/{filename}"
        print(f"⚠️ Storage path not in job data, reconstructing: {storage_path}", flush=True)

    try:
        print(f"📥 Downloading file for ETL: {storage_path}", flush=True)
        file_response = supabase.storage.from_("uploads").download(storage_path)
        if file_response is None:
            raise Exception("File data is None - file may not exist in Storage")
        if isinstance(file_response, bytes):
            file_data = file_response
        elif hasattr(file_response, 'read'):
            file_data = file_response.read()
        else:
            file_data = file_response
        if not file_data:
            raise Exception("File data is empty")

        output_dir = settings.OUTPUT_DIR if settings.OUTPUT_DIR.startswith("/tmp") else "/tmp/output"
        local_upload_dir = Path(output_dir) / "uploads" / job_id
        local_upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = local_upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_data)
        print(f"✅ File downloaded and saved to: {file_path}", flush=True)
    except Exception as e:
        import traceback
        error_msg = f"Failed to download file from Supabase Storage: {str(e)}"
        print(f"❌ {error_msg}", flush=True)
        print(traceback.format_exc(), flush=True)
        await update_job_in_db(job_id, {
            "etl_status": "failed",
            "etl_error": error_msg
        })
        raise HTTPException(status_code=404, detail=error_msg)

    try:
        await run_etl_job(job_id, str(file_path), job.get("user_id"))
        return {"message": "ETL processed successfully", "job_id": job_id}
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error processing ETL job {job_id}: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process ETL job: {error_msg}")


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

    result = job.get("result")
    if isinstance(result, dict) and result.get("storage_path"):
        try:
            loaded = load_json_from_storage(result["storage_path"])
            if loaded is not None:
                job["result"] = loaded
        except Exception as e:
            print(f"⚠️ Failed to load result from storage: {e}", flush=True)

    etl_result = job.get("etl_result")
    if isinstance(etl_result, dict) and etl_result.get("storage_path"):
        try:
            loaded = load_json_from_storage(etl_result["storage_path"])
            if loaded is not None:
                job["etl_result"] = loaded
        except Exception as e:
            print(f"⚠️ Failed to load etl_result from storage: {e}", flush=True)

    return job


@app.post("/api/pipeline/jobs/{job_id}/questions/{question_id}")
async def answer_question(
    job_id: str,
    question_id: str,
    payload: QuestionAnswer,
    user: dict = Depends(get_current_user)
):
    """Answer a pending prompt question for a job."""
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user.get("id"):
        raise HTTPException(status_code=403, detail="Access denied")

    questions = job.get("questions", []) or []
    updated = False
    for q in questions:
        if q.get("id") == question_id:
            q["answer"] = payload.answer
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Question not found")

    await update_job_in_db(job_id, {"questions": questions})
    return {"message": "Answer recorded", "job_id": job_id, "question_id": question_id}


@app.get("/api/pipeline/jobs/{job_id}/download/{file_type}")
async def download_output(job_id: str, file_type: str, user: dict = Depends(get_current_user)):
    """Download output files"""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    user_id = user.get("id")
    
    job = get_job_from_db(job_id)  # Synchronous call
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    result = job.get("result")
    if isinstance(result, dict) and result.get("storage_path"):
        result = load_json_from_storage(result["storage_path"])
    if not result:
        raise HTTPException(status_code=404, detail="Job result not found")
    
    output = result.get("output")
    if not output:
        raise HTTPException(status_code=404, detail="Output not found")
    
    # Get file path based on file_type
    file_path = None
    content_type = None
    filename = None
    
    if file_type == "txt":
        file_path = output.get("text_file_path")
        content_type = "text/plain"
        filename = f"{job.get('filename', 'insights')}.txt"
    elif file_type == "pptx":
        file_path = output.get("pptx_file_path")
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        filename = f"{job.get('filename', 'presentation')}.pptx"
    elif file_type == "md":
        file_path = output.get("markdown_file_path")
        content_type = "text/markdown"
        filename = f"{job.get('filename', 'insights')}.md"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")
    
    if not file_path:
        raise HTTPException(status_code=404, detail=f"{file_type} file not generated")
    
    # Try to download from Supabase Storage first (if files were uploaded there)
    # Check for storage paths in output result first
    storage_path = None
    if file_type == "txt":
        storage_path = output.get("text_file_storage_path")
    elif file_type == "pptx":
        storage_path = output.get("pptx_file_storage_path")
    elif file_type == "md":
        storage_path = output.get("markdown_file_storage_path")
    
    # Fallback to default path structure if not in result
    if not storage_path:
        storage_path = f"{user_id}/{job_id}/outputs/{filename}"
    
    if supabase:
        try:
            print(f"📥 Downloading output file from Supabase Storage: {storage_path}", flush=True)
            file_data = supabase.storage.from_("uploads").download(storage_path)
            
            if file_data:
                from fastapi.responses import Response
                content = file_data if isinstance(file_data, bytes) else file_data.read()
                print(f"✅ Downloaded {len(content)} bytes from Storage", flush=True)
                return Response(
                    content=content,
                    media_type=content_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                )
            else:
                print(f"⚠️ File data is None from Storage path: {storage_path}", flush=True)
        except Exception as e:
            print(f"⚠️ Could not download from Supabase Storage: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            # Fall through to try local filesystem
    
    # Fallback: Try local filesystem (only works if running on same machine as worker)
    path = Path(file_path)
    if not path.exists():
        # Try relative to OUTPUT_DIR
        from config import settings
        output_dir = settings.OUTPUT_DIR if settings.OUTPUT_DIR.startswith("/tmp") else "/tmp/output"
        path = Path(output_dir) / path.name
        if not path.exists():
            # Try to find file in job-specific output directory
            path = Path(output_dir) / "insights" / path.name
            if not path.exists() and file_type == "pptx":
                path = Path(output_dir) / "presentations" / path.name
            if not path.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found. Output files are stored on the worker and need to be uploaded to Supabase Storage. File path: {file_path}"
                )
    
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=filename
    )


# Polling endpoint for progress updates
@app.get("/api/pipeline/jobs/{job_id}/status")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get current job status for polling from Supabase database"""
    user_id = user.get("id")
    
    print(f"📊 Status endpoint called for job {job_id} by user {user_id}", flush=True)
    
    if not user_id:
        print(f"❌ No user_id in user dict: {user}", flush=True)
        raise HTTPException(status_code=401, detail="User ID not found")
    
    job = get_job_from_db(job_id)  # Synchronous call
    
    if not job:
        print(f"❌ Job {job_id} not found in database", flush=True)
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job_user_id = job.get("user_id")
    if job_user_id != user_id:
        print(f"❌ Access denied: job user_id={job_user_id}, request user_id={user_id}", flush=True)
        raise HTTPException(status_code=403, detail="Access denied")
    
    print(f"✅ Returning status for job {job_id}: status={job.get('status')}, stage={job.get('current_stage')}", flush=True)
    
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

