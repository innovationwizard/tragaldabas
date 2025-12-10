"""Authentication database operations"""

from typing import Optional
from datetime import datetime

from .models import User, Session, PasswordResetToken, UserStatus
from db import DatabaseManager
from core.exceptions import DatabaseError


class AuthDatabase:
    """Database operations for authentication"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._ensure_tables()
    
    async def _ensure_tables(self):
        """Ensure authentication tables exist"""
        # Create users table
        await self.db.execute_write("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(20) DEFAULT 'user',
                status VARCHAR(20) DEFAULT 'pending_verification',
                email_verified BOOLEAN DEFAULT FALSE,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_changed_at TIMESTAMP
            );
        """)
        
        # Create sessions table
        await self.db.execute_write("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                device_info VARCHAR(255),
                ip_address VARCHAR(45),
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                refresh_expires_at TIMESTAMP NOT NULL,
                revoked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create password reset tokens table
        await self.db.execute_write("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes
        await self.db.execute_write("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_user_id ON password_reset_tokens(user_id);
        """)
    
    async def create_user(self, user: User) -> User:
        """Create a new user"""
        query = """
            INSERT INTO users (email, username, password_hash, full_name, role, status, 
                             email_verified, password_changed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, created_at, updated_at
        """
        
        result = await self.db.execute_one(
            query,
            user.email,
            user.username,
            user.password_hash,
            user.full_name,
            user.role.value,
            user.status.value,
            user.email_verified,
            user.password_changed_at
        )
        
        if result:
            user.id = result[0] if isinstance(result, tuple) else result['id']
            user.created_at = result[2] if isinstance(result, tuple) else result['created_at']
            user.updated_at = result[3] if isinstance(result, tuple) else result['updated_at']
        
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = $1"
        result = await self.db.execute_one(query, user_id)
        
        if not result:
            return None
        
        return self._row_to_user(result)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = $1"
        result = await self.db.execute_one(query, email)
        
        if not result:
            return None
        
        return self._row_to_user(result)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = $1"
        result = await self.db.execute_one(query, username)
        
        if not result:
            return None
        
        return self._row_to_user(result)
    
    async def update_user(self, user: User) -> User:
        """Update user"""
        query = """
            UPDATE users SET
                email = $2, username = $3, password_hash = $4, full_name = $5,
                role = $6, status = $7, email_verified = $8,
                failed_login_attempts = $9, locked_until = $10, last_login = $11,
                updated_at = CURRENT_TIMESTAMP, password_changed_at = $12
            WHERE id = $1
            RETURNING updated_at
        """
        
        result = await self.db.execute_one(
            query,
            user.id,
            user.email,
            user.username,
            user.password_hash,
            user.full_name,
            user.role.value,
            user.status.value,
            user.email_verified,
            user.failed_login_attempts,
            user.locked_until,
            user.last_login,
            user.password_changed_at
        )
        
        if result:
            user.updated_at = result['updated_at']
        
        return user
    
    async def create_session(self, session: Session) -> Session:
        """Create a new session"""
        query = """
            INSERT INTO sessions (user_id, token, refresh_token, device_info, ip_address,
                                user_agent, expires_at, refresh_expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, created_at, last_used_at
        """
        
        result = await self.db.execute_one(
            query,
            session.user_id,
            session.token,
            session.refresh_token,
            session.device_info,
            session.ip_address,
            session.user_agent,
            session.expires_at,
            session.refresh_expires_at
        )
        
        if result:
            session.id = result['id']
            session.created_at = result['created_at']
            session.last_used_at = result['last_used_at']
        
        return session
    
    async def get_session_by_token(self, token: str) -> Optional[Session]:
        """Get session by token"""
        query = "SELECT * FROM sessions WHERE token = $1 AND revoked = FALSE"
        result = await self.db.execute_one(query, token)
        
        if not result:
            return None
        
        return self._row_to_session(result)
    
    async def update_session(self, session: Session) -> Session:
        """Update session"""
        query = """
            UPDATE sessions SET
                revoked = $2, last_used_at = $3
            WHERE id = $1
        """
        
        await self.db.execute_write(
            query,
            session.id,
            session.revoked,
            session.last_used_at
        )
        
        return session
    
    async def revoke_all_user_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user"""
        query = """
            UPDATE sessions SET revoked = TRUE
            WHERE user_id = $1 AND revoked = FALSE
        """
        
        await self.db.execute_write(query, user_id)
        
        # Get count (would need a separate query in real implementation)
        return 0
    
    async def create_password_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        """Create password reset token"""
        query = """
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES ($1, $2, $3)
            RETURNING id, created_at
        """
        
        result = await self.db.execute_one(
            query,
            token.user_id,
            token.token,
            token.expires_at
        )
        
        if result:
            token.id = result['id']
            token.created_at = result['created_at']
        
        return token
    
    async def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """Get password reset token"""
        query = "SELECT * FROM password_reset_tokens WHERE token = $1"
        result = await self.db.execute_one(query, token)
        
        if not result:
            return None
        
        return self._row_to_reset_token(result)
    
    async def update_password_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        """Update password reset token"""
        query = "UPDATE password_reset_tokens SET used = $2 WHERE id = $1"
        await self.db.execute_write(query, token.id, token.used)
        return token
    
    def _row_to_user(self, row) -> User:
        """Convert database row to User model"""
        from .models import UserRole, UserStatus
        
        # Handle both dict and tuple/Record formats
        if isinstance(row, dict):
            get_val = lambda key: row.get(key)
        else:
            # Assume Record type with attribute access
            get_val = lambda key: getattr(row, key, None)
        
        return User(
            id=get_val('id'),
            email=get_val('email'),
            username=get_val('username'),
            password_hash=get_val('password_hash'),
            full_name=get_val('full_name'),
            role=UserRole(get_val('role') or 'user'),
            status=UserStatus(get_val('status') or 'pending_verification'),
            email_verified=get_val('email_verified') or False,
            failed_login_attempts=get_val('failed_login_attempts') or 0,
            locked_until=get_val('locked_until'),
            last_login=get_val('last_login'),
            created_at=get_val('created_at') or datetime.utcnow(),
            updated_at=get_val('updated_at') or datetime.utcnow(),
            password_changed_at=get_val('password_changed_at')
        )
    
    def _row_to_session(self, row) -> Session:
        """Convert database row to Session model"""
        if isinstance(row, dict):
            get_val = lambda key: row.get(key)
        else:
            get_val = lambda key: getattr(row, key, None)
        
        return Session(
            id=get_val('id'),
            user_id=get_val('user_id'),
            token=get_val('token'),
            refresh_token=get_val('refresh_token'),
            device_info=get_val('device_info'),
            ip_address=get_val('ip_address'),
            user_agent=get_val('user_agent'),
            expires_at=get_val('expires_at'),
            refresh_expires_at=get_val('refresh_expires_at'),
            revoked=get_val('revoked') or False,
            created_at=get_val('created_at') or datetime.utcnow(),
            last_used_at=get_val('last_used_at') or datetime.utcnow()
        )
    
    def _row_to_reset_token(self, row) -> PasswordResetToken:
        """Convert database row to PasswordResetToken model"""
        if isinstance(row, dict):
            get_val = lambda key: row.get(key)
        else:
            get_val = lambda key: getattr(row, key, None)
        
        return PasswordResetToken(
            id=get_val('id'),
            user_id=get_val('user_id'),
            token=get_val('token'),
            expires_at=get_val('expires_at'),
            used=get_val('used') or False,
            created_at=get_val('created_at') or datetime.utcnow()
        )

