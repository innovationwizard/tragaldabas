#!/bin/bash
# Quick Win Debugging Script
# Runs the most common checks to identify genesis pipeline issues

set -e

echo "🔍 GENESIS PIPELINE QUICK DEBUG"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

echo "📍 1. Checking worker health..."
if curl -sf https://tragaldabas-worker-production.up.railway.app/health > /dev/null; then
    echo -e "${GREEN}✓${NC} Worker is responding"
    HEALTH_OUTPUT=$(curl -s https://tragaldabas-worker-production.up.railway.app/health)
    echo "   $HEALTH_OUTPUT"
else
    echo -e "${RED}✗${NC} Worker is not responding!"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "📍 2. Checking deployed code version..."
RAILWAY_COMMIT=$(railway logs --tail 5 | grep "Worker commit" | tail -1 | awk '{print $NF}' || echo "unknown")
LOCAL_COMMIT=$(git rev-parse HEAD)
LOCAL_SHORT=$(git rev-parse --short HEAD)

echo "   Railway: $RAILWAY_COMMIT"
echo "   Local:   $LOCAL_COMMIT"

if [[ "$RAILWAY_COMMIT" == "$LOCAL_COMMIT" ]] || [[ "$RAILWAY_COMMIT" == "$LOCAL_SHORT" ]]; then
    echo -e "${GREEN}✓${NC} Code versions match"
else
    echo -e "${YELLOW}⚠${NC}  Code versions differ - Railway may not have latest code"
fi
echo ""

echo "📍 3. Checking for uncommitted changes..."
if [[ -z $(git status --short) ]]; then
    echo -e "${GREEN}✓${NC} No uncommitted changes"
else
    echo -e "${YELLOW}⚠${NC}  Uncommitted changes detected:"
    git status --short | head -5
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "📍 4. Checking Railway environment variables..."
if railway variables | grep -q "RAILWAY_API_KEY"; then
    echo -e "${GREEN}✓${NC} RAILWAY_API_KEY is set"
else
    echo -e "${RED}✗${NC} RAILWAY_API_KEY is missing!"
    FAILURES=$((FAILURES + 1))
fi

if railway variables | grep -q "SUPABASE_URL"; then
    echo -e "${GREEN}✓${NC} SUPABASE_URL is set"
else
    echo -e "${RED}✗${NC} SUPABASE_URL is missing!"
    FAILURES=$((FAILURES + 1))
fi

if railway variables | grep -q "SUPABASE_SERVICE_KEY"; then
    echo -e "${GREEN}✓${NC} SUPABASE_SERVICE_KEY is set"
else
    echo -e "${RED}✗${NC} SUPABASE_SERVICE_KEY is missing!"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "📍 5. Testing direct worker authentication..."
RAILWAY_KEY=$(railway variables --json 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('RAILWAY_API_KEY', ''))" || echo "")

if [[ -z "$RAILWAY_KEY" ]]; then
    echo -e "${RED}✗${NC} Could not extract RAILWAY_API_KEY"
    FAILURES=$((FAILURES + 1))
else
    echo "   Testing with API key: ${RAILWAY_KEY:0:8}..."

    # Test with correct key
    RESPONSE=$(curl -s -X POST "https://tragaldabas-worker-production.up.railway.app/process/test-job-id" \
      -H "Authorization: Bearer $RAILWAY_KEY" \
      -w "\n%{http_code}" || echo "000")

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    if [[ "$HTTP_CODE" == "404" ]]; then
        echo -e "${GREEN}✓${NC} Authentication works (404 expected for test-job-id)"
    elif [[ "$HTTP_CODE" == "401" ]]; then
        echo -e "${RED}✗${NC} Authentication failed (401 Unauthorized)"
        echo "   Response: $BODY"
        FAILURES=$((FAILURES + 1))
    elif [[ "$HTTP_CODE" == "200" ]]; then
        echo -e "${GREEN}✓${NC} Authentication works (200 OK)"
    else
        echo -e "${YELLOW}⚠${NC}  Unexpected response code: $HTTP_CODE"
        echo "   Response: $BODY"
    fi
fi
echo ""

echo "📍 6. Checking Railway deployment logs..."
echo "   Recent logs:"
railway logs --tail 10 | grep -v "GET /health" | tail -5 | sed 's/^/   /'
echo ""

echo "📍 7. Checking for recent errors in Railway..."
ERROR_COUNT=$(railway logs --tail 100 | grep -i -E "(error|exception|failed|traceback)" | wc -l | tr -d ' ')
if [[ "$ERROR_COUNT" -eq 0 ]]; then
    echo -e "${GREEN}✓${NC} No recent errors in Railway logs"
else
    echo -e "${YELLOW}⚠${NC}  Found $ERROR_COUNT error lines in last 100 log lines"
    echo "   Recent errors:"
    railway logs --tail 100 | grep -i -E "(error|exception|failed)" | tail -3 | sed 's/^/   /'
fi
echo ""

echo "📍 8. Testing job status query..."
JOB_ID="bc79d695-2877-40d1-adc6-3caf92149198"
echo "   Checking job: $JOB_ID"

# Try to get job status via API
SUPABASE_URL="https://ncrgbzxypujhzhbhzvbv.supabase.co"
ANON_KEY=$(grep VITE_SUPABASE_ANON_KEY frontend/.env 2>/dev/null | cut -d= -f2 | tr -d "'" | tr -d '"' || echo "")

if [[ -n "$ANON_KEY" ]]; then
    JOB_STATUS=$(curl -s "$SUPABASE_URL/rest/v1/pipeline_jobs?id=eq.$JOB_ID&select=id,filename,status,stage,batch_id,app_generation" \
      -H "apikey: $ANON_KEY" \
      -H "Content-Type: application/json" || echo "[]")

    if [[ "$JOB_STATUS" != "[]" ]] && [[ "$JOB_STATUS" != "" ]]; then
        echo -e "${GREEN}✓${NC} Job query successful"
        echo "$JOB_STATUS" | python3 -m json.tool 2>/dev/null | sed 's/^/   /' || echo "   $JOB_STATUS"

        # Check for batch-aware status
        STATUS=$(echo "$JOB_STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0].get('status', '') if data else '')" 2>/dev/null || echo "")
        BATCH_ID=$(echo "$JOB_STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0].get('batch_id', '') if data else '')" 2>/dev/null || echo "")

        if [[ "$STATUS" == "ready_for_genesis" ]]; then
            echo ""
            echo -e "${YELLOW}⚠${NC}  Job is at 'ready_for_genesis' - waiting for batch promotion"
            if [[ -n "$BATCH_ID" ]] && [[ "$BATCH_ID" != "null" ]]; then
                echo "   Batch ID: $BATCH_ID"
                echo "   Checking batch status..."
                BATCH_STATUS=$(curl -s "$SUPABASE_URL/rest/v1/pipeline_jobs?batch_id=eq.$BATCH_ID&select=id,filename,status,app_generation" \
                  -H "apikey: $ANON_KEY" \
                  -H "Content-Type: application/json" 2>/dev/null || echo "[]")
                echo "$BATCH_STATUS" | python3 -m json.tool 2>/dev/null | sed 's/^/   /' || echo "   Failed to get batch status"

                # Count jobs in different states
                READY_COUNT=$(echo "$BATCH_STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation') and j.get('status') == 'ready_for_genesis'))" 2>/dev/null || echo "0")
                TOTAL_APP_COUNT=$(echo "$BATCH_STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for j in data if j.get('app_generation')))" 2>/dev/null || echo "0")

                echo ""
                echo "   📊 Batch status: $READY_COUNT/$TOTAL_APP_COUNT app_generation jobs ready"
                if [[ "$READY_COUNT" == "$TOTAL_APP_COUNT" ]] && [[ "$READY_COUNT" != "0" ]]; then
                    echo -e "   ${YELLOW}⚠${NC}  All jobs ready but not promoted - check Phase 6A.4C in SYSTEMATIC_DEBUGGING_PROTOCOL.md"
                else
                    echo "   ⏳ Waiting for other jobs to complete stage 7"
                fi
            fi
        fi
    else
        echo -e "${YELLOW}⚠${NC}  Could not retrieve job status"
    fi
else
    echo -e "${YELLOW}⚠${NC}  Could not find VITE_SUPABASE_ANON_KEY in frontend/.env"
fi
echo ""

echo "================================"
echo "📊 SUMMARY"
echo "================================"

if [[ $FAILURES -eq 0 ]]; then
    echo -e "${GREEN}✓ All quick checks passed!${NC}"
    echo ""
    echo "System appears healthy. If issue persists:"
    echo "1. Check SYSTEMATIC_DEBUGGING_PROTOCOL.md Phase 3: Genesis Trigger Analysis"
    echo "2. Monitor Railway logs in real-time: railway logs --tail 50"
    echo "3. Try direct worker call:"
    echo "   ./retry-jobs.sh"
else
    echo -e "${RED}✗ Found $FAILURES issues${NC}"
    echo ""
    echo "Fix the issues above, then:"
    echo "1. Commit and push any code changes"
    echo "2. Wait for Railway to redeploy (~2 min)"
    echo "3. Re-run this script"
fi
echo ""
echo "📖 For detailed debugging, see: SYSTEMATIC_DEBUGGING_PROTOCOL.md"
