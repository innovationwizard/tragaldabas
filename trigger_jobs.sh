#!/bin/bash
# Trigger processing for all pending jobs in local development

echo "🔍 Finding pending jobs..."

# Get pending jobs from database
JOBS=$(psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -t -c "SELECT id FROM pipeline_jobs WHERE status = 'pending';")

if [ -z "$JOBS" ]; then
    echo "✅ No pending jobs found"
    exit 0
fi

echo "📋 Found pending jobs:"
echo "$JOBS"
echo ""

# Process each job
for JOB_ID in $JOBS; do
    # Remove whitespace
    JOB_ID=$(echo $JOB_ID | tr -d '[:space:]')

    echo "🚀 Processing job: $JOB_ID"

    # Call the process endpoint
    curl -X POST "http://localhost:8000/api/pipeline/process/$JOB_ID" \
        -H "Content-Type: application/json" \
        2>&1 | head -3

    echo ""
    echo "✅ Triggered job: $JOB_ID"
    echo ""
done

echo "✅ All jobs triggered!"
echo "📊 Check the backend logs to see processing status"
