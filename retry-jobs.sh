#!/bin/bash

# Job IDs from the database
JOB_1="bc79d695-2877-40d1-adc6-3caf92149198"
JOB_2="680e7e08-a9a6-4492-af98-b9db2712d822"

# Supabase configuration
SUPABASE_URL="https://ncrgbzxypujhzhbhzvbv.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jcmdienh5cHVqaHpoYmh6dmJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUzOTE2MzMsImV4cCI6MjA4MDk2NzYzM30.cBP3m2DYy0URSj3ikM1wnZJ3IQO6upqO-tNE7qbf0cE"

echo "======================================"
echo "Retrying stuck genesis jobs"
echo "======================================"
echo ""

# Retry Job 1: Comisiones.xlsx
echo "1. Triggering Comisiones.xlsx (Job ID: $JOB_1)"
curl -X POST "${SUPABASE_URL}/functions/v1/process-pipeline" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"${JOB_1}\"}"
echo ""
echo ""

# Wait a moment between requests
sleep 2

# Retry Job 2: Reservas.xlsx
echo "2. Triggering Reservas.xlsx (Job ID: $JOB_2)"
curl -X POST "${SUPABASE_URL}/functions/v1/process-pipeline" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": \"${JOB_2}\"}"
echo ""
echo ""

echo "======================================"
echo "Done! Jobs have been triggered."
echo "Check your dashboard to monitor progress."
echo "======================================"
