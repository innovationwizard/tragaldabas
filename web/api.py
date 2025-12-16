"""FastAPI application with Supabase Auth"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

security = HTTPBearer()

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

# In-memory storage for pipeline jobs (use Redis in production)
pipeline_jobs: Dict[str, Dict[str, Any]] = {}


# Pydantic models for request validation
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str  # Changed from email to username
    password: str


class WebProgressTracker:
    """Polling-based progress tracker - stores progress in job object"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.current_stage = None
        self.stage_name = None
    
    def start_stage(self, stage_num: int, stage_name: str):
        self.current_stage = stage_num
        self.stage_name = stage_name
        # Update job object for polling
        if self.job_id in pipeline_jobs:
            pipeline_jobs[self.job_id]["current_stage"] = stage_num
            pipeline_jobs[self.job_id]["current_stage_name"] = stage_name
            pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def complete_stage(self, stage_num: int):
        # Update job object for polling
        if self.job_id in pipeline_jobs:
            pipeline_jobs[self.job_id]["completed_stages"] = pipeline_jobs[self.job_id].get("completed_stages", [])
            if stage_num not in pipeline_jobs[self.job_id]["completed_stages"]:
                pipeline_jobs[self.job_id]["completed_stages"].append(stage_num)
            pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def fail(self, stage_num: int, error: str):
        # Update job object for polling
        if self.job_id in pipeline_jobs:
            pipeline_jobs[self.job_id]["status"] = "failed"
            pipeline_jobs[self.job_id]["error"] = error
            pipeline_jobs[self.job_id]["failed_stage"] = stage_num
            pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def complete(self):
        # Update job object for polling
        if self.job_id in pipeline_jobs:
            pipeline_jobs[self.job_id]["status"] = "completed"
            pipeline_jobs[self.job_id]["current_stage"] = 7  # Output stage
            pipeline_jobs[self.job_id]["current_stage_name"] = "Output"
            pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()


class WebUserPrompt:
    """Web-based user prompt - inherits from UserPrompt (lazy import)"""
    
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
        pipeline_jobs[self.job_id]["questions"] = self.pending_questions
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
    
    # Save uploaded file - use /tmp for Vercel serverless compatibility
    # Vercel provides /tmp directory that persists during function execution
    output_dir = settings.OUTPUT_DIR if settings.OUTPUT_DIR.startswith("/tmp") else "/tmp/output"
    upload_dir = Path(output_dir) / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        import traceback
        print(f"Error saving file: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Initialize job
    user_id = user.get("id")
    pipeline_jobs[job_id] = {
        "id": job_id,
        "user_id": user_id,
        "filename": file.filename,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "current_stage": None,
        "current_stage_name": None,
        "completed_stages": [],
        "questions": []
    }
    
    # Start pipeline asynchronously
    asyncio.create_task(run_pipeline(job_id, str(file_path), user_id))
    
    return {"job_id": job_id, "status": "started"}


async def run_pipeline(job_id: str, file_path: str, user_id: str):
    """Run pipeline in background - lazy imports to reduce serverless function size"""
    # Lazy import heavy dependencies only when pipeline runs
    from orchestrator import Orchestrator
    from ui.progress import ProgressTracker
    from ui.prompts import UserPrompt
    from config import settings
    
    # Make WebProgressTracker inherit from ProgressTracker
    class WebProgressTracker(ProgressTracker):
        """Polling-based progress tracker - stores progress in job object"""
        
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id
            self.current_stage = None
            self.stage_name = None
        
        def start_stage(self, stage_num: int, stage_name: str):
            self.current_stage = stage_num
            self.stage_name = stage_name
            # Update job object for polling
            if self.job_id in pipeline_jobs:
                pipeline_jobs[self.job_id]["current_stage"] = stage_num
                pipeline_jobs[self.job_id]["current_stage_name"] = stage_name
                pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        def complete_stage(self, stage_num: int):
            # Update job object for polling
            if self.job_id in pipeline_jobs:
                pipeline_jobs[self.job_id]["completed_stages"] = pipeline_jobs[self.job_id].get("completed_stages", [])
                if stage_num not in pipeline_jobs[self.job_id]["completed_stages"]:
                    pipeline_jobs[self.job_id]["completed_stages"].append(stage_num)
                pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        def fail(self, stage_num: int, error: str):
            # Update job object for polling
            if self.job_id in pipeline_jobs:
                pipeline_jobs[self.job_id]["status"] = "failed"
                pipeline_jobs[self.job_id]["error"] = error
                pipeline_jobs[self.job_id]["failed_stage"] = stage_num
                pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        def complete(self):
            # Update job object for polling
            if self.job_id in pipeline_jobs:
                pipeline_jobs[self.job_id]["status"] = "completed"
                pipeline_jobs[self.job_id]["current_stage"] = 7  # Output stage
                pipeline_jobs[self.job_id]["current_stage_name"] = "Output"
                pipeline_jobs[self.job_id]["updated_at"] = datetime.utcnow().isoformat()
    
    # Make WebUserPrompt inherit from UserPrompt
    class WebUserPrompt(UserPrompt):
        """Web-based user prompt (stores questions for frontend)"""
        
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
            pipeline_jobs[self.job_id]["questions"] = self.pending_questions
            # In real implementation, wait for user response via polling
            # For now, default to yes
            return True
        
        async def select_domain(self):
            """Domain selection"""
            # Would prompt user via WebSocket
            from core.enums import Domain
            return Domain.FINANCIAL  # Default
    
    try:
        pipeline_jobs[job_id]["status"] = "running"
        pipeline_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        progress = WebProgressTracker(job_id)
        prompt = WebUserPrompt(job_id)
        
        orchestrator = Orchestrator(
            progress=progress,
            prompt=prompt,
            db_connection_string=settings.DATABASE_URL
        )
        
        ctx = await orchestrator.run(file_path)
        
        pipeline_jobs[job_id]["status"] = "completed"
        pipeline_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Convert Pydantic models to dict (works for both v1 and v2)
        def to_dict(model):
            if model is None:
                return None
            if hasattr(model, 'model_dump'):
                return model.model_dump()
            elif hasattr(model, 'dict'):
                return model.dict()
            return str(model)
        
        pipeline_jobs[job_id]["result"] = {
            "reception": to_dict(ctx.reception),
            "classification": to_dict(ctx.classification),
            "structure": to_dict(ctx.structure),
            "archaeology": to_dict(ctx.archaeology),
            "reconciliation": to_dict(ctx.reconciliation),
            "etl": to_dict(ctx.etl),
            "analysis": to_dict(ctx.analysis),
            "output": to_dict(ctx.output),
        }
        
    except Exception as e:
        pipeline_jobs[job_id]["status"] = "failed"
        pipeline_jobs[job_id]["error"] = str(e)
        pipeline_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


@app.get("/api/pipeline/jobs")
async def list_jobs(user: dict = Depends(get_current_user)):
    """List user's pipeline jobs"""
    user_id = user.get("id")
    user_jobs = [
        {k: v for k, v in job.items() if k != "result"}
        for job in pipeline_jobs.values()
        if job.get("user_id") == user_id
    ]
    return {"jobs": user_jobs}


@app.get("/api/pipeline/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    """Get pipeline job details"""
    user_id = user.get("id")
    
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = pipeline_jobs[job_id]
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return job


@app.get("/api/pipeline/jobs/{job_id}/download/{file_type}")
async def download_output(job_id: str, file_type: str, user: dict = Depends(get_current_user)):
    """Download output files"""
    user_id = user.get("id")
    
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = pipeline_jobs[job_id]
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return file based on file_type (pptx, txt, sql, etc.)
    # Implementation depends on output structure
    return {"message": "Download endpoint - implement based on output structure"}


# Polling endpoint for progress updates
@app.get("/api/pipeline/jobs/{job_id}/status")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get current job status for polling"""
    user_id = user.get("id")
    
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = pipeline_jobs[job_id]
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "current_stage": job.get("current_stage"),
        "current_stage_name": job.get("current_stage_name"),
        "completed_stages": job.get("completed_stages", []),
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

