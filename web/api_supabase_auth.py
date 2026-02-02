"""FastAPI application with Supabase Auth integration"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
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

from orchestrator import Orchestrator
from ui.progress import ProgressTracker
from ui.prompts import UserPrompt
from config import settings

# Initialize Supabase client
supabase: Optional[Client] = None
if SUPABASE_AVAILABLE and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )

security = HTTPBearer()

app = FastAPI(
    title="Tragaldabas API",
    description="Universal Data Ingestor API",
    version="1.0.0"
)

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# In-memory storage for pipeline jobs (use Redis in production)
pipeline_jobs: Dict[str, Dict[str, Any]] = {}
progress_connections: Dict[str, List[WebSocket]] = {}


class WebProgressTracker(ProgressTracker):
    """WebSocket-based progress tracker"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.current_stage = None
        self.stage_name = None
    
    def start_stage(self, stage_num: int, stage_name: str):
        self.current_stage = stage_num
        self.stage_name = stage_name
        self._broadcast({
            "type": "stage_start",
            "stage": stage_num,
            "name": stage_name
        })
    
    def complete_stage(self, stage_num: int):
        self._broadcast({
            "type": "stage_complete",
            "stage": stage_num
        })
    
    def fail(self, stage_num: int, error: str):
        self._broadcast({
            "type": "stage_error",
            "stage": stage_num,
            "error": error
        })
    
    def complete(self):
        self._broadcast({
            "type": "pipeline_complete"
        })
    
    def _broadcast(self, message: dict):
        """Broadcast progress to all connected clients"""
        if self.job_id in progress_connections:
            disconnected = []
            for ws in progress_connections[self.job_id]:
                try:
                    asyncio.create_task(ws.send_json(message))
                except:
                    disconnected.append(ws)
            for ws in disconnected:
                progress_connections[self.job_id].remove(ws)


class WebUserPrompt(UserPrompt):
    """Web-based user prompt"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.pending_questions: List[Dict[str, Any]] = []
    
    async def yes_no(self, question: str) -> bool:
        question_id = str(uuid.uuid4())
        self.pending_questions.append({
            "id": question_id,
            "type": "yes_no",
            "question": question
        })
        pipeline_jobs[self.job_id]["questions"] = self.pending_questions
        return True
    
    async def select_domain(self):
        from core.enums import Domain
        return Domain.FINANCIAL


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
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# Auth endpoints (using Supabase Auth)
@app.post("/api/auth/register")
async def register(user_data: dict):
    """Register new user via Supabase Auth"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")
    
    try:
        email = user_data.get("email")
        password = user_data.get("password")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        # Register with Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": user_data.get("username"),
                    "full_name": user_data.get("full_name")
                }
            }
        })
        
        if response.user:
            return {
                "message": "User created successfully",
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "email_confirmed": response.user.email_confirmed_at is not None
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login(login_data: dict):
    """Login user via Supabase Auth"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")
    
    try:
        email = login_data.get("email")
        password = login_data.get("password")
        
        # Login with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/logout")
async def logout(user: dict = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user via Supabase Auth"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Auth not configured")
    
    token = credentials.credentials
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


# Pipeline endpoints (same as before, but using Supabase Auth user)
@app.post("/api/pipeline/upload")
async def upload_file(
    files: List[UploadFile] = File(None),
    file: UploadFile = File(None),
    user: dict = Depends(get_current_user)
):
    """Upload file and start pipeline"""
    from config import settings
    
    user_id = user.get("id")

    upload_files = files or ([] if file is None else [file])
    if not upload_files:
        raise HTTPException(status_code=400, detail="No files provided")

    job_ids: List[str] = []
    
    for upload_file in upload_files:
        job_id = str(uuid.uuid4())

        upload_dir = Path(settings.OUTPUT_DIR) / "uploads" / job_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / upload_file.filename
        
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)
        
        pipeline_jobs[job_id] = {
            "id": job_id,
            "user_id": user_id,
            "filename": upload_file.filename,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "questions": []
        }
        
        asyncio.create_task(run_pipeline(job_id, str(file_path), user_id))
        job_ids.append(job_id)
    
    response_payload = {"job_ids": job_ids, "status": "started"}
    if len(job_ids) == 1:
        response_payload["job_id"] = job_ids[0]
    return response_payload


async def run_pipeline(job_id: str, file_path: str, user_id: str):
    """Run pipeline in background - lazy imports to reduce serverless function size"""
    from orchestrator import Orchestrator
    from ui.progress import ProgressTracker
    from ui.prompts import UserPrompt
    from config import settings
    
    class WebProgressTracker(ProgressTracker):
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id
            self.current_stage = None
            self.stage_name = None
        
        def start_stage(self, stage_num: int, stage_name: str):
            self.current_stage = stage_num
            self.stage_name = stage_name
            self._broadcast({
                "type": "stage_start",
                "stage": stage_num,
                "name": stage_name
            })
        
        def complete_stage(self, stage_num: int):
            self._broadcast({
                "type": "stage_complete",
                "stage": stage_num
            })
        
        def fail(self, stage_num: int, error: str):
            self._broadcast({
                "type": "stage_error",
                "stage": stage_num,
                "error": error
            })
        
        def complete(self):
            self._broadcast({
                "type": "pipeline_complete"
            })
        
        def _broadcast(self, message: dict):
            if self.job_id in progress_connections:
                disconnected = []
                for ws in progress_connections[self.job_id]:
                    try:
                        asyncio.create_task(ws.send_json(message))
                    except:
                        disconnected.append(ws)
                for ws in disconnected:
                    progress_connections[self.job_id].remove(ws)
    
    class WebUserPrompt(UserPrompt):
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id
            self.pending_questions: List[Dict[str, Any]] = []
        
        async def yes_no(self, question: str) -> bool:
            question_id = str(uuid.uuid4())
            self.pending_questions.append({
                "id": question_id,
                "type": "yes_no",
                "question": question
            })
            pipeline_jobs[self.job_id]["questions"] = self.pending_questions
            return True
        
        async def select_domain(self):
            from core.enums import Domain
            return Domain.FINANCIAL
    
    try:
        pipeline_jobs[job_id]["status"] = "running"
        
        progress = WebProgressTracker(job_id)
        prompt = WebUserPrompt(job_id)
        
        orchestrator = Orchestrator(
            progress=progress,
            prompt=prompt,
            db_connection_string=settings.DATABASE_URL
        )
        
        ctx = await orchestrator.run(file_path)
        
        pipeline_jobs[job_id]["status"] = "completed"
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
    
    return {"message": "Download endpoint - implement based on output structure"}


# WebSocket for progress updates
@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    
    if job_id not in progress_connections:
        progress_connections[job_id] = []
    progress_connections[job_id].append(websocket)
    
    try:
        if job_id in pipeline_jobs:
            await websocket.send_json({
                "type": "status",
                "data": pipeline_jobs[job_id]
            })
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if job_id in progress_connections:
            progress_connections[job_id].remove(websocket)


# Serve frontend
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend app"""
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        raise HTTPException(status_code=404)
    
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not built. Run 'npm run build' in frontend directory."}

