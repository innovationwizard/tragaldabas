# Genesis Pipeline Debugging Tools

**Created**: February 3, 2026
**Purpose**: Systematic debugging of batch-aware Genesis pipeline

---

## 📚 Documentation Files

### 1. [SYSTEMATIC_DEBUGGING_PROTOCOL.md](SYSTEMATIC_DEBUGGING_PROTOCOL.md)
**Comprehensive debugging methodology** - The definitive guide for diagnosing Genesis pipeline issues.

**What it contains**:
- 6 debugging phases covering all failure modes
- **NEW Phase 6A**: Batch promotion analysis for `ready_for_genesis` status
- Decision matrix for quick issue identification
- Step-by-step procedures with exact commands
- Common issues and solutions
- Emergency procedures

**When to use**: Deep investigation of stuck jobs, complex issues, or when automated tools don't reveal the problem.

### 2. [DEBUGGING_GENESIS_STUCK_JOBS.md](DEBUGGING_GENESIS_STUCK_JOBS.md)
**Historical debugging log** - Documents previous issues and their resolutions.

**What it contains**:
- Root causes identified: Configuration issues + 3 code bugs
- Evidence and fix commits
- Deployment history
- Lessons learned

**When to use**: Reference for similar issues that have been fixed before.

---

## 🔧 Automated Debugging Scripts

### 1. [quick-debug.sh](quick-debug.sh)
**Quick health check** - Runs common diagnostic checks in ~30 seconds.

**What it checks**:
- ✓ Worker health and responsiveness
- ✓ Code version deployed vs local
- ✓ Uncommitted changes
- ✓ Environment variables (Railway)
- ✓ Authentication
- ✓ Recent errors in logs
- ✓ Job status (including batch awareness)
- ✓ Batch promotion status (NEW)

**Usage**:
```bash
./quick-debug.sh
```

**When to use**: First step in any debugging session. Run this before anything else.

**Output**: Color-coded summary with actionable recommendations.

### 2. [check-batch-status.sh](check-batch-status.sh)
**Batch diagnosis tool** - Analyzes batch-aware genesis flow in detail.

**What it shows**:
- All jobs in a batch with current status
- App generation vs non-app jobs
- Batch promotion state
- Blocking jobs (if any)
- Specific diagnosis with recommended actions

**Usage**:
```bash
# Using job ID
./check-batch-status.sh bc79d695-2877-40d1-adc6-3caf92149198

# Using batch ID directly
./check-batch-status.sh <batch-uuid>
```

**When to use**:
- Jobs stuck at `ready_for_genesis`
- Batch not promoting to `awaiting_genesis`
- Need to understand why batch isn't ready
- Debugging batch coordination issues

**Output**: Detailed batch state with visual job list and specific diagnosis.

### 3. [retry-jobs.sh](retry-jobs.sh)
**Job retry utility** - Restarts failed or stuck jobs.

**Usage**:
```bash
./retry-jobs.sh
```

**When to use**: When jobs have failed and need to be restarted.

---

## 🎯 Debugging Workflow

### Quick Issue → Start Here
```bash
./quick-debug.sh
```

If it identifies issues, follow the on-screen recommendations.

### Batch-Specific Issues
```bash
# Check batch state
./check-batch-status.sh <job-id>

# Follow diagnosis recommendations
# See SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 6A
```

### Deep Investigation
```bash
# Open the comprehensive guide
cat SYSTEMATIC_DEBUGGING_PROTOCOL.md

# Follow the phase that matches your symptom
# Use the Decision Matrix (section 📊)
```

---

## 🔄 New Batch-Aware Flow

### Status Progression
```
Upload → running (stages 1-7) → ready_for_genesis (individual)
                                         ↓
                              Wait for ALL batch jobs
                                         ↓
                              awaiting_genesis (batch)
                                         ↓
                              User clicks GENESIS
                                         ↓
                              pending_genesis (all jobs)
                                         ↓
                              running (stages 8-12) → completed
```

### Key Changes (Feb 3, 2026)
1. **New status**: `ready_for_genesis` - Individual job completion
2. **Batch coordination**: Jobs wait for entire batch
3. **Batch promotion**: All jobs move to `awaiting_genesis` together
4. **Batch triggering**: One click triggers ALL batch jobs

### Critical Functions
- [web/api.py:130-150](web/api.py#L130-L150) - `promote_batch_to_awaiting_genesis()`
- [web/api.py:1065-1068](web/api.py#L1065-L1068) - Promotion trigger
- [web/api.py:746-797](web/api.py#L746-L797) - `/api/pipeline/genesis/{job_id}` endpoint

---

## 📊 Common Scenarios

### Scenario 1: Jobs Stuck at `ready_for_genesis`

**Check batch state:**
```bash
./check-batch-status.sh <job-id>
```

**Possible causes:**
1. **Other jobs still running** - Normal, wait for completion
2. **One job failed** - Blocking batch, retry failed job
3. **All ready but not promoted** - Batch promotion bug, see Phase 6A.4C

### Scenario 2: All Jobs `awaiting_genesis` but Button Doesn't Work

**Run health check:**
```bash
./quick-debug.sh
```

**Check frontend:**
- Browser console for errors
- Network tab for failed API calls
- See SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 5

### Scenario 3: Genesis Triggered but Jobs Not Processing

**Check worker:**
```bash
railway logs --tail 50
```

**Look for:**
- Errors in Python traceback
- Missing configuration
- Authentication failures

**See**: SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 4

### Scenario 4: One Job in Batch Keeps Failing

**Direct worker test:**
```bash
RAILWAY_KEY=$(railway variables --json | python3 -c "import sys, json; print(json.load(sys.stdin)['RAILWAY_API_KEY'])")

curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/<job-id>" \
  -H "Authorization: Bearer $RAILWAY_KEY" \
  -v
```

**Check Railway logs for specific error**
**See**: SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 2

---

## 🚨 Emergency Quick Fixes

### Manual Batch Promotion
If batch is stuck with all jobs ready but not promoted:

```bash
# Get batch ID from any job
BATCH_ID="<batch-uuid>"

# Manually promote all app_generation jobs
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis'
WHERE batch_id = '$BATCH_ID'
  AND app_generation = true
  AND status = 'ready_for_genesis'
"
```

### Force Worker Restart
If worker is completely unresponsive:

```bash
railway down
sleep 5
railway up -d
railway logs --tail 20
```

### Reset Job to Known State
If job is in corrupted state:

```bash
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis', stage = 7, error = NULL
WHERE id = '<job-id>'
"
```

---

## 📖 Reference Information

### Environment Details
- **Supabase URL**: `https://ncrgbzxypujhzhbhzvbv.supabase.co`
- **Railway Worker**: `https://tragaldabas-worker-production.up.railway.app`
- **Worker Health**: `https://tragaldabas-worker-production.up.railway.app/health`

### Pipeline Stages
- **1-7**: ETL Pipeline (data extraction, analysis, insights)
- **8-12**: Genesis Pipeline (app generation)
  - Stage 8: Cell Classification
  - Stage 9: Dependency Graph
  - Stage 10: Logic Extraction
  - Stage 11: Code Generation
  - Stage 12: Scaffold & Deploy

### Key Job Statuses
- `running` - Processing stages 1-7
- `ready_for_genesis` - Stage 7 complete, waiting for batch (NEW)
- `awaiting_genesis` - Ready for user to click GENESIS button
- `pending_genesis` - Genesis triggered, waiting for worker
- `running` - Processing stages 8-12
- `completed` - All stages done
- `failed` - Error occurred

### Dashboard Links
- [Railway Dashboard](https://railway.app/project/ade3d250-9036-4ef0-8430-44aa981d5883)
- [Supabase Dashboard](https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv)
- [Edge Function Logs](https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv/functions/process-pipeline/logs)

---

## 🎓 Debugging Best Practices

1. **Always start with quick-debug.sh** - It catches 80% of issues
2. **Use check-batch-status.sh for batch issues** - Visualizes batch state
3. **Check Railway logs early** - Errors appear there first
4. **Verify code deployment** - Local changes aren't active until deployed
5. **Document findings** - Update DEBUGGING_GENESIS_STUCK_JOBS.md
6. **Test incrementally** - Fix one issue, verify, then move to next
7. **Use direct worker calls** - Bypass entire frontend/API stack for testing

---

## 🔍 Decision Matrix Quick Reference

| Current Status | Likely Issue | Tool to Use | Protocol Phase |
|----------------|--------------|-------------|----------------|
| `failed` | Code bug or data issue | `quick-debug.sh` + Railway logs | Phase 2 |
| `ready_for_genesis` | Batch not ready or promotion failed | `check-batch-status.sh` | Phase 6A |
| `pending_genesis` | Worker not processing | `quick-debug.sh` + Railway logs | Phase 3 |
| `running` (>5 min) | Worker stuck on stage | Railway logs + direct call | Phase 4 |
| `awaiting_genesis` (button broken) | Frontend or API issue | Browser console | Phase 5 |

---

## 📝 Next Steps After Fixing

1. **Document the fix** in [DEBUGGING_GENESIS_STUCK_JOBS.md](DEBUGGING_GENESIS_STUCK_JOBS.md)
2. **Update this README** if you discover new patterns
3. **Commit changes** with clear message
4. **Deploy** to Railway/Vercel
5. **Verify** with test upload
6. **Monitor** for recurrence

---

## 💡 Tips

- **Watch mode**: `watch -n 2 './check-batch-status.sh <job-id>'` for real-time updates
- **Parallel debugging**: Open multiple terminals - one for logs, one for commands
- **Save outputs**: `./quick-debug.sh > debug-$(date +%Y%m%d-%H%M%S).log` for records
- **Test files**: Keep a small test Excel file for quick validation uploads

---

**Last Updated**: February 3, 2026
**Maintainer**: Genesis Pipeline Team
**Version**: 2.0 (Batch-Aware)
