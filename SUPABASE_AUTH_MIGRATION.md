# Migrating to Supabase Auth

## Why Switch?

**Current Custom Auth:**
- ✅ Full control
- ❌ More code to maintain
- ❌ Manual RLS setup
- ❌ No built-in OAuth
- ❌ No email verification
- ❌ Manual session management

**Supabase Auth:**
- ✅ Built-in RLS integration (`auth.uid()`)
- ✅ OAuth providers (Google, GitHub, etc.)
- ✅ Magic links, email verification
- ✅ MFA support
- ✅ Less code to maintain
- ✅ Better Supabase Storage integration
- ✅ Built-in user management UI

## Migration Plan

### Phase 1: Setup Supabase Auth

1. **Enable Auth in Supabase Dashboard:**
   - Go to Authentication → Settings
   - Enable Email provider
   - Configure email templates (optional)

2. **Add Environment Variables:**
   ```env
   SUPABASE_URL=https://[PROJECT-REF].supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   ```

3. **Install Supabase Client:**
   ```bash
   pip install supabase
   ```

### Phase 2: Update Backend API

Replace custom auth with Supabase Auth:

```python
# web/api_supabase.py (new file)
from supabase import create_client, Client
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current user from Supabase Auth"""
    token = credentials.credentials
    
    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token)
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Phase 3: Update Frontend

Replace custom auth with Supabase JS client:

```javascript
// frontend/src/lib/supabase.js
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### Phase 4: Migrate Existing Users (if any)

If you have existing users in your custom `users` table:

```sql
-- Migration script to move users to Supabase Auth
-- Note: This is a one-time migration
```

## Quick Start: Supabase Auth Integration

### Backend Changes

1. **Replace auth endpoints:**
   - Use Supabase Auth API instead of custom JWT
   - Remove custom auth service dependencies

2. **Update RLS policies:**
   ```sql
   -- Now you can use auth.uid()!
   CREATE POLICY "Users can view own data"
   ON users FOR SELECT
   USING (auth.uid() = id);
   ```

### Frontend Changes

1. **Replace AuthContext:**
   ```javascript
   import { supabase } from './lib/supabase'
   
   // Login
   const { data, error } = await supabase.auth.signInWithPassword({
     email,
     password
   })
   
   // Register
   const { data, error } = await supabase.auth.signUp({
     email,
     password
   })
   
   // Get current user
   const { data: { user } } = await supabase.auth.getUser()
   ```

## Benefits After Migration

1. **Simplified RLS:**
   ```sql
   -- Before (custom JWT):
   CREATE POLICY "Users can view own data"
   ON users FOR SELECT
   USING (id = get_current_user_id()); -- Custom function needed
   
   -- After (Supabase Auth):
   CREATE POLICY "Users can view own data"
   ON users FOR SELECT
   USING (auth.uid() = id); -- Built-in!
   ```

2. **OAuth Out of the Box:**
   ```javascript
   // Google login - just works!
   await supabase.auth.signInWithOAuth({
     provider: 'google'
   })
   ```

3. **Email Verification:**
   - Automatic email verification
   - Magic links
   - Password reset emails

4. **Less Code:**
   - Remove: `auth/service.py`, `auth/jwt.py`, `auth/password.py`
   - Keep: Only business logic

## Migration Checklist

- [ ] Enable Supabase Auth in dashboard
- [ ] Add Supabase environment variables
- [ ] Install `supabase` Python package
- [ ] Install `@supabase/supabase-js` in frontend
- [ ] Update backend API endpoints
- [ ] Update frontend AuthContext
- [ ] Update RLS policies to use `auth.uid()`
- [ ] Migrate existing users (if any)
- [ ] Test authentication flow
- [ ] Remove custom auth code (after verification)

## Next Steps

Would you like me to:
1. Create the Supabase Auth integration code?
2. Update the API endpoints?
3. Update the frontend AuthContext?
4. Create migration scripts for existing users?

