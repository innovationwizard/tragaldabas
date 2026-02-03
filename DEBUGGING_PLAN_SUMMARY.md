# Systematic Debugging Plan - Executive Summary

**Date**: February 3, 2026
**Status**: Issue persists - Comprehensive debugging system created
**Context**: Batch-aware Genesis flow deployed, new debugging methodology needed

---

## 🎯 What Was Created

A complete systematic debugging framework for the Genesis pipeline with special focus on the new batch-aware flow.

### 📖 Documentation (4 files)

1. **[SYSTEMATIC_DEBUGGING_PROTOCOL.md](SYSTEMATIC_DEBUGGING_PROTOCOL.md)** ⭐ PRIMARY
   - 6 debugging phases covering all failure scenarios
   - **NEW Phase 6A**: Batch promotion analysis
   - Decision matrix for rapid diagnosis
   - Step-by-step procedures with exact commands
   - 50+ pages of comprehensive troubleshooting

2. **[DEBUGGING_TOOLS_README.md](DEBUGGING_TOOLS_README.md)** ⭐ START HERE
   - Quick reference for all tools
   - Usage guide for each script
   - Common scenarios and solutions
   - Decision matrix quick reference

3. **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)**
   - Deployment steps for batch-aware flow
   - Testing procedures
   - Rollback plan
   - Monitoring commands

4. **[DEBUGGING_GENESIS_STUCK_JOBS.md](DEBUGGING_GENESIS_STUCK_JOBS.md)** (existing)
   - Historical debugging log
   - Previous fixes documented
   - Lessons learned

### 🔧 Automated Scripts (3 files)

1. **[quick-debug.sh](quick-debug.sh)** ⭐ RUN FIRST
   - 8 automated health checks
   - Batch-aware status detection
   - Color-coded output
   - Takes ~30 seconds
   - **Command**: `./quick-debug.sh`

2. **[check-batch-status.sh](check-batch-status.sh)** ⭐ FOR BATCH ISSUES
   - Detailed batch state analysis
   - Visual job list with statuses
   - Specific diagnosis and recommendations
   - **Command**: `./check-batch-status.sh <job-id-or-batch-id>`

3. **[retry-jobs.sh](retry-jobs.sh)** (existing)
   - Retry failed jobs
   - **Command**: `./retry-jobs.sh`

---

## 🚀 How to Use This System

### Step 1: Quick Diagnosis (30 seconds)
```bash
./quick-debug.sh
```

**This tells you**:
- ✓ Is the system healthy?
- ✓ What's the current job status?
- ✓ Are jobs in a batch?
- ✓ What phase should you investigate?

### Step 2: If Batch Issue (1 minute)
```bash
./check-batch-status.sh <job-id>
```

**This shows**:
- All jobs in the batch
- Which jobs are ready vs blocking
- Specific diagnosis with action items
- Direct link to relevant protocol phase

### Step 3: Deep Investigation (varies)
```bash
# Open the comprehensive protocol
open SYSTEMATIC_DEBUGGING_PROTOCOL.md

# Navigate to the phase identified in Step 1 or 2
# Follow step-by-step procedures
```

---

## 🔄 Batch-Aware Flow Overview

### New Status: `ready_for_genesis`

**What it means**: Job completed stage 7, waiting for other batch jobs

### Flow Diagram
```
Individual Job:     Stage 7 complete → ready_for_genesis
                                              ↓
Batch Coordination: Wait for ALL batch jobs to reach ready_for_genesis
                                              ↓
Batch Promotion:    ALL jobs promoted → awaiting_genesis (together)
                                              ↓
User Action:        Click GENESIS on any one job
                                              ↓
Batch Trigger:      ALL jobs → pending_genesis (triggers together)
                                              ↓
Processing:         Worker processes each → stages 8-12 → completed
```

### Key Differences from Before
| Before | After (Batch-Aware) |
|--------|---------------------|
| Each job independent | Jobs coordinate in batches |
| Stage 7 → `awaiting_genesis` | Stage 7 → `ready_for_genesis` |
| Click GENESIS triggers 1 job | Click GENESIS triggers ALL batch jobs |
| No waiting | Wait for batch to be ready |

---

## 🎯 Common Scenarios

### Scenario 1: "Jobs stuck at ready_for_genesis"

**Quick diagnosis**:
```bash
./check-batch-status.sh <job-id>
```

**Likely causes**:
1. ✅ **Normal**: Other jobs still processing stage 7 (wait)
2. ⚠️ **One job failed**: Blocking entire batch (retry failed job)
3. 🚨 **Promotion failed**: All ready but not promoted (see Phase 6A.4C)

**Action**: Follow recommendation from `check-batch-status.sh`

---

### Scenario 2: "All jobs awaiting_genesis but button doesn't work"

**Quick diagnosis**:
```bash
./quick-debug.sh
```

**Likely causes**:
1. Frontend issue (check browser console)
2. API issue (check Vercel logs)
3. Configuration issue (will be detected by quick-debug.sh)

**Action**: See [SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 5](SYSTEMATIC_DEBUGGING_PROTOCOL.md#phase-5-uifrontend-analysis-10-minutes)

---

### Scenario 3: "Genesis triggered but jobs not processing"

**Quick diagnosis**:
```bash
railway logs --tail 50
./quick-debug.sh
```

**Likely causes**:
1. Worker code error (check Railway logs for traceback)
2. Configuration missing (check environment variables)
3. Worker not receiving requests (check authentication)

**Action**: See [SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 3-4](SYSTEMATIC_DEBUGGING_PROTOCOL.md#phase-3-genesis-trigger-analysis-15-minutes)

---

### Scenario 4: "One job in batch keeps failing"

**Quick diagnosis**:
```bash
./check-batch-status.sh <batch-id>
railway logs --tail 200 | grep <job-id>
```

**Likely causes**:
1. File-specific issue (complex formulas, corrupted data)
2. Code bug in worker (stages 8-12)
3. Resource limits (memory, timeout)

**Action**: See [SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 2](SYSTEMATIC_DEBUGGING_PROTOCOL.md#phase-2-error-analysis-10-minutes)

---

## 📊 Debugging Decision Tree

```
Start: Issue persists
    ↓
Run: ./quick-debug.sh
    ↓
    ├─ System unhealthy? → Fix detected issues, redeploy
    ├─ Status = failed? → Phase 2: Error Analysis
    ├─ Status = ready_for_genesis? → Run ./check-batch-status.sh
    │   ├─ Waiting for batch? → Normal, wait
    │   ├─ One job blocking? → Fix/retry blocking job
    │   └─ All ready, not promoted? → Phase 6A.4C
    ├─ Status = pending_genesis? → Phase 3: Genesis Trigger
    ├─ Status = running (>5 min)? → Phase 4: Worker Processing
    └─ Status = awaiting_genesis? → Phase 5: Frontend Issue
```

---

## ✅ System Health Checklist

Before investigating issues, verify:

- [x] Worker is responding: `curl https://...railway.app/health`
- [x] Worker has latest code: `railway logs | grep "Worker commit"`
- [x] API deployed to Vercel: `git log -1 -- web/api.py`
- [x] No uncommitted changes: `git status`
- [x] Environment variables set: `./quick-debug.sh`
- [x] No recent errors: `railway logs --tail 100`

**Command**: `./quick-debug.sh` checks all of the above automatically

---

## 🆘 Emergency Procedures

### Nuclear Option: Manual Batch Promotion
If all jobs ready but stuck:
```bash
# Get batch ID
BATCH_ID="<batch-uuid>"

# Manually promote
supabase db query --project ncrgbzxypujhzhbhzvbv "
UPDATE pipeline_jobs
SET status = 'awaiting_genesis'
WHERE batch_id = '$BATCH_ID'
  AND app_generation = true
  AND status = 'ready_for_genesis'
"
```

### Nuclear Option: Reset Worker
If worker completely stuck:
```bash
railway down && sleep 5 && railway up -d
railway logs --tail 20
```

### Nuclear Option: Direct Worker Call
Bypass everything, call worker directly:
```bash
RAILWAY_KEY=$(railway variables --json | python3 -c "import sys, json; print(json.load(sys.stdin)['RAILWAY_API_KEY'])")

curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/<job-id>" \
  -H "Authorization: Bearer $RAILWAY_KEY" \
  -v
```

---

## 📈 Next Steps

### Immediate: Diagnose Current Issue
1. **Run**: `./quick-debug.sh`
2. **If batch issue**: `./check-batch-status.sh <job-id>`
3. **Follow** the specific recommendations provided
4. **Document** findings in [DEBUGGING_GENESIS_STUCK_JOBS.md](DEBUGGING_GENESIS_STUCK_JOBS.md)

### Before Deployment: Test Batch Flow
1. **Follow**: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. **Deploy** API to Vercel
3. **Deploy** Worker to Railway
4. **Test** end-to-end with 2-3 files
5. **Verify** batch promotion and triggering work

### Ongoing: Monitor Production
1. **Run** `./quick-debug.sh` daily or when issues reported
2. **Check** Railway logs for errors: `railway logs --tail 200 | grep -i error`
3. **Monitor** batch promotions with `check-batch-status.sh`
4. **Update** documentation when new issues discovered

---

## 📖 File Quick Reference

| File | Purpose | When to Use |
|------|---------|-------------|
| [DEBUGGING_TOOLS_README.md](DEBUGGING_TOOLS_README.md) | Overview of all tools | Start here, reference guide |
| [SYSTEMATIC_DEBUGGING_PROTOCOL.md](SYSTEMATIC_DEBUGGING_PROTOCOL.md) | Deep troubleshooting | Complex issues, step-by-step |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Deployment guide | Before/during deployment |
| [quick-debug.sh](quick-debug.sh) | Automated health check | Every debugging session |
| [check-batch-status.sh](check-batch-status.sh) | Batch diagnosis | Batch-specific issues |
| [retry-jobs.sh](retry-jobs.sh) | Retry failed jobs | Jobs failed, need restart |

---

## 🎓 Key Insights

### What We Know
1. ✅ Previous bugs fixed: DefinedNameDict, RGB colors, NoneType ranges
2. ✅ Configuration verified: WORKER_URL, RAILWAY_API_KEY
3. ✅ Worker healthy: Latest code deployed, responding
4. ✅ Batch flow implemented: `ready_for_genesis` status, promotion logic

### What to Investigate
1. 🔍 **Batch promotion**: Is it triggering correctly?
2. 🔍 **Race conditions**: Multiple jobs completing simultaneously?
3. 🔍 **Vercel deployment**: Is latest API code active?
4. 🔍 **Edge Function**: Is it calling worker for all batch jobs?

### What to Monitor
1. 📊 Job transitions: `ready_for_genesis` → `awaiting_genesis`
2. 📊 Batch coordination: All jobs reaching ready together
3. 📊 Genesis triggering: All batch jobs starting together
4. 📊 Worker processing: Stages 8-12 completing successfully

---

## 💡 Pro Tips

1. **Use watch mode**: `watch -n 2 './check-batch-status.sh <job-id>'` for real-time monitoring
2. **Parallel terminals**: Logs in one, commands in another
3. **Save outputs**: `./quick-debug.sh > debug-$(date +%Y%m%d-%H%M%S).log`
4. **Test files**: Keep small test Excel files for quick validation
5. **Direct worker calls**: Fastest way to test bypassing all layers

---

## 🎯 Success Metrics

You'll know the system is working when:

- ✅ `./quick-debug.sh` passes all checks
- ✅ Multiple file uploads create batch with same `batch_id`
- ✅ Each job reaches `ready_for_genesis` after stage 7
- ✅ ALL jobs promoted to `awaiting_genesis` together
- ✅ Single GENESIS click triggers ALL batch jobs
- ✅ All jobs complete stages 8-12 successfully

---

**Ready to Start**: Run `./quick-debug.sh` to begin diagnosis

**Questions?** See [DEBUGGING_TOOLS_README.md](DEBUGGING_TOOLS_README.md) for complete guide

**Deep Dive?** See [SYSTEMATIC_DEBUGGING_PROTOCOL.md](SYSTEMATIC_DEBUGGING_PROTOCOL.md) for full methodology
