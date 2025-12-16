# Vercel Deployment Guide

## Issue: Serverless Function Size Limit

Vercel has a 250 MB unzipped size limit for serverless functions. The Tragaldabas application includes heavy dependencies (pandas, numpy, LLM libraries) that exceed this limit.

## Solutions

### Option 1: Lazy Imports (Recommended)

Modify `web/api.py` to use lazy imports for heavy dependencies:

```python
# Instead of:
from orchestrator import Orchestrator

# Use:
def get_orchestrator():
    from orchestrator import Orchestrator
    return Orchestrator(...)
```

### Option 2: Separate API and Worker

Split the application:
- **API Serverless Function**: Lightweight, handles requests
- **Worker/Queue**: Processes pipeline jobs (can be deployed separately)

### Option 3: Use Vercel's Edge Functions

For simple endpoints, use Edge Functions instead of serverless functions.

### Option 4: Deploy Backend Separately

Deploy the FastAPI backend to:
- Railway
- Render
- Fly.io
- AWS Lambda (with proper configuration)
- Google Cloud Run

And deploy only the frontend to Vercel.

## Current Configuration

- `vercel.json` - Vercel configuration
- `requirements.txt` - Minimal requirements for Vercel deployment (auto-detected by Vercel)
- `requirements-full.txt` - Full requirements for local development
- `.vercelignore` - Excludes heavy files from deployment

## Recommended Approach

For production, consider deploying:
1. **Frontend** → Vercel (static site)
2. **Backend** → Railway/Render/Fly.io (full Python environment)

This allows:
- Full access to all dependencies
- Better performance for long-running pipeline jobs
- No size limitations
- Better WebSocket support

## Quick Fix for Vercel

If you must deploy to Vercel, implement lazy imports in `web/api.py`:

```python
# Lazy import heavy dependencies
def run_pipeline(job_id: str, file_path: str, user_id: int):
    # Import only when needed
    from orchestrator import Orchestrator
    from ui.progress import WebProgressTracker
    from ui.prompts import WebUserPrompt
    from config import settings
    # ... rest of function
```

This reduces the initial function size significantly.

