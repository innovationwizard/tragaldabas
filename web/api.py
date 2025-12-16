"""FastAPI application"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import uuid
from pathlib import Path
import os
from datetime import datetime

from auth.service import AuthService
from auth.database import AuthDatabase
from auth.jwt import JWTManager
from auth.password import PasswordHasher
from auth.models import UserCreate, UserLogin, User, PasswordChange
from orchestrator import Orchestrator
from ui.progress import ProgressTracker
from ui.prompts import UserPrompt
from config import settings

# Initialize auth components
auth_db = AuthDatabase()
jwt_manager = JWTManager()
password_hasher = PasswordHasher()
auth_service = AuthService(auth_db, jwt_manager, password_hasher)

security = HTTPBearer()

app = FastAPI(
    title="Tragaldabas API",
    description="Universal Data Ingestor API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite/React dev servers
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
    """Web-based user prompt (stores questions for frontend)"""
    
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
        # In real implementation, wait for WebSocket response
        # For now, default to yes
        return True
    
    async def select_domain(self):
        """Domain selection"""
        # Would prompt user via WebSocket
        from core.enums import Domain
        return Domain.FINANCIAL  # Default


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


# Auth endpoints
@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    """Register new user"""
    try:
        user = await auth_service.register(user_data)
        return {"message": "User created successfully", "user_id": user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login(login_data: UserLogin, request: Request):
    """Login user"""
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        session, user = await auth_service.login(
            login_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "access_token": session.token,
            "refresh_token": session.refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.value
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/logout")
async def logout(user: User = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user"""
    token = credentials.credentials
    await auth_service.logout(token)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value
    }


# Pipeline endpoints
@app.post("/api/pipeline/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Upload file and start pipeline"""
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_dir = Path(settings.OUTPUT_DIR) / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Initialize job
    pipeline_jobs[job_id] = {
        "id": job_id,
        "user_id": user.id,
        "filename": file.filename,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "questions": []
    }
    
    # Start pipeline asynchronously
    asyncio.create_task(run_pipeline(job_id, str(file_path), user.id))
    
    return {"job_id": job_id, "status": "started"}


async def run_pipeline(job_id: str, file_path: str, user_id: int):
    """Run pipeline in background"""
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


@app.get("/api/pipeline/jobs")
async def list_jobs(user: User = Depends(get_current_user)):
    """List user's pipeline jobs"""
    user_jobs = [
        {k: v for k, v in job.items() if k != "result"}
        for job in pipeline_jobs.values()
        if job.get("user_id") == user.id
    ]
    return {"jobs": user_jobs}


@app.get("/api/pipeline/jobs/{job_id}")
async def get_job(job_id: str, user: User = Depends(get_current_user)):
    """Get pipeline job details"""
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = pipeline_jobs[job_id]
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return job


@app.get("/api/pipeline/jobs/{job_id}/download/{file_type}")
async def download_output(job_id: str, file_type: str, user: User = Depends(get_current_user)):
    """Download output files"""
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = pipeline_jobs[job_id]
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return file based on file_type (pptx, txt, sql, etc.)
    # Implementation depends on output structure
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
        # Send current status if job exists
        if job_id in pipeline_jobs:
            await websocket.send_json({
                "type": "status",
                "data": pipeline_jobs[job_id]
            })
        
        # Keep connection alive
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

