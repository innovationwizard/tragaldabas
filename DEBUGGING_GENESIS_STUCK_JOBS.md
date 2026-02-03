# Genesis Pipeline Debugging - Stuck Jobs Issue

**Date**: February 3, 2026
**Issue**: Two pipeline jobs stuck at `pending_genesis` status after completing stage 7

## Initial Problem

Two jobs were stuck and not progressing:
- **Comisiones.xlsx** (`bc79d695-2877-40d1-adc6-3caf92149198`)
- **Reservas.xlsx** (`680e7e08-a9a6-4492-af98-b9db2712d822`)

Both jobs:
- Completed stages 1-7 successfully
- Reached `pending_genesis` status
- Were not being processed by the Railway worker

## Root Causes Identified

### 1. Configuration Issues

#### WORKER_URL Misconfiguration
**Location**: Supabase Edge Function environment variables
**Issue**: Edge Function was calling incorrect worker URL

```
❌ Incorrect: https://tragaldabas-worker.up.railway.app
✅ Correct:   https://tragaldabas-worker-production.up.railway.app
```

**Evidence**:
- `railway status --json` showed actual URL: `tragaldabas-worker-production.up.railway.app`
- curl to wrong URL returned 404
- curl to correct URL returned healthy response

**Fix**: Updated `WORKER_URL` in Supabase Dashboard → Edge Functions → process-pipeline → Secrets

#### Missing RAILWAY_API_KEY
**Location**: Supabase Edge Function environment variables
**Issue**: Edge Function couldn't authenticate with Railway worker

**Code Reference**: [supabase/functions/process-pipeline/index.ts:99-104](supabase/functions/process-pipeline/index.ts:99-104)
```typescript
if (WORKER_URL) {
  const railwayKey = Deno.env.get('RAILWAY_API_KEY')
  if (!railwayKey) {
    throw new Error('Missing RAILWAY_API_KEY - required when WORKER_URL is set')
  }
  authToken = railwayKey
}
```

**Fix**: Added `RAILWAY_API_KEY` secret to Supabase Edge Function with value from Railway environment variables

### 2. Code Bugs in Stage 8 (Cell Classification)

#### Bug #1: DefinedNameDict Iteration Error
**File**: `stages/s8_cell_classification/classifier.py:209`
**Commit**: `6dea2d3`

**Error**:
```python
AttributeError: 'DefinedNameDict' object has no attribute 'definedName'
```

**Root Cause**: Incorrect iteration over openpyxl's `defined_names` object

**Original Code**:
```python
for defined_name in workbook.defined_names.definedName:
```

**Fixed Code**:
```python
for defined_name in workbook.defined_names.values():
```

**Evidence**: Railway worker logs showed traceback at line 209

#### Bug #2: RGB Color Type Conversion
**File**: `stages/s8_cell_classification/classifier.py:322-324`
**Commit**: `7cbfa3a`

**Error**:
```
1 validation error for CellFormatting
font_color - Input should be a valid string [type=string_type, input_value=Values must be of type <class 'str'>, input_type=RGB]
```

**Root Cause**: RGB objects from openpyxl were not converted to strings before passing to Pydantic model

**Original Code**:
```python
if cell.font and cell.font.color:
    font_color = getattr(cell.font.color, "rgb", None)
if cell.fill and getattr(cell.fill, "fgColor", None):
    fill_color = getattr(cell.fill.fgColor, "rgb", None)
```

**Fixed Code**:
```python
if cell.font and cell.font.color:
    rgb = getattr(cell.font.color, "rgb", None)
    font_color = str(rgb) if rgb is not None else None
if cell.fill and getattr(cell.fill, "fgColor", None):
    rgb = getattr(cell.fill.fgColor, "rgb", None)
    fill_color = str(rgb) if rgb is not None else None
```

**Evidence**: Direct worker call returned Pydantic validation error

#### Bug #3: NoneType Range Boundaries
**File**: `stages/s8_cell_classification/classifier.py:286`
**Commit**: `14fb378`

**Error**:
```python
TypeError: unsupported operand type(s) for -: 'NoneType' and 'NoneType'
```

**Root Cause**: `range_boundaries()` function returned None values, but code didn't check before arithmetic operations

**Original Code**:
```python
try:
    min_col, min_row, max_col, max_row = range_boundaries(address)
except ValueError:
    return []

total = (max_row - min_row + 1) * (max_col - min_col + 1)
```

**Fixed Code**:
```python
try:
    min_col, min_row, max_col, max_row = range_boundaries(address)
except ValueError:
    return []

# Handle None values from range_boundaries
if None in (min_col, min_row, max_col, max_row):
    return [f"{sheet_name}!{address}"]

total = (max_row - min_row + 1) * (max_col - min_col + 1)
```

**Evidence**: Railway logs showed TypeError during genesis processing

## Debugging Steps Taken

### 1. Initial Investigation
```bash
# Check Railway worker health
curl https://tragaldabas-worker-production.up.railway.app/health

# Response showed worker was running and configured correctly
```

### 2. Configuration Verification
```bash
# Check Railway environment variables
railway variables | grep -E "(WORKER_URL|RAILWAY_API_KEY)"

# Found RAILWAY_API_KEY set in Railway: 61CD2803-47E3-45EE-B48A-2D41E05B8203
```

### 3. Worker Authentication Testing
```bash
# Test with wrong API key
curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/test-job-id" \
  -H "Authorization: Bearer wrong-key"

# Response: {"detail":"Invalid API key"}
# ✅ Confirms authentication is working
```

### 4. Direct Worker Calls
```bash
# Get Railway API key
RAILWAY_KEY=$(railway variables --json | python3 -c "import sys, json; print(json.load(sys.stdin)['RAILWAY_API_KEY'])")

# Call worker directly for Comisiones.xlsx
curl -X POST "https://tragaldabas-worker-production.up.railway.app/process/bc79d695-2877-40d1-adc6-3caf92149198" \
  -H "Authorization: Bearer $RAILWAY_KEY"

# First attempt revealed Bug #1 (DefinedNameDict)
# Second attempt revealed Bug #2 (RGB color)
# Third attempt revealed Bug #3 (NoneType range)
```

### 5. Log Analysis
```bash
# Monitor Railway worker logs
railway logs --tail 200 | grep -E "(bc79d695|680e7e08|error|genesis)"

# Revealed each bug in sequence as they were encountered
```

## Deployment History

| Commit | Description | Deployment Time |
|--------|-------------|-----------------|
| `6dea2d3` | Fix DefinedNameDict iteration bug | ~2 minutes |
| `7cbfa3a` | Fix RGB color conversion | ~2 minutes |
| `14fb378` | Fix NoneType range boundaries | ~2 minutes |

All deployments to Railway succeeded automatically via GitHub webhook.

## Hard Facts

### Job Status Transitions
```
Initial:        pending_genesis (stuck)
                     ↓
After retry:    failed (due to Bug #1)
                     ↓
After retry:    running → awaiting_genesis (Bug #1 fixed, stages 1-7 complete)
                     ↓
Trigger genesis:pending_genesis
                     ↓
Genesis attempt:failed (due to Bug #2)
                     ↓
After retry:    running → awaiting_genesis (Bug #2 fixed, stages 1-7 complete)
                     ↓
Trigger genesis:pending_genesis
                     ↓
Genesis attempt:failed (due to Bug #3)
                     ↓
After retry:    running (Bug #3 fixed, stages 1-7 in progress)
```

### Environment Configuration
- **Supabase URL**: `https://ncrgbzxypujhzhbhzvbv.supabase.co`
- **Railway Worker URL**: `https://tragaldabas-worker-production.up.railway.app`
- **Railway Project**: `tragaldabas-worker` (production environment)
- **Worker Port**: 8080
- **Railway API Key**: UUID format starting with `61CD2803-`

### File Locations
- **Worker**: `/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/worker.py`
- **Cell Classifier**: `/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/stages/s8_cell_classification/classifier.py`
- **Edge Function**: `/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/supabase/functions/process-pipeline/index.ts`
- **API**: `/Users/jorgeluiscontrerasherrera/Documents/_git/tragaldabas/web/api.py`

### Pipeline Stages
- **Stages 1-7**: Data extraction, analysis, insights (ETL pipeline)
- **Stages 8-12**: App generation (genesis pipeline)
  - Stage 8: Cell Classification
  - Stage 9: Dependency Graph
  - Stage 10: Logic Extraction
  - Stage 11: Code Generation
  - Stage 12: Scaffold & Deploy

## Current Status

**As of last check**:
- ✅ All three bugs fixed and deployed
- ✅ Configuration corrected (WORKER_URL + RAILWAY_API_KEY)
- 🔄 Both jobs processing stages 1-7 (will reach `awaiting_genesis` soon)
- ⏳ Genesis stages 8-12 ready to be triggered with all fixes in place

## Next Steps

1. **Wait for jobs to complete stages 1-7** (~2-5 minutes)
2. **Verify status in dashboard**: Both jobs should show `awaiting_genesis`
3. **Trigger genesis**: Click "Genesis" button on each job
4. **Monitor progress**: Genesis should complete without errors
5. **Validate output**: Check generated applications

## Verification Commands

```bash
# Check worker health
curl https://tragaldabas-worker-production.up.railway.app/health

# Check job status via Supabase
curl "https://ncrgbzxypujhzhbhzvbv.supabase.co/rest/v1/pipeline_jobs?id=in.(bc79d695-2877-40d1-adc6-3caf92149198,680e7e08-a9a6-4492-af98-b9db2712d822)&select=id,filename,status" \
  -H "apikey: YOUR_SUPABASE_ANON_KEY"

# Monitor Railway logs
railway logs --tail 100 | grep -E "(bc79d695|680e7e08|genesis|error)"

# Check Railway deployment status
railway status
```

## Lessons Learned

1. **Configuration issues can masquerade as code bugs**: The initial stuck jobs were due to misconfiguration, not code issues
2. **Openpyxl API gotchas**:
   - `defined_names` is a `DefinedNameDict`, iterate with `.values()`
   - Color objects (RGB) need explicit string conversion
   - `range_boundaries()` can return None values
3. **Edge Function environment**: Secrets must be set in Supabase Dashboard, not local `.env` files
4. **Worker authentication**: Railway worker requires separate API key, distinct from Supabase keys
5. **Job status behavior**: Failed jobs restart from stage 1, not from the failed stage

## References

- Railway Dashboard: https://railway.app/project/ade3d250-9036-4ef0-8430-44aa981d5883
- Supabase Dashboard: https://supabase.com/dashboard/project/ncrgbzxypujhzhbhzvbv
- Worker Deployment Guide: `docs/WORKER_DEPLOYMENT.md`
- Git commits: `6dea2d3`, `7cbfa3a`, `14fb378`
