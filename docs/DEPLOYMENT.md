# Deployment Options

## Problem

Vercel serverless functions have a **250 MB unzipped size limit**. The Tragaldabas pipeline requires heavy dependencies:
- `pandas` (~12 MB)
- `numpy` (~16 MB)
- LLM libraries (anthropic, openai, google-generativeai)
- File processing libraries (openpyxl, python-docx, python-pptx)
- Database drivers (psycopg2-binary)

These dependencies exceed Vercel's limits when combined.

## Solutions

### Option 1: Separate Worker Service (Recommended)

Deploy the pipeline processing to a separate service:

**Railway** (Recommended):
```bash
# Deploy worker with full dependencies
railway up --service worker
```

**Render**:
- Create a new Web Service
- Use `requirements-full.txt` for dependencies
- Set start command: `python -m web.worker`

**Fly.io**:
```bash
fly launch --name tragaldabas-worker
```

**Worker Service Architecture**:
- API endpoints stay on Vercel (lightweight)
- Worker service handles `/api/pipeline/process/{job_id}`
- Worker has access to all dependencies
- No size limitations

### Option 2: Supabase Edge Functions

Rewrite pipeline processing in TypeScript/Deno:

**Pros**:
- No size limitations
- Integrated with Supabase
- Serverless scaling

**Cons**:
- Requires rewriting Python pipeline code in TypeScript
- More development time

**Setup**:
1. Create Edge Function: `supabase/functions/process-pipeline/index.ts`
2. Port pipeline logic from Python to TypeScript
3. Use Deno-compatible libraries

### Option 3: Vercel Pro Plan

Upgrade to Vercel Pro for higher limits:
- Higher function size limits
- Longer execution times
- More resources

**Cost**: $20/month per member

### Option 4: Hybrid Approach (Current)

**Current Setup**:
- API endpoints on Vercel (minimal dependencies)
- Edge Function triggers processing
- Processing endpoint returns 503 if dependencies unavailable
- Worker service can be added later

**To Add Worker**:
1. Deploy worker service with `requirements-full.txt`
2. Update Edge Function to call worker instead of Vercel API
3. Or update Vercel API to proxy to worker

## Recommended Architecture

```
┌─────────────┐
│   Frontend  │ (Vercel)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Vercel API │ (Minimal - Auth, Job Management)
└──────┬──────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│   Supabase  │   │   Worker    │ (Railway/Render)
│     DB      │   │  (Pipeline) │
└─────────────┘   └──────────────┘
```

## Quick Start: Railway Worker

1. **Create `worker.py`**:
```python
from fastapi import FastAPI
from web.api import app, process_job

# Worker only handles pipeline processing
worker_app = FastAPI()

@worker_app.post("/process/{job_id}")
async def worker_process(job_id: str):
    # Process job with full dependencies
    return await process_job(job_id, ...)
```

2. **Deploy to Railway**:
```bash
railway init
railway up
```

3. **Update Edge Function** to call Railway worker instead of Vercel API

## Current Status

✅ **Deployed**:
- Frontend (Vercel)
- API endpoints (Vercel - minimal)
- Supabase Edge Function
- Database (Supabase)

⚠️ **Needs Worker**:
- Pipeline processing (requires heavy dependencies)

## Next Steps

1. Choose deployment option (Railway recommended)
2. Deploy worker service
3. Update Edge Function to call worker
4. Test end-to-end flow

