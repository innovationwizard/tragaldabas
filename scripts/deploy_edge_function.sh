#!/bin/bash
# Script to deploy Supabase Edge Function for pipeline processing

set -e

echo "🚀 Deploying Supabase Edge Function: process-pipeline"
echo ""

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Installing..."
    brew install supabase/tap/supabase
fi

# Check if logged in
if ! supabase projects list &> /dev/null; then
    echo "⚠️  Not logged in to Supabase. Please run:"
    echo "   supabase login"
    echo ""
    echo "Or set SUPABASE_ACCESS_TOKEN environment variable:"
    echo "   export SUPABASE_ACCESS_TOKEN=your_access_token"
    echo ""
    exit 1
fi

# Get project ref from .env if available
if [ -f .env ]; then
    SUPABASE_URL=$(grep SUPABASE_URL .env | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    if [ ! -z "$SUPABASE_URL" ]; then
        PROJECT_REF=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co.*||')
        echo "📋 Found project ref: $PROJECT_REF"
    fi
fi

# Link project if project ref is available
if [ ! -z "$PROJECT_REF" ]; then
    echo "🔗 Linking to project: $PROJECT_REF"
    supabase link --project-ref "$PROJECT_REF" --password "$(grep DATABASE_URL .env | head -1 | cut -d'@' -f1 | cut -d':' -f3 | tr -d '/')" 2>/dev/null || echo "⚠️  Could not auto-link. Please link manually: supabase link --project-ref $PROJECT_REF"
fi

# Deploy the function
echo ""
echo "📦 Deploying Edge Function..."
supabase functions deploy process-pipeline --no-verify-jwt

echo ""
echo "✅ Edge Function deployed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Set environment variables in Supabase Dashboard:"
echo "   - Go to: Edge Functions → process-pipeline → Settings"
echo "   - Add: VERCEL_API_URL=https://tragaldabas.vercel.app"
echo "   - Add: SUPABASE_URL=$SUPABASE_URL"
echo "   - Add: SUPABASE_SERVICE_ROLE_KEY=(your service role key)"
echo ""
echo "2. Test the function:"
echo "   curl -X POST https://$PROJECT_REF.supabase.co/functions/v1/process-pipeline \\"
echo "     -H 'Authorization: Bearer YOUR_ANON_KEY' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"job_id\": \"your-job-id\"}'"
echo ""

