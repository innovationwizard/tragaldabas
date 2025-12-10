# Supabase Integration - Industry Best Practices

Complete guide for integrating Tragaldabas with Supabase PostgreSQL.

## Table of Contents

1. [Setup & Configuration](#setup--configuration)
2. [Security Best Practices](#security-best-practices)
3. [Connection Management](#connection-management)
4. [Row Level Security (RLS)](#row-level-security-rls)
5. [Database Schema](#database-schema)
6. [Connection Pooling](#connection-pooling)
7. [Migrations](#migrations)
8. [Performance Optimization](#performance-optimization)
9. [Backup & Recovery](#backup--recovery)
10. [Monitoring & Observability](#monitoring--observability)
11. [Troubleshooting](#troubleshooting)

---

## Setup & Configuration

### 1. Get Supabase Connection String

From Supabase Dashboard:
1. Go to **Settings** → **Database**
2. Find **Connection string** section
3. Copy the **URI** connection string

### 2. Environment Configuration

**`.env` file:**
```env
# Supabase Database Connection
# Use the connection pooling URL for production (recommended)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?pgbouncer=true

# OR direct connection (for migrations/admin)
DATABASE_URL_DIRECT=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Supabase Project Settings
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # Keep secret!

# Connection Pool Settings
SUPABASE_POOL_SIZE=10
SUPABASE_MAX_OVERFLOW=20
SUPABASE_POOL_TIMEOUT=30
```

### 3. Connection String Formats

**Connection Pooling (Recommended for Production):**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?pgbouncer=true
```

**Direct Connection (For Migrations):**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

**Transaction Mode (For PgBouncer):**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true
```

---

## Security Best Practices

### 1. **Never Commit Secrets**

✅ **DO:**
```env
# .env (gitignored)
DATABASE_URL=postgresql://postgres:secret@...
SUPABASE_SERVICE_ROLE_KEY=secret-key
```

❌ **DON'T:**
```python
# Never hardcode in code
DATABASE_URL = "postgresql://postgres:password@..."
```

### 2. **Use Environment-Specific Keys**

- **Development:** Use `anon` key (limited permissions)
- **Production:** Use `service_role` key (full permissions) - **server-side only**
- **Client-side:** Never expose `service_role` key

### 3. **Connection String Security**

```python
# ✅ Good: Read from environment
from config import settings
db_url = settings.DATABASE_URL

# ❌ Bad: Hardcoded
db_url = "postgresql://user:pass@..."
```

### 4. **SSL/TLS Connection**

Supabase requires SSL. Ensure your connection includes SSL:

```python
# asyncpg automatically uses SSL for Supabase
# But you can explicitly set it:
DATABASE_URL=postgresql://...?sslmode=require
```

### 5. **IP Allowlisting**

In Supabase Dashboard:
- Go to **Settings** → **Database**
- Configure **Connection Pooling** → **IP Allowlist**
- Add your server IPs only

### 6. **Password Rotation**

- Rotate database passwords regularly
- Use Supabase Dashboard → **Settings** → **Database** → **Reset Database Password**
- Update `.env` immediately after rotation

---

## Connection Management

### 1. **Use Connection Pooling**

Supabase provides PgBouncer for connection pooling:

```python
# config.py
class Settings(BaseSettings):
    # Use pooling URL
    DATABASE_URL: str = "postgresql://...?pgbouncer=true"
    
    # Pool settings
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    DB_POOL_MAX_QUERIES: int = 50000
    DB_POOL_MAX_IDLE: float = 300.0  # 5 minutes
```

### 2. **Connection Lifecycle**

```python
# ✅ Good: Use context managers
async with db.get_connection() as conn:
    result = await conn.fetch("SELECT * FROM users")

# ❌ Bad: Don't forget to close
conn = await asyncpg.connect(url)
# Missing: await conn.close()
```

### 3. **Connection Timeouts**

```python
# Set appropriate timeouts
DATABASE_URL=postgresql://...?connect_timeout=10&command_timeout=30
```

### 4. **Handle Connection Errors**

```python
from core.exceptions import DatabaseError
import asyncpg

try:
    async with db.get_connection() as conn:
        await conn.fetch("SELECT 1")
except asyncpg.PostgresConnectionError:
    # Handle connection errors
    logger.error("Database connection failed")
    raise DatabaseError("Unable to connect to database")
except asyncpg.PostgresError as e:
    # Handle other PostgreSQL errors
    logger.error(f"Database error: {e}")
    raise DatabaseError(f"Database operation failed: {e}")
```

---

## Row Level Security (RLS)

### 1. **Enable RLS on Tables**

```sql
-- Enable RLS on users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Enable RLS on sessions table
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Enable RLS on password_reset_tokens table
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
```

### 2. **Create RLS Policies**

**Users Table:**
```sql
-- Users can only see their own data
CREATE POLICY "Users can view own data"
ON users FOR SELECT
USING (auth.uid() = id);

-- Users can update own data
CREATE POLICY "Users can update own data"
ON users FOR UPDATE
USING (auth.uid() = id);

-- Service role can do anything
CREATE POLICY "Service role full access"
ON users FOR ALL
USING (auth.role() = 'service_role');
```

**Sessions Table:**
```sql
-- Users can only see their own sessions
CREATE POLICY "Users can view own sessions"
ON sessions FOR SELECT
USING (auth.uid() = user_id);

-- Users can delete their own sessions
CREATE POLICY "Users can delete own sessions"
ON sessions FOR DELETE
USING (auth.uid() = user_id);
```

### 3. **Service Role Bypass**

For server-side operations, use service role:

```python
# Use service role for admin operations
SERVICE_DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[SERVICE-ROLE-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

---

## Database Schema

### 1. **Schema Organization**

```sql
-- Create schemas for organization
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS data;
CREATE SCHEMA IF NOT EXISTS analytics;
```

### 2. **Table Naming Conventions**

- Use `snake_case` for table names
- Prefix with schema: `auth.users`, `data.ingestions`
- Use singular nouns: `user`, not `users`

### 3. **Indexes for Performance**

```sql
-- Indexes for auth tables
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Partial index for active sessions
CREATE INDEX idx_sessions_active 
ON sessions(user_id, expires_at) 
WHERE revoked = FALSE AND expires_at > NOW();
```

### 4. **Foreign Key Constraints**

```sql
-- Add foreign keys with proper actions
ALTER TABLE sessions
ADD CONSTRAINT fk_sessions_user
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE CASCADE;

ALTER TABLE password_reset_tokens
ADD CONSTRAINT fk_reset_tokens_user
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE CASCADE;
```

---

## Connection Pooling

### 1. **PgBouncer Modes**

**Transaction Mode (Recommended):**
- Use port `6543` for transaction pooling
- Best for most applications
- Connection string: `?pgbouncer=true`

**Session Mode:**
- Use port `5432` for session pooling
- For migrations and admin tasks
- Direct connection

### 2. **Pool Configuration**

```python
# db/connection.py
import asyncpg

class DatabaseManager:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def create_pool(self):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=5,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300.0,
            timeout=10.0
        )
    
    async def get_connection(self):
        """Get connection from pool"""
        if not self.pool:
            await self.create_pool()
        return await self.pool.acquire()
    
    async def release_connection(self, conn):
        """Release connection back to pool"""
        await self.pool.release(conn)
```

### 3. **Pool Monitoring**

```python
# Monitor pool health
async def check_pool_health(self):
    if self.pool:
        size = self.pool.get_size()
        idle = self.pool.get_idle_size()
        print(f"Pool: {size} total, {idle} idle")
```

---

## Migrations

### 1. **Migration Strategy**

Use Supabase migrations or your own system:

```sql
-- migrations/001_initial_schema.sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    -- ... other columns
    created_at TIMESTAMP DEFAULT NOW()
);

-- migrations/002_add_indexes.sql
CREATE INDEX idx_users_email ON users(email);
```

### 2. **Version Control**

```sql
-- Add version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

### 3. **Rollback Strategy**

Always write reversible migrations:

```sql
-- Up migration
CREATE TABLE users (...);

-- Down migration (for rollback)
DROP TABLE IF EXISTS users;
```

---

## Performance Optimization

### 1. **Query Optimization**

```sql
-- ✅ Use EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';

-- ✅ Use prepared statements
PREPARE get_user AS SELECT * FROM users WHERE id = $1;

-- ✅ Use LIMIT for large datasets
SELECT * FROM sessions WHERE user_id = $1 LIMIT 100;
```

### 2. **Batch Operations**

```python
# ✅ Batch inserts
async with db.get_connection() as conn:
    await conn.executemany(
        "INSERT INTO users (email, username) VALUES ($1, $2)",
        [('user1@example.com', 'user1'), ('user2@example.com', 'user2')]
    )
```

### 3. **Connection Reuse**

```python
# ✅ Reuse connections within a request
async def process_request():
    async with db.get_connection() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        sessions = await conn.fetch("SELECT * FROM sessions WHERE user_id = $1", user_id)
        # Reuse same connection
```

### 4. **Index Usage**

- Index frequently queried columns
- Use composite indexes for multi-column queries
- Monitor index usage with `pg_stat_user_indexes`

---

## Backup & Recovery

### 1. **Supabase Automatic Backups**

- Supabase provides daily backups automatically
- Retention: 7 days (free), 30 days (pro)
- Access via Dashboard → **Database** → **Backups**

### 2. **Manual Backups**

```bash
# Using pg_dump
pg_dump "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" \
  > backup_$(date +%Y%m%d).sql

# Restore
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" \
  < backup_20240101.sql
```

### 3. **Point-in-Time Recovery**

- Available on Pro plan and above
- Restore to any point in last 7-30 days
- Via Supabase Dashboard

---

## Monitoring & Observability

### 1. **Supabase Dashboard Metrics**

Monitor in Dashboard:
- **Database** → **Usage**: Connection count, query performance
- **Database** → **Logs**: Query logs, errors
- **Database** → **Reports**: Slow queries, connection pool stats

### 2. **Application-Level Monitoring**

```python
import time
import logging

logger = logging.getLogger(__name__)

async def execute_with_monitoring(query, *args):
    start = time.time()
    try:
        result = await db.execute(query, *args)
        duration = time.time() - start
        logger.info(f"Query executed in {duration:.3f}s: {query[:50]}")
        return result
    except Exception as e:
        duration = time.time() - start
        logger.error(f"Query failed after {duration:.3f}s: {e}")
        raise
```

### 3. **Connection Pool Monitoring**

```python
# Monitor pool metrics
async def get_pool_stats():
    return {
        "size": pool.get_size(),
        "idle": pool.get_idle_size(),
        "active": pool.get_size() - pool.get_idle_size()
    }
```

### 4. **Slow Query Logging**

```sql
-- Enable slow query logging in Supabase
-- (Configured via Dashboard → Settings → Database)
```

---

## Troubleshooting

### 1. **Connection Issues**

**Problem:** "Connection refused" or "Timeout"

**Solutions:**
- Check IP allowlist in Supabase Dashboard
- Verify connection string format
- Check SSL mode: `?sslmode=require`
- Verify password is correct

### 2. **Pool Exhaustion**

**Problem:** "Too many connections"

**Solutions:**
- Reduce pool size
- Use connection pooling (PgBouncer)
- Close connections properly
- Check for connection leaks

### 3. **RLS Blocking Queries**

**Problem:** Queries return no rows despite data existing

**Solutions:**
- Check RLS policies
- Verify user context (`auth.uid()`)
- Use service role for admin operations
- Review policy conditions

### 4. **Performance Issues**

**Problem:** Slow queries

**Solutions:**
- Add indexes on frequently queried columns
- Use `EXPLAIN ANALYZE` to identify bottlenecks
- Optimize query patterns
- Consider materialized views for complex queries

---

## Quick Start Checklist

- [ ] Create Supabase project
- [ ] Get connection string from Dashboard
- [ ] Add to `.env` file (gitignored)
- [ ] Test connection: `python -c "from db import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('your-url').test_connection())"`
- [ ] Enable RLS on sensitive tables
- [ ] Create RLS policies
- [ ] Set up connection pooling
- [ ] Configure indexes
- [ ] Set up monitoring
- [ ] Test backup/restore process

---

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/current/admin.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Supabase Status Page](https://status.supabase.com/)

---

## Example Configuration

Complete `.env` example:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Server-side only!

# Database Connection (with pooling)
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true

# Direct connection for migrations
DATABASE_URL_DIRECT=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Connection Pool Settings
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_POOL_TIMEOUT=30
```

---

**Last Updated:** 2024-12-19
**Version:** 1.0

