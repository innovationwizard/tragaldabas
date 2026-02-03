#!/bin/bash
# Batch Status Checker for Genesis Pipeline
# Diagnoses batch-aware genesis flow issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "📦 BATCH STATUS CHECKER"
echo "======================="
echo ""

# Get job ID or batch ID from argument
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <job_id_or_batch_id>"
    echo ""
    echo "Examples:"
    echo "  $0 bc79d695-2877-40d1-adc6-3caf92149198"
    echo "  $0 batch-uuid-here"
    exit 1
fi

INPUT_ID="$1"

# Setup
SUPABASE_URL="https://ncrgbzxypujhzhbhzvbv.supabase.co"
ANON_KEY=$(grep VITE_SUPABASE_ANON_KEY frontend/.env 2>/dev/null | cut -d= -f2 | tr -d "'" | tr -d '"' || echo "")

if [[ -z "$ANON_KEY" ]]; then
    echo -e "${RED}✗${NC} Could not find VITE_SUPABASE_ANON_KEY in frontend/.env"
    exit 1
fi

# Function to query Supabase
query_supabase() {
    local filter=$1
    curl -s "$SUPABASE_URL/rest/v1/pipeline_jobs?$filter&select=id,filename,status,stage,app_generation,batch_id,batch_order,batch_total,updated_at" \
      -H "apikey: $ANON_KEY" \
      -H "Content-Type: application/json"
}

# Try to determine if input is job_id or batch_id
echo "🔍 Looking up ID: $INPUT_ID"
echo ""

# First, try as job_id
JOB_DATA=$(query_supabase "id=eq.$INPUT_ID")
BATCH_ID=""

if [[ "$JOB_DATA" != "[]" ]] && [[ "$JOB_DATA" != "" ]]; then
    echo -e "${GREEN}✓${NC} Found as job ID"
    BATCH_ID=$(echo "$JOB_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0].get('batch_id', '') if data and data[0].get('batch_id') else '')")

    if [[ -z "$BATCH_ID" ]] || [[ "$BATCH_ID" == "null" ]]; then
        echo -e "${BLUE}ℹ${NC}  This is a single-file job (no batch)"
        echo ""
        echo "$JOB_DATA" | python3 -m json.tool 2>/dev/null
        echo ""
        echo "Single-file jobs skip batch logic and go directly to 'awaiting_genesis'"
        exit 0
    fi
else
    # Try as batch_id
    BATCH_DATA=$(query_supabase "batch_id=eq.$INPUT_ID")
    if [[ "$BATCH_DATA" != "[]" ]] && [[ "$BATCH_DATA" != "" ]]; then
        echo -e "${GREEN}✓${NC} Found as batch ID"
        BATCH_ID="$INPUT_ID"
    else
        echo -e "${RED}✗${NC} ID not found in database"
        exit 1
    fi
fi

echo "📦 Batch ID: $BATCH_ID"
echo ""

# Get all jobs in batch
BATCH_JOBS=$(query_supabase "batch_id=eq.$BATCH_ID&order=batch_order.asc")

if [[ "$BATCH_JOBS" == "[]" ]] || [[ -z "$BATCH_JOBS" ]]; then
    echo -e "${RED}✗${NC} No jobs found for batch $BATCH_ID"
    exit 1
fi

# Parse batch data
TOTAL_JOBS=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data))")
APP_GEN_JOBS=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len([j for j in data if j.get('app_generation')]))")

echo "📊 Batch Overview"
echo "   Total jobs: $TOTAL_JOBS"
echo "   App generation jobs: $APP_GEN_JOBS"
echo ""

# Display job statuses
echo "📋 Job Status Details:"
echo ""
echo "$BATCH_JOBS" | python3 << 'PYEOF'
import sys
import json
from datetime import datetime

data = json.load(sys.stdin)

# ANSI colors
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
GRAY = '\033[0;37m'
NC = '\033[0m'

for job in data:
    order = job.get('batch_order', '?')
    filename = job.get('filename', 'Unknown')[:30].ljust(30)
    status = job.get('status', 'unknown')
    stage = job.get('stage', '?')
    app_gen = '📱' if job.get('app_generation') else '📄'

    # Color code status
    if status == 'completed':
        status_color = GREEN
    elif status == 'ready_for_genesis':
        status_color = YELLOW
    elif status == 'awaiting_genesis':
        status_color = BLUE
    elif status == 'pending_genesis':
        status_color = BLUE
    elif status == 'running':
        status_color = YELLOW
    elif status == 'failed':
        status_color = RED
    else:
        status_color = GRAY

    print(f"   {order}. {app_gen} {filename} | Stage {stage} | {status_color}{status}{NC}")

PYEOF

echo ""

# Analyze batch state
echo "🔬 Batch Analysis:"
echo ""

READY_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'ready_for_genesis'))")
AWAITING_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'awaiting_genesis'))")
PENDING_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'pending_genesis'))")
RUNNING_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'running'))")
COMPLETED_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'completed'))")
FAILED_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'failed'))")
OTHER_COUNT=$(echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); statuses=['ready_for_genesis','awaiting_genesis','pending_genesis','running','completed','failed']; print(sum(1 for j in data if j.get('app_generation') and j.get('status') not in statuses))")

echo "   App generation jobs by status:"
echo "   • ready_for_genesis: $READY_COUNT"
echo "   • awaiting_genesis:  $AWAITING_COUNT"
echo "   • pending_genesis:   $PENDING_COUNT"
echo "   • running:           $RUNNING_COUNT"
echo "   • completed:         $COMPLETED_COUNT"
echo "   • failed:            $FAILED_COUNT"
if [[ "$OTHER_COUNT" != "0" ]]; then
    echo "   • other:             $OTHER_COUNT"
fi
echo ""

# Diagnosis
echo "💡 Diagnosis:"
echo ""

if [[ "$COMPLETED_COUNT" == "$APP_GEN_JOBS" ]]; then
    echo -e "${GREEN}✓${NC} All jobs completed! Batch is done."
elif [[ "$FAILED_COUNT" != "0" ]]; then
    echo -e "${RED}⚠${NC}  $FAILED_COUNT job(s) failed - blocking batch progression"
    echo "   Action: Retry failed jobs or investigate errors"
    echo "   Command: ./retry-jobs.sh"
elif [[ "$RUNNING_COUNT" != "0" ]]; then
    echo -e "${YELLOW}⏳${NC} $RUNNING_COUNT job(s) currently processing"
    echo "   Action: Wait for jobs to complete, monitor Railway logs"
    echo "   Command: railway logs --tail 50"
elif [[ "$PENDING_COUNT" != "0" ]]; then
    echo -e "${BLUE}⏳${NC} $PENDING_COUNT job(s) pending genesis trigger"
    echo "   Action: Wait for Railway worker to process"
    echo "   Command: railway logs --tail 50"
elif [[ "$AWAITING_COUNT" == "$APP_GEN_JOBS" ]]; then
    echo -e "${GREEN}✓${NC} All jobs ready! Click GENESIS button on any job to start."
    echo "   This will trigger ALL $APP_GEN_JOBS jobs together."
elif [[ "$AWAITING_COUNT" != "0" ]] && [[ "$AWAITING_COUNT" != "$APP_GEN_JOBS" ]]; then
    echo -e "${YELLOW}⚠${NC}  Partial batch promotion - unexpected state"
    echo "   Expected: ALL jobs at awaiting_genesis or NONE"
    echo "   Actual: $AWAITING_COUNT/$APP_GEN_JOBS at awaiting_genesis"
    echo "   Action: Check SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 6A.4"
elif [[ "$READY_COUNT" == "$APP_GEN_JOBS" ]]; then
    echo -e "${YELLOW}⚠${NC}  All jobs ready but NOT promoted to awaiting_genesis"
    echo "   This indicates a batch promotion failure."
    echo ""
    echo "   Possible causes:"
    echo "   1. Last job didn't trigger promotion (check Vercel logs)"
    echo "   2. Race condition (multiple jobs completed simultaneously)"
    echo "   3. Vercel API not deployed with latest batch logic"
    echo ""
    echo "   Action: See SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 6A.4C"
    echo ""
    echo "   Quick fix (manual promotion):"
    echo "   Update all jobs to awaiting_genesis status in database"
elif [[ "$READY_COUNT" != "0" ]]; then
    echo -e "${YELLOW}⏳${NC} Batch partially ready: $READY_COUNT/$APP_GEN_JOBS jobs at ready_for_genesis"
    echo "   Waiting for remaining jobs to complete stage 7"
    echo ""
    echo "   Blocking jobs:"
    echo "$BATCH_JOBS" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f\"      • {j.get('filename')} - {j.get('status')} (stage {j.get('stage')})\") for j in data if j.get('app_generation') and j.get('status') != 'ready_for_genesis']"
else
    echo -e "${BLUE}ℹ${NC}  Jobs are in early stages (not yet at ready_for_genesis)"
    echo "   Wait for jobs to complete stages 1-7"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📖 For detailed debugging: SYSTEMATIC_DEBUGGING_PROTOCOL.md"
echo "🔧 Quick health check: ./quick-debug.sh"
echo "🔄 Retry failed jobs: ./retry-jobs.sh"
