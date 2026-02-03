# Systematic Debugging Protocol for Genesis Pipeline Issues

**Created**: February 3, 2026
**Status**: Active - Issue persists despite previous fixes
**Context**: Jobs stuck at pending_genesis; three bugs fixed but problem continues

---

## 🎯 Debugging Philosophy

**Core Principle**: Verify assumptions at every layer. Don't assume anything works until proven.

**Methodology**: Binary search through the system - isolate each component, test independently, eliminate possibilities systematically.

## 🔄 New Batch-Aware Genesis Flow (Feb 3, 2026)

**Critical Change**: Genesis is now batch-aware with coordinated status transitions.

### Status Flow
```
Stage 7 complete → ready_for_genesis (individual job)
        ↓
Wait for ALL batch jobs to reach ready_for_genesis
        ↓
ALL batch jobs promoted → awaiting_genesis (batch-level)
        ↓
User clicks GENESIS on any one job
        ↓
ALL batch jobs → pending_genesis (triggers all together)
        ↓
Worker processes each job → running → completed
```

### Key Functions
- **[web/api.py:130-150](web/api.py#L130-L150)**: `promote_batch_to_awaiting_genesis()` - Batch promotion logic
- **[web/api.py:938](web/api.py#L938)**: Sets `ready_for_genesis` after stage 7
- **[web/api.py:1065-1068](web/api.py#L1065-L1068)**: Calls batch promotion or single promotion
- **[web/api.py:746-797](web/api.py#L746-L797)**: `/api/pipeline/genesis/{job_id}` endpoint - Batch triggering

### Important
- Jobs no longer go directly to `awaiting_genesis` after stage 7
- Single-file uploads skip batch logic (no `batch_id`)
- Frontend shows "Waiting for batch..." message for `ready_for_genesis` status

---

## 📋 Phase 1: State Verification (15 minutes)

### 1.1 Get Current Job Status

```bash
# Check database directly - Get job IDs and their actual status
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT
  id,
  filename,
  status,
  stage,
  created_at,
  updated_at,
  error_message
FROM pipeline_jobs
WHERE id IN (
  'bc79d695-2877-40d1-adc6-3caf92149198',
  '680e7e08-a9a6-4492-af98-b9db2712d822'
)
ORDER BY updated_at DESC
"
```

**Critical Questions**:
- What is the exact current status? (`pending_genesis`, `running`, `failed`, `awaiting_genesis`)
- When was `updated_at` last modified?
- Is there an error_message field populated?
- What is the current stage number?

**Decision Tree**:
- If `status = 'failed'` → Go to Phase 2: Error Analysis
- If `status = 'ready_for_genesis'` → Go to **Phase 6A: Batch Promotion Analysis** (NEW)
- If `status = 'pending_genesis'` → Go to Phase 3: Genesis Trigger Analysis
- If `status = 'running'` → Go to Phase 4: Worker Processing Analysis
- If `status = 'awaiting_genesis'` → Go to Phase 5: UI/Frontend Analysis

---

### 1.2 Verify Code Deployment

```bash
# Check what code is actually running on Railway
railway logs --tail 5 | grep "Worker commit"

# Compare with local repo
git rev-parse HEAD

# Check if local changes are uncommitted
git status --short

# Verify the three fixes are present in deployed code
railway run python3 -c "
import inspect
from stages.s8_cell_classification.classifier import CellClassifier
source = inspect.getsource(CellClassifier._extract_format_info)
print('✓ RGB fix present' if 'str(rgb)' in source else '✗ RGB fix MISSING')
"
```

**Critical Questions**:
- Is Railway running the latest commit?
- Are there local uncommitted changes?
- Are the specific bug fixes actually in the deployed code?

**Red Flags**:
- 🚨 Railway commit ≠ Local HEAD commit
- 🚨 Git shows uncommitted changes to critical files
- 🚨 Fix verification fails

---

### 1.3 Check All Configuration

```bash
# Railway environment variables
railway variables | grep -E "(WORKER_URL|RAILWAY_API_KEY|SUPABASE)" | sort

# Supabase Edge Function environment
# Manual check required in Dashboard:
# https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv/functions/process-pipeline

# Frontend environment
cat frontend/.env | grep -E "(API_URL|SUPABASE)"
```

**Critical Questions**:
- Is `WORKER_URL` = `https://tragaldabas-worker-production.up.railway.app`?
- Is `RAILWAY_API_KEY` set in both Railway AND Supabase Edge Function?
- Do all URLs match actual deployed services?

**Configuration Matrix** (all must be ✓):
```
Railway Worker:
  ✓ SUPABASE_URL = https://ncrgbzxypujhzhbhzvbv.supabase.co
  ✓ SUPABASE_SERVICE_KEY = [set]
  ✓ RAILWAY_API_KEY = [UUID format]

Supabase Edge Function:
  ✓ WORKER_URL = https://tragaldabas-worker-production.up.railway.app
  ✓ RAILWAY_API_KEY = [same UUID as Railway]
  ✓ SUPABASE_URL = https://ncrgbzxypujhzhbhzvbv.supabase.co
  ✓ SUPABASE_SERVICE_KEY = [set]

Frontend:
  ✓ VITE_SUPABASE_URL = https://ncrgbzxypujhzhbhzvbv.supabase.co
  ✓ VITE_SUPABASE_ANON_KEY = [set]
```

---

## 🔬 Phase 2: Error Analysis (10 minutes)

**Condition**: Job status is `failed` or has `error_message`

### 2.1 Extract Full Error Stack

```bash
# Get error from database
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT error_message, error_details, updated_at
FROM pipeline_jobs
WHERE id = 'bc79d695-2877-40d1-adc6-3caf92149198'
"

# Get error from Railway logs
railway logs --tail 500 | grep -A 20 "bc79d695-2877-40d1-adc6-3caf92149198"
```

### 2.2 Error Classification

**Type A: Python Exception**
- Contains "Traceback", "Exception", "Error"
- **Action**: Identify file:line, read code, fix bug
- **Pattern**: Same as bugs #1, #2, #3 previously fixed

**Type B: Validation Error**
- Contains "validation error", "Pydantic"
- **Action**: Check Pydantic model vs actual data types
- **Example**: RGB color bug was this type

**Type C: Network/Timeout Error**
- Contains "timeout", "connection", "502", "503"
- **Action**: Check service health, network connectivity
- **Root cause**: Usually configuration or infrastructure

**Type D: Authentication Error**
- Contains "401", "403", "Invalid API key", "Unauthorized"
- **Action**: Verify API keys match between services
- **Root cause**: Configuration mismatch

**Type E: Missing Data Error**
- Contains "KeyError", "None", "not found"
- **Action**: Check if file/data exists, validate upload
- **Root cause**: Corrupted job state or missing file

### 2.3 Error Resolution Playbook

For each error type:
1. **Reproduce locally** (if possible)
2. **Write minimal test case**
3. **Fix and verify** with test
4. **Deploy** and monitor logs
5. **Retry job** with direct worker call
6. **Verify** job progresses to next stage

---

## 🔄 Phase 3: Genesis Trigger Analysis (15 minutes)

**Condition**: Job status is `pending_genesis` (stuck waiting for genesis to start)

### 3.1 Understand Genesis Flow

```
User clicks "Genesis" button
        ↓
Frontend sends API request
        ↓
API calls trigger_genesis_for_job()
        ↓
API updates job status to 'pending_genesis'
        ↓
API calls Supabase Edge Function
        ↓
Edge Function determines worker URL
        ↓
Edge Function calls Railway worker /process/{job_id}
        ↓
Worker updates status to 'running'
        ↓
Worker processes stages 8-12
        ↓
Worker updates status to 'completed'
```

**Potential Failure Points**:
1. Frontend doesn't send request
2. API endpoint fails
3. Status update fails
4. Edge Function isn't triggered
5. Edge Function gets wrong URL
6. Edge Function auth fails
7. Worker never receives request
8. Worker crashes during processing

### 3.2 Test Each Link in Chain

#### Test 1: Can we trigger genesis via API?

```bash
# Get Supabase anon key from frontend
ANON_KEY=$(grep VITE_SUPABASE_ANON_KEY frontend/.env | cut -d= -f2)

# Call API directly
curl -X POST "https://ncrgbzxypujhzhbhzvbv.supabase.co/rest/v1/rpc/trigger_genesis_for_job" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "bc79d695-2877-40d1-adc6-3caf92149198"}'
```

**Expected**: Job status changes OR get error response
**If fails**: API layer issue (database, RLS, function)

#### Test 2: Does Edge Function get triggered?

```bash
# Check Edge Function logs
# Manual: https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv/functions/process-pipeline/logs

# Look for recent invocations
# Should see: "Processing job: bc79d695-2877-40d1-adc6-3caf92149198"
```

**Expected**: Log entry for job ID within last few seconds
**If fails**: Database trigger or Edge Function not deploying

#### Test 3: Does Edge Function call worker successfully?

```bash
# Check Railway logs for incoming requests
railway logs --tail 100 | grep -E "(POST /process|bc79d695)"
```

**Expected**: `POST /process/bc79d695-2877-40d1-adc6-3caf92149198`
**If fails**:
- Edge Function has wrong WORKER_URL → Check Supabase secrets
- Edge Function auth failing → Check RAILWAY_API_KEY matches
- Network issue → Test worker endpoint from external

#### Test 4: Bypass everything - call worker directly

```bash
# Get Railway API key
RAILWAY_KEY=$(railway variables --json | python3 -c "import sys, json; print(json.load(sys.stdin)['RAILWAY_API_KEY'])")

# Call worker directly
curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/bc79d695-2877-40d1-adc6-3caf92149198" \
  -H "Authorization: Bearer $RAILWAY_KEY" \
  -H "Content-Type: application/json" \
  -v
```

**Expected**: Job starts processing (status → running)
**If succeeds**: Problem is in Edge Function or API layer
**If fails**: Problem is in worker code (go to Phase 2)

---

## ⚙️ Phase 4: Worker Processing Analysis (20 minutes)

**Condition**: Job status is `running` but not progressing

### 4.1 Identify Stuck Stage

```bash
# Check job progress
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT id, filename, status, stage,
       extract(epoch from (now() - updated_at)) as seconds_stuck
FROM pipeline_jobs
WHERE id = 'bc79d695-2877-40d1-adc6-3caf92149198'
"
```

**Questions**:
- What stage number is it stuck on?
- How long has it been stuck? (normal: 1-3 min/stage, stuck: >5 min)

### 4.2 Monitor Worker Logs in Real-Time

```bash
# Watch logs as job processes
railway logs --tail 50 | grep -E "(bc79d695|stage|error|Exception)"

# In parallel, check for CPU/memory issues
railway logs --tail 10 | grep -E "(memory|killed|OOM)"
```

### 4.3 Stage-Specific Debugging

#### Stage 8: Cell Classification
```bash
# Verify fixes are deployed
railway run python3 << 'EOF'
from stages.s8_cell_classification.classifier import CellClassifier
import inspect

# Check Bug #1 fix (DefinedNameDict)
source = inspect.getsource(CellClassifier._identify_named_ranges)
assert 'defined_names.values()' in source, "Bug #1 fix missing!"

# Check Bug #2 fix (RGB conversion)
source = inspect.getsource(CellClassifier._extract_format_info)
assert 'str(rgb)' in source, "Bug #2 fix missing!"

# Check Bug #3 fix (NoneType range)
source = inspect.getsource(CellClassifier._expand_named_range)
assert 'if None in' in source, "Bug #3 fix missing!"

print("✅ All three fixes verified in deployed code")
EOF
```

#### Stage 9: Dependency Graph
```bash
# Common issue: Circular dependencies
railway logs --tail 200 | grep -A 10 "stage 9"
```

#### Stage 10: Logic Extraction
```bash
# Common issue: Complex formulas
railway logs --tail 200 | grep -A 10 "stage 10"
```

#### Stage 11: Code Generation
```bash
# Common issue: f-string syntax errors
railway logs --tail 200 | grep -A 10 "stage 11"
```

#### Stage 12: Scaffold & Deploy
```bash
# Common issue: File I/O, permissions
railway logs --tail 200 | grep -A 10 "stage 12"
```

### 4.4 Database Lock Check

```bash
# Check if job updates are being written
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT
  id,
  status,
  stage,
  updated_at,
  NOW() - updated_at as age
FROM pipeline_jobs
WHERE id = 'bc79d695-2877-40d1-adc6-3caf92149198'
"

# Run again after 30 seconds
sleep 30
# [repeat query]
```

**If `updated_at` doesn't change**: Worker isn't updating database
- Check SUPABASE_SERVICE_KEY in Railway
- Check RLS policies on pipeline_jobs table
- Check database connection errors in logs

---

## 🖥️ Phase 5: UI/Frontend Analysis (10 minutes)

**Condition**: Job status is `awaiting_genesis` but button doesn't trigger genesis

### 5.1 Check Frontend Logs

```bash
# Open browser console
# Look for API call to trigger_genesis_for_job
# Check for errors (401, 403, 500, CORS)
```

### 5.2 Verify API Integration

```typescript
// Check file: frontend/src/api/jobs.ts or similar
// Verify function calls correct endpoint
// Verify auth headers are included
```

### 5.3 Test Button Manually

```javascript
// Run in browser console
fetch('https://ncrgbzxypujhzhbhzvbv.supabase.co/rest/v1/rpc/trigger_genesis_for_job', {
  method: 'POST',
  headers: {
    'apikey': 'YOUR_ANON_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({job_id: 'bc79d695-2877-40d1-adc6-3caf92149198'})
})
.then(r => r.json())
.then(console.log)
```

---

## 📦 Phase 6A: Batch Promotion Analysis (15 minutes) **NEW**

**Condition**: Job status is `ready_for_genesis` (stuck waiting for batch promotion)

### 6A.1 Understand Batch State

```bash
# Get all jobs in the batch
JOB_ID="bc79d695-2877-40d1-adc6-3caf92149198"

# First, get the batch_id
BATCH_ID=$(supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT batch_id FROM pipeline_jobs WHERE id = '$JOB_ID'
" --output json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['batch_id'] if data and data[0].get('batch_id') else 'null')")

echo "Batch ID: $BATCH_ID"

# Get all jobs in this batch
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT
  id,
  filename,
  status,
  stage,
  app_generation,
  batch_order,
  updated_at
FROM pipeline_jobs
WHERE batch_id = '$BATCH_ID'
ORDER BY batch_order
"
```

**Critical Questions**:
- How many jobs in the batch?
- How many have `app_generation = true`?
- What are their current statuses?
- Are ALL app_generation jobs at `ready_for_genesis`?

### 6A.2 Check Batch Promotion Logic

The promotion happens in [web/api.py:1065-1068](web/api.py#L1065-L1068):

```python
if app_generation:
    if job.get("batch_id"):
        await promote_batch_to_awaiting_genesis(job.get("batch_id"))
    else:
        await update_job_in_db(job_id, {"status": "awaiting_genesis"})
```

**Promotion Requirements** (all must be true):
1. ✓ `batch_id` is not null
2. ✓ At least one job has `app_generation = true`
3. ✓ ALL `app_generation` jobs have `status = 'ready_for_genesis'`

### 6A.3 Test Promotion Function Manually

```bash
# Get batch info
BATCH_ID="your-batch-id-here"

# Check what promotion would do
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT
  id,
  status,
  app_generation,
  CASE
    WHEN app_generation = true AND status = 'ready_for_genesis' THEN 'Will promote'
    WHEN app_generation = true AND status != 'ready_for_genesis' THEN 'Blocking: ' || status
    ELSE 'Not app generation'
  END as promotion_status
FROM pipeline_jobs
WHERE batch_id = '$BATCH_ID'
ORDER BY batch_order
"
```

### 6A.4 Common Batch Issues

#### Issue A: Mixed Status (Some ready, some not)
**Symptom**: Some jobs at `ready_for_genesis`, others at `running` or `failed`
**Cause**: One job in batch is slower or failed
**Solution**:
- Check logs for the blocking job
- If failed, retry it: `curl -X POST .../api/pipeline/jobs/{job_id}/retry`
- Wait for it to reach `ready_for_genesis`

#### Issue B: Non-app-generation Job Blocking
**Symptom**: Batch has mix of `app_generation = true` and `false` jobs
**Cause**: Some files in batch are not Excel files
**Expected Behavior**: Only Excel files with `app_generation = true` are included in promotion
**Verification**:
```bash
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT
  filename,
  app_generation,
  status
FROM pipeline_jobs
WHERE batch_id = '$BATCH_ID'
"
```

#### Issue C: Promotion Function Not Called
**Symptom**: ALL app_generation jobs at `ready_for_genesis` but not promoted
**Cause**: Last job to complete didn't trigger promotion
**Debug**:
```bash
# Check Vercel API logs for promotion call
# Look for: "promote_batch_to_awaiting_genesis" in logs

# Manually trigger promotion by completing any job again
# Or call API endpoint directly (if exists)
```

**Workaround**: Manually update status
```bash
# TEMPORARY FIX - manually promote all jobs
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis'
WHERE batch_id = '$BATCH_ID'
  AND app_generation = true
  AND status = 'ready_for_genesis'
"
```

#### Issue D: Race Condition
**Symptom**: Two jobs complete stage 7 simultaneously
**Cause**: Both check batch state before either updates, both see incomplete batch
**Evidence**: Check `updated_at` timestamps - if multiple jobs completed within 1 second
**Solution**: Add database transaction or locking (code change needed)

### 6A.5 Verify Vercel API Deployment

The batch promotion logic is in `web/api.py`, which must be deployed to Vercel:

```bash
# Check if local changes are deployed
git status

# Check recent Vercel deployments
vercel ls

# Check if api.py was updated recently
git log -1 --format="%H %s" -- web/api.py
```

**If not deployed**:
```bash
# Deploy to Vercel
git add web/api.py
git commit -m "Batch-aware genesis flow"
git push origin main

# Verify deployment
# Check Vercel dashboard or run: vercel ls
```

### 6A.6 Test Batch Flow End-to-End

```bash
# 1. Upload multiple Excel files at once
# 2. Monitor first job reaching ready_for_genesis
# 3. Monitor subsequent jobs reaching ready_for_genesis
# 4. Verify ALL jobs promoted to awaiting_genesis together
# 5. Click GENESIS on any one job
# 6. Verify ALL jobs triggered together

# Query to watch batch status in real-time
watch -n 2 "supabase db query --project ncrgbzxypujhzhbhzvbv \"
SELECT filename, status, stage, updated_at
FROM pipeline_jobs
WHERE batch_id = '$BATCH_ID'
ORDER BY batch_order
\""
```

---

## 🔧 Phase 6: Nuclear Options (30 minutes)

**Condition**: All previous phases failed to identify issue

### 6.1 Full System Reset

```bash
# 1. Stop all services
railway down

# 2. Clear any stuck processes
# [manual check in Railway dashboard]

# 3. Restart worker
railway up -d

# 4. Verify health
curl https://tragaldabas-worker-production.up.railway.app/health

# 5. Reset job to known state
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis', stage = 7
WHERE id = 'bc79d695-2877-40d1-adc6-3caf92149198'
"

# 6. Trigger genesis via direct worker call
RAILWAY_KEY=$(railway variables --json | python3 -c "import sys, json; print(json.load(sys.stdin)['RAILWAY_API_KEY'])")
curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/bc79d695-2877-40d1-adc6-3caf92149198" \
  -H "Authorization: Bearer $RAILWAY_KEY"
```

### 6.2 Create Minimal Test Case

```bash
# Upload a tiny, simple Excel file
# Single sheet, 2x2 grid, no formulas
# Track through entire pipeline

# If THIS fails → fundamental system issue
# If THIS succeeds → problem is with specific file (Comisiones.xlsx, Reservas.xlsx)
```

### 6.3 File-Specific Issues

```bash
# Check if files are corrupted
railway run python3 << 'EOF'
from openpyxl import load_workbook
import supabase

# Download file from storage
client = supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
data = client.storage.from_('excel-files').download('bc79d695-2877-40d1-adc6-3caf92149198/original.xlsx')

# Try to load
try:
    wb = load_workbook(data)
    print(f"✓ File loads successfully: {len(wb.sheetnames)} sheets")
except Exception as e:
    print(f"✗ File is corrupted: {e}")
EOF
```

### 6.4 Add Instrumentation

```python
# Add to worker.py or classifier.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Add progress logging
print(f"[STAGE 8] Starting cell classification for {job_id}")
print(f"[STAGE 8] Processing sheet {sheet_name}: {cell_count} cells")
print(f"[STAGE 8] Named ranges: {named_range_count}")
# etc.
```

Deploy with extra logging:
```bash
git add -A
git commit -m "Add debug instrumentation"
git push
# Wait for Railway to redeploy
railway logs --tail 100
```

---

## 📊 Decision Matrix

| Symptom | Likely Cause | Go To Phase |
|---------|--------------|-------------|
| Status = `failed` | Code bug | Phase 2 |
| Status = `ready_for_genesis` (stuck) | **Batch not ready or promotion failed** | **Phase 6A** |
| Status = `pending_genesis` (stuck) | Genesis trigger broken | Phase 3 |
| Status = `running` (>5 min on one stage) | Worker stuck | Phase 4 |
| Status = `awaiting_genesis` (button doesn't work) | Frontend issue | Phase 5 |
| Railway logs silent | Worker not receiving requests | Phase 3.2 |
| Railway logs show errors | Code bug | Phase 2 |
| Database `updated_at` not changing | Database connection issue | Phase 4.4 |
| Simple test file works, real files don't | File-specific issue | Phase 6.3 |
| Batch: some ready, some not | One job blocking batch | Phase 6A.4A |
| Batch: all ready, not promoted | Promotion logic issue | Phase 6A.4C |

---

## 🎯 Quick Win Checklist

Before deep debugging, verify these common issues:

```bash
# ✓ Worker is actually running
curl https://tragaldabas-worker-production.up.railway.app/health

# ✓ Worker has latest code
railway logs --tail 5 | grep "Worker commit"
git rev-parse HEAD

# ✓ Configuration is correct
railway variables | grep -E "RAILWAY_API_KEY|SUPABASE"

# ✓ Can call worker directly
RAILWAY_KEY=$(railway variables --json | python3 -c "import sys, json; print(json.load(sys.stdin)['RAILWAY_API_KEY'])")
curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/test-job-id" \
  -H "Authorization: Bearer $RAILWAY_KEY"

# ✓ No uncommitted local changes
git status --short

# ✓ Railway deployment succeeded
railway logs --tail 20 | grep -E "(Starting|Listening)"
```

---

## 🚨 Emergency Procedures

### If Worker Won't Start
```bash
railway logs --tail 50
# Look for import errors, syntax errors
# Fix locally, commit, push
```

### If Database Connection Fails
```bash
# Verify service key
supabase db query --project ncrgbzxypujhzhbhzvbv "SELECT 1"
```

### If Nothing Makes Sense
```bash
# Create fresh test job from scratch
# Upload new file via frontend
# Track from stage 1
# Compare behavior
```

---

## 📝 Logging Protocol

For every debugging session:

1. **Record exact time**: `date +"%Y-%m-%d %H:%M:%S"`
2. **Record exact job ID and status**: Query database
3. **Record command and output**: Copy-paste everything
4. **Record hypothesis before test**: "I think X is broken because Y"
5. **Record result**: "Confirmed" or "Rejected" + evidence

Example format:
```
2026-02-03 14:23:15 - Testing direct worker call
Hypothesis: Edge Function isn't calling worker
Command: curl -X POST https://... -H "Authorization: Bearer ..."
Result: 200 OK, job started processing
Conclusion: Edge Function IS working, problem must be elsewhere
```

---

## ✅ Success Criteria

A debugging session is complete when:

1. ✅ You can trigger genesis AND job completes stages 8-12 OR
2. ✅ You have identified exact failure point + root cause OR
3. ✅ You have reproducible test case that demonstrates the bug

Document findings immediately in `DEBUGGING_GENESIS_STUCK_JOBS.md`.

---

## 🔗 Quick Reference

- **Railway Dashboard**: https://railway.app/project/ade3d250-9036-4ef0-8430-44aa981d5883
- **Supabase Dashboard**: https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv
- **Edge Function Logs**: https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv/functions/process-pipeline/logs
- **Worker URL**: https://tragaldabas-worker-production.up.railway.app
- **Health Check**: https://tragaldabas-worker-production.up.railway.app/health

**Job IDs**:
- Comisiones.xlsx: `bc79d695-2877-40d1-adc6-3caf92149198`
- Reservas.xlsx: `680e7e08-a9a6-4492-af98-b9db2712d822`
