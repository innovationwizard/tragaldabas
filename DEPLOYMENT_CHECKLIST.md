# Batch-Aware Genesis Deployment Checklist

**Created**: February 3, 2026
**Context**: New batch-aware genesis flow needs deployment and testing

---

## 📦 What Changed

### Code Changes
- ✅ [web/api.py](web/api.py) - Batch-aware status logic
  - Line 130-150: `promote_batch_to_awaiting_genesis()` function
  - Line 938: Sets `ready_for_genesis` after stage 7
  - Line 1065-1068: Triggers batch promotion
  - Line 746-797: Batch genesis triggering
- ✅ [frontend/src/pages/Pipeline.jsx](frontend/src/pages/Pipeline.jsx) - UI for `ready_for_genesis`
- ✅ [frontend/src/pages/Results.jsx](frontend/src/pages/Results.jsx) - Accepts `ready_for_genesis` status

### New Tooling
- ✅ [SYSTEMATIC_DEBUGGING_PROTOCOL.md](SYSTEMATIC_DEBUGGING_PROTOCOL.md) - Phase 6A for batch debugging
- ✅ [quick-debug.sh](quick-debug.sh) - Enhanced with batch awareness
- ✅ [check-batch-status.sh](check-batch-status.sh) - New batch diagnosis tool
- ✅ [DEBUGGING_TOOLS_README.md](DEBUGGING_TOOLS_README.md) - Complete tooling guide

---

## 🚀 Deployment Steps

### Step 1: Verify Local State
```bash
# Check what's ready to deploy
git status

# Review changes
git diff web/api.py
git diff frontend/src/pages/Pipeline.jsx
git diff frontend/src/pages/Results.jsx
```

**Expected**: All batch-aware changes present in working directory

---

### Step 2: Deploy to Vercel (API)

The API (`web/api.py`) runs on Vercel and must be deployed first.

```bash
# Commit changes if not already committed
git add web/api.py frontend/
git commit -m "Add batch-aware genesis flow with coordinated status transitions"

# Push to trigger Vercel deployment
git push origin main

# Monitor deployment
# Option A: CLI
vercel ls --app tragaldabas

# Option B: Dashboard
# https://vercel.com/dashboard
```

**Verify deployment**:
```bash
# Check API health (update URL to your Vercel deployment)
curl https://tragaldabas.vercel.app/health

# Or check specific endpoint
curl https://tragaldabas.vercel.app/api/pipeline/jobs
```

**Expected**: Vercel shows successful deployment, API responds

---

### Step 3: Deploy to Railway (Worker)

The worker shares `web/api.py` logic and must also be redeployed.

```bash
# Railway auto-deploys on git push, so same push triggers both
# Wait for Railway deployment (~2-3 minutes)

# Monitor deployment
railway status

# Check logs for startup
railway logs --tail 20
```

**Look for**:
```
Worker commit: <latest-commit-hash>
🚀 TRAGALDABAS WORKER STARTING
✅ GENERATOR.PY FIX VERIFIED
```

**Verify deployment**:
```bash
# Check worker health
curl https://tragaldabas-worker-production.up.railway.app/health

# Should return with config status
```

**Expected**: Worker running latest commit, health check passes

---

### Step 4: Run Pre-Flight Checks

```bash
# Run automated health check
./quick-debug.sh
```

**Expected output**:
- ✓ Worker is responding
- ✓ Code versions match
- ✓ No uncommitted changes
- ✓ All environment variables set
- ✓ Authentication works

**If any checks fail**: Fix before proceeding to testing

---

### Step 5: Test Batch Flow End-to-End

#### 5.1 Upload Multiple Files

```bash
# In browser or via API
# Upload 2-3 small Excel files at once
# Ensure "App Generation" is enabled
```

**Expected**:
- All files get same `batch_id`
- Each file has unique `batch_order`
- All files start at status `running`

#### 5.2 Monitor Stage 7 Completion

```bash
# Get batch_id from first upload response
BATCH_ID="<batch-id-from-upload>"

# Watch batch status in real-time
watch -n 3 "./check-batch-status.sh $BATCH_ID"
```

**Expected progression**:
1. Jobs process stages 1-7 (status: `running`)
2. First job completes stage 7 → status: `ready_for_genesis`
3. Subsequent jobs complete stage 7 → status: `ready_for_genesis`
4. When ALL jobs reach `ready_for_genesis` → ALL promoted to `awaiting_genesis`

**Timeline**: ~2-5 minutes per file for stages 1-7

#### 5.3 Verify Batch Promotion

```bash
# Check final batch state
./check-batch-status.sh $BATCH_ID
```

**Expected**:
```
📊 Batch status: 3/3 app_generation jobs ready
💡 Diagnosis:
✓ All jobs ready! Click GENESIS button on any job to start.
```

**If stuck at `ready_for_genesis`**:
- Check diagnosis from `check-batch-status.sh`
- See [SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 6A](SYSTEMATIC_DEBUGGING_PROTOCOL.md#phase-6a-batch-promotion-analysis-15-minutes-new)

#### 5.4 Trigger Genesis

```bash
# In browser
# Click GENESIS button on any one job in the batch
# (Should trigger ALL jobs together)
```

**Expected**:
- All jobs change to status: `pending_genesis`
- Railway logs show processing for ALL jobs
- All jobs progress through stages 8-12

**Monitor**:
```bash
# Watch Railway logs
railway logs --tail 50 | grep -E "(genesis|stage 8|stage 9|stage 10|stage 11|stage 12)"

# Watch batch progress
watch -n 3 "./check-batch-status.sh $BATCH_ID"
```

#### 5.5 Verify Completion

```bash
# Final check
./check-batch-status.sh $BATCH_ID
```

**Expected**:
```
📊 Batch status: 0/3 app_generation jobs ready
   • completed: 3

💡 Diagnosis:
✓ All jobs completed! Batch is done.
```

---

## ✅ Success Criteria

### Batch Promotion
- [x] Individual jobs reach `ready_for_genesis` after stage 7
- [x] Jobs wait at `ready_for_genesis` until batch is ready
- [x] All jobs promoted to `awaiting_genesis` simultaneously
- [x] Frontend shows appropriate waiting message

### Batch Triggering
- [x] Single GENESIS click triggers all batch jobs
- [x] All jobs move to `pending_genesis` together
- [x] Worker processes all jobs through stages 8-12
- [x] All jobs complete or fail independently

### Single-File Behavior
- [x] Single uploads skip batch logic (no `batch_id`)
- [x] Single uploads go directly to `awaiting_genesis`
- [x] Single uploads work as before

---

## 🐛 Common Issues During Testing

### Issue 1: Jobs Stuck at `ready_for_genesis`

**Symptom**: All jobs at `ready_for_genesis`, not promoting

**Diagnosis**:
```bash
./check-batch-status.sh $BATCH_ID
```

**Likely Causes**:
1. **Vercel API not deployed** - Promotion logic not active
   - Fix: Verify Vercel deployment, check logs
2. **Race condition** - Multiple jobs completed simultaneously
   - Fix: Manual promotion (see Phase 6A.4C)
3. **Code error** - Exception in promotion function
   - Fix: Check Vercel logs for errors

**Quick Fix**:
```bash
# Manual promotion
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis'
WHERE batch_id = '$BATCH_ID'
  AND app_generation = true
  AND status = 'ready_for_genesis'
"
```

### Issue 2: Genesis Doesn't Trigger All Jobs

**Symptom**: Click GENESIS, only one job starts processing

**Diagnosis**: Check [web/api.py:746-797](web/api.py#L746-L797) logic

**Likely Causes**:
1. **API not deployed** - Old logic still running
2. **Frontend caching** - Hard refresh (Cmd+Shift+R)
3. **Jobs not in `awaiting_genesis`** - Check actual status

**Fix**: Redeploy API, clear browser cache

### Issue 3: Worker Doesn't Process Genesis Jobs

**Symptom**: Jobs stuck at `pending_genesis`

**Diagnosis**:
```bash
railway logs --tail 100 | grep -E "(pending_genesis|genesis|error)"
```

**Likely Causes**:
1. **Worker not deployed** - Old code running
2. **Code bug in stages 8-12** - Check logs for traceback
3. **Configuration issue** - Missing environment variables

**Fix**: See [SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 3-4](SYSTEMATIC_DEBUGGING_PROTOCOL.md)

---

## 📊 Monitoring Commands

### Real-Time Batch Monitoring
```bash
# Watch batch status (updates every 3 seconds)
watch -n 3 "./check-batch-status.sh $BATCH_ID"
```

### Railway Worker Logs
```bash
# All logs
railway logs --tail 50

# Genesis-specific
railway logs --tail 100 | grep -i genesis

# Errors only
railway logs --tail 200 | grep -i -E "(error|exception|failed)"
```

### Database Direct Query
```bash
# Quick status check
supabase db query --project ncrgbzxypujhzhbhzvbv "
SELECT id, filename, status, stage, batch_order
FROM pipeline_jobs
WHERE batch_id = '$BATCH_ID'
ORDER BY batch_order
"
```

### Vercel Logs
```bash
# CLI (if installed)
vercel logs

# Or check dashboard:
# https://vercel.com/dashboard
```

---

## 🔄 Rollback Plan

If batch-aware flow causes issues:

### Option 1: Revert to Previous Status Logic

```bash
# Revert api.py changes
git revert <commit-hash>
git push origin main

# Manually fix stuck jobs
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis'
WHERE status = 'ready_for_genesis'
  AND app_generation = true
"
```

### Option 2: Feature Flag

Add to `web/api.py`:
```python
BATCH_AWARE_GENESIS = os.getenv("BATCH_AWARE_GENESIS", "true").lower() == "true"

# Then wrap batch logic
if BATCH_AWARE_GENESIS and batch_id:
    await promote_batch_to_awaiting_genesis(batch_id)
else:
    await update_job_in_db(job_id, {"status": "awaiting_genesis"})
```

Set environment variable in Vercel to disable:
```bash
vercel env add BATCH_AWARE_GENESIS false
```

---

## 📝 Post-Deployment Tasks

### 1. Document Test Results

Update [DEBUGGING_GENESIS_STUCK_JOBS.md](DEBUGGING_GENESIS_STUCK_JOBS.md):
```markdown
## Batch-Aware Flow Deployment - [Date]

**Test Results**:
- Batch promotion: ✅/❌
- Batch triggering: ✅/❌
- Single-file behavior: ✅/❌

**Issues Found**: [None / List issues]
**Fixes Applied**: [None / List fixes]
```

### 2. Monitor Production

```bash
# Watch for errors over next hour
railway logs --tail 50 > logs-$(date +%Y%m%d-%H%M%S).log

# Check every 15 minutes
watch -n 900 "./quick-debug.sh >> monitoring.log"
```

### 3. User Communication

If deploying to production with real users:
- Notify users of new batch behavior
- Document "Waiting for batch..." message meaning
- Provide support contact if issues arise

---

## 🎯 Quick Reference

| Step | Command | Expected Result |
|------|---------|----------------|
| Deploy | `git push origin main` | Vercel + Railway deploy |
| Verify API | `curl https://...vercel.app/health` | 200 OK |
| Verify Worker | `curl https://...railway.app/health` | 200 OK |
| Health Check | `./quick-debug.sh` | All ✓ |
| Test Upload | Upload 2-3 Excel files | Get batch_id |
| Monitor Batch | `./check-batch-status.sh $BATCH_ID` | See progression |
| Check Logs | `railway logs --tail 50` | No errors |

---

## 🆘 Emergency Contacts

- **Railway Dashboard**: https://railway.app/project/ade3d250-9036-4ef0-8430-44aa981d5883
- **Vercel Dashboard**: https://vercel.com/dashboard
- **Supabase Dashboard**: https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv
- **Debugging Guide**: [SYSTEMATIC_DEBUGGING_PROTOCOL.md](SYSTEMATIC_DEBUGGING_PROTOCOL.md)
- **Tooling Guide**: [DEBUGGING_TOOLS_README.md](DEBUGGING_TOOLS_README.md)

---

**Status**: Ready for deployment
**Last Updated**: February 3, 2026
**Next Action**: Deploy to Vercel and Railway, then test batch flow
