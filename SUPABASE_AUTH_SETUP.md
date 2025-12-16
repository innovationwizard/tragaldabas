# Supabase Auth Setup Guide

## Quick Comparison

| Feature | Custom Auth | Supabase Auth |
|---------|------------|---------------|
| Code to maintain | ~500 lines | ~50 lines |
| RLS integration | Custom function | Built-in `auth.uid()` |
| OAuth providers | Manual | Built-in (Google, GitHub, etc.) |
| Email verification | Manual | Built-in |
| Magic links | No | Yes |
| MFA | No | Yes |
| Storage integration | Manual | Built-in |

## Setup Steps

### 1. Enable Supabase Auth

In Supabase Dashboard:
- Go to **Authentication** → **Settings**
- Enable **Email** provider
- Configure email templates (optional)

### 2. Get API Keys

From Supabase Dashboard → **Settings** → **API**:
- Copy **Project URL** → `SUPABASE_URL`
- Copy **anon public** key → `SUPABASE_ANON_KEY`
- Copy **service_role** key → `SUPABASE_SERVICE_ROLE_KEY` (keep secret!)

### 3. Environment Variables

**Backend (.env):**
```env
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Server-side only!
DATABASE_URL=postgresql://...  # Still needed for data
```

**Frontend (.env.local):**
```env
VITE_SUPABASE_URL=https://[PROJECT-REF].supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGc...  # Safe for client-side
```

### 4. Install Dependencies

**Backend:**
```bash
pip install supabase
```

**Frontend:**
```bash
cd frontend
npm install @supabase/supabase-js
```

### 5. Update Code

**Backend:**
- Use `web/api_supabase_auth.py` instead of `web/api.py`
- Or update `web/api.py` to use Supabase Auth

**Frontend:**
- Replace `AuthContext.jsx` with `AuthContextSupabase.jsx`
- Update `App.jsx` to use new context

### 6. Setup RLS

Run the simplified RLS script:
```bash
# In Supabase SQL Editor
# Copy and paste: scripts/setup_rls_supabase_auth.sql
```

Much simpler! Uses `auth.uid()` instead of custom functions.

## Migration Path

### Option A: Gradual Migration (Recommended)

1. Keep custom auth working
2. Add Supabase Auth alongside
3. Migrate users gradually
4. Switch endpoints one by one
5. Remove custom auth when done

### Option B: Clean Cutover

1. Set up Supabase Auth
2. Migrate all users at once
3. Switch all endpoints
4. Remove custom auth code

## Benefits You'll Get

1. **Simpler RLS:**
   ```sql
   -- Before: Custom function needed
   USING (id = get_current_user_id())
   
   -- After: Built-in!
   USING (auth.uid() = id)
   ```

2. **OAuth Out of the Box:**
   ```javascript
   // Google login - just works!
   await supabase.auth.signInWithOAuth({ provider: 'google' })
   ```

3. **Email Verification:**
   - Automatic email verification
   - Magic links
   - Password reset emails

4. **Less Code:**
   - Remove ~500 lines of auth code
   - Focus on business logic

5. **Better Storage Integration:**
   ```javascript
   // Upload to Supabase Storage with automatic auth
   await supabase.storage
     .from('outputs')
     .upload(`${jobId}/file.pptx`, file)
   ```

## Files Created

- `web/api_supabase_auth.py` - API with Supabase Auth
- `frontend/src/lib/supabase.js` - Supabase client
- `frontend/src/contexts/AuthContextSupabase.jsx` - Auth context
- `scripts/setup_rls_supabase_auth.sql` - Simplified RLS setup
- `SUPABASE_AUTH_MIGRATION.md` - Migration guide

## Next Steps

1. Review the migration guide
2. Test Supabase Auth locally
3. Migrate users (if any)
4. Update production
5. Remove custom auth code

Would you like me to:
- ✅ Create the full migration?
- ✅ Update all endpoints?
- ✅ Create user migration script?

