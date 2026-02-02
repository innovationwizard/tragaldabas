# Vercel Environment Variables

## Required Environment Variables

### Minimum Required (for basic functionality)

At least **ONE** LLM API key is required:

```env
# Choose at least one:
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-...
# OR
GOOGLE_API_KEY=AIzaSy...
```

### Authentication (Required for Production)

**Supabase Auth (Recommended):**
```env
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=eyJhbGc...  # From Supabase Dashboard → Settings → API
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Server-side only! Keep secret.
```

**Note:** The application now uses Supabase Auth. The old `JWT_SECRET_KEY` is no longer needed.

## Recommended Environment Variables

### Supabase Auth (Recommended - Better than Custom JWT)

**Required for Supabase Auth:**
```env
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=eyJhbGc...  # From Supabase Dashboard → Settings → API
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Server-side only! Keep secret.
```

**Benefits:**
- Built-in RLS with `auth.uid()` (much simpler!)
- OAuth providers (Google, GitHub, etc.)
- Email verification, magic links
- MFA support
- Less code to maintain (~500 lines → ~50 lines)

**Note:** If using Supabase Auth, you don't need `JWT_SECRET_KEY` - Supabase handles tokens.

### Database (Required)

**Supabase PostgreSQL** connection:

```env
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require
```

**Note:** Supabase Storage can be used for output files (PPTX, TXT, etc.) instead of local filesystem.

### LLM Configuration (Optional)

```env
# Provider priority (comma-separated)
LLM_PROVIDER_PRIORITY=anthropic,openai,gemini

# Model selection (optional, uses defaults if not set)
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o
GEMINI_MODEL_ID=gemini-1.5-pro
GEMINI_FALLBACK_MODEL_ID=gemini-2.5-flash
```

### Output Directory / Storage

**Option 1: Supabase Storage (Recommended for Vercel)**

Since you're using Supabase, use Supabase Storage for output files:

```env
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=outputs  # Create this bucket in Supabase Dashboard
```

**Option 2: Local Filesystem (Not recommended for Vercel)**

For Vercel, `/tmp` is ephemeral and files are lost when function terminates:

```env
OUTPUT_DIR=/tmp/output
```

⚠️ **Recommendation:** Use Supabase Storage for persistent file storage. Files will persist across deployments and function invocations.

### Frontend Configuration (Optional)

For OpenGraph tags and absolute URLs:

```env
VITE_BASE_URL=https://your-domain.vercel.app
```

### CORS Configuration (Optional)

If your frontend is on a different domain:

```env
CORS_ORIGINS=https://your-domain.vercel.app,https://www.your-domain.com
```

**Default:** `http://localhost:5173,http://localhost:3000` (for local development)

## Complete Example for Vercel

### Option 1: With Supabase Auth (Recommended)

```env
# Required: At least one LLM API key
ANTHROPIC_API_KEY=sk-ant-api03-...

# Required: Supabase Auth
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Server-side only!

# Required: Supabase Database
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require

# Recommended: Supabase Storage (for output files)
SUPABASE_STORAGE_BUCKET=outputs

# Optional: Frontend base URL (for OpenGraph)
VITE_BASE_URL=https://tragaldabas.vercel.app

# Optional: LLM configuration
LLM_PROVIDER_PRIORITY=anthropic,openai,gemini
```

**Note:** With Supabase Auth, you don't need `JWT_SECRET_KEY` - Supabase handles tokens automatically.

### Option 2: Custom Auth (Legacy)

```env
# Required: At least one LLM API key
ANTHROPIC_API_KEY=sk-ant-api03-...

# Required: JWT secret (generate securely)
JWT_SECRET_KEY=your-generated-secret-key-here

# Required: Database
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require

# Optional: Output directory (use /tmp for Vercel or Supabase Storage)
OUTPUT_DIR=/tmp/output
# OR
SUPABASE_STORAGE_BUCKET=outputs

# Optional: Frontend base URL
VITE_BASE_URL=https://tragaldabas.vercel.app
```

## How to Set in Vercel

### Via Vercel Dashboard

1. Go to your project in Vercel
2. Navigate to **Settings** → **Environment Variables**
3. Add each variable:
   - **Key:** `ANTHROPIC_API_KEY`
   - **Value:** Your API key
   - **Environment:** Select `Production`, `Preview`, and/or `Development`
4. Click **Save**
5. Redeploy for changes to take effect

### Via Vercel CLI

```bash
vercel env add ANTHROPIC_API_KEY
vercel env add JWT_SECRET_KEY
vercel env add DATABASE_URL
# etc.
```

### Via `.env` file (for local development)

Create `.env.local` (gitignored) for local testing:

```bash
cp .env.example .env.local
# Edit .env.local with your values
```

## Security Best Practices

1. **Never commit secrets** - Use Vercel's environment variables
2. **Use different keys** for production/preview/development
3. **Rotate secrets** periodically
4. **Use Vercel's secret management** - Don't hardcode values
5. **Restrict access** - Only add variables to environments that need them

## Verification

After setting environment variables, verify they're loaded:

1. Check Vercel deployment logs
2. Test an API endpoint that requires the variables
3. Use Vercel's function logs to debug

## Troubleshooting

### Variables not loading?

1. **Redeploy** after adding variables
2. Check **Environment** selection (Production/Preview/Development)
3. Verify **variable names** match exactly (case-sensitive)
4. Check **Vercel logs** for errors

### JWT tokens invalid after deploy?

- Set `JWT_SECRET_KEY` to a fixed value (not auto-generated)
- Ensure it's set in all environments (Production, Preview, Development)

### File uploads not persisting?

- Vercel's `/tmp` is ephemeral
- Use external storage (S3, Cloud Storage) or database
- Consider deploying backend separately (Railway)

## Quick Setup Checklist

- [ ] At least one LLM API key set (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GOOGLE_API_KEY`)
- [ ] `JWT_SECRET_KEY` set (generate securely)
- [ ] `DATABASE_URL` set to Supabase PostgreSQL connection string
- [ ] Supabase Storage configured (create `outputs` bucket in Supabase Dashboard)
- [ ] `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set (for Storage access)
- [ ] `VITE_BASE_URL` set to your Vercel domain (for OpenGraph)
- [ ] Variables added to correct environments (Production/Preview/Development)
- [ ] Redeployed after adding variables

## Supabase Storage Setup

1. **Create Storage Bucket:**
   - Go to Supabase Dashboard → Storage
   - Create bucket named `outputs`
   - Set to **Public** (or configure RLS policies)

2. **Get Service Role Key:**
   - Go to Supabase Dashboard → Settings → API
   - Copy **service_role** key (not anon key)
   - This has full access to Storage

3. **Set Environment Variables:**
   ```env
   SUPABASE_URL=https://[PROJECT-REF].supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
   SUPABASE_STORAGE_BUCKET=outputs
   ```

