# Worker Service Deployment Guide

## Quick Start: Railway

### 1. Login to Railway

```bash
railway login
```

This will open a browser for authentication.

### 2. Initialize Railway Project

```bash
railway init
```

Follow the prompts:
- Create new project: `tragaldabas-worker`
- Select your GitHub repo

### 3. Deploy Worker

```bash
railway up
```

Railway will automatically:
- Detect `railway.json` configuration
- Install dependencies from `requirements-full.txt`
- Start the worker with `python worker.py`

### 4. Set Environment Variables

In Railway Dashboard → Variables, add:

```
SUPABASE_URL=https://ncrgbzxypujhzhbhzvbv.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=your-database-url
ANTHROPIC_API_KEY=your-anthropic-key (or other LLM provider)
OUTPUT_DIR=/tmp/output
```

### 5. Get Worker URL

Railway will provide a URL like: `https://tragaldabas-worker.up.railway.app`

### 6. Update Edge Function

In Supabase Dashboard → Edge Functions → `process-pipeline` → Settings → Secrets:

Add:
```
WORKER_URL=https://tragaldabas-worker.up.railway.app
```

### 7. Test

Upload a file through the web app. The Edge Function should now call the Railway worker for processing.

## Alternative: Render

### 1. Create Account

Go to [render.com](https://render.com) and sign up

### 2. New Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select the `tragaldabas` repository

### 4. Configure Service

- **Name**: `tragaldabas-worker`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements-full.txt`
- **Start Command**: `python worker.py`
- **Plan**: Free or Starter

### 5. Environment Variables

Add the same environment variables as Railway (see step 4 above)

### 6. Deploy

Click "Create Web Service" - Render will deploy automatically

### 7. Update Edge Function

Add `WORKER_URL` secret pointing to your Render service URL

## Health Check

Test the worker is running:

```bash
curl https://your-worker-url.railway.app/health
```

Should return:
```json
{"status": "ok", "service": "pipeline-worker"}
```

## Troubleshooting

### Worker returns 401
- Check `SUPABASE_SERVICE_ROLE_KEY` is set correctly
- Verify the key matches your Supabase project

### Worker can't connect to database
- Check `DATABASE_URL` is set
- Verify database connection string format

### Pipeline fails with missing dependencies
- Ensure `requirements-full.txt` is being used
- Check Railway/Render logs for installation errors

### Edge Function can't reach worker
- Verify `WORKER_URL` is set in Edge Function secrets
- Check worker is publicly accessible (not behind auth)
- Test worker URL directly: `curl https://your-worker-url/health`

## Architecture

```
User Uploads File
    ↓
Vercel API (creates job, status: pending)
    ↓
Supabase Edge Function (triggered automatically)
    ↓
Railway/Render Worker (processes pipeline)
    ↓
Updates job status in Supabase DB
    ↓
Frontend polls for updates
```

## Cost Estimates

**Railway**:
- Free tier: $5 credit/month
- Hobby: $5/month (after free tier)
- Pro: $20/month

**Render**:
- Free tier: Limited hours
- Starter: $7/month

Both are suitable for development and small-scale production.

