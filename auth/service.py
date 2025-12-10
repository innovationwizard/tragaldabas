"""Authentication service"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.exceptions import TragaldabasError
from .models import (
    User, UserCreate, UserLogin, Session, PasswordResetToken,
    PasswordResetRequest, PasswordReset, PasswordChange, UserStatus
)
from .password import PasswordHasher, validate_password_strength, generate_secure_token
from .jwt import JWTManager, JWTError
from .database import AuthDatabase
from config import settings


class AuthError(TragaldabasError):
    """Authentication error"""
    pass


class AuthService:
    """Authentication service with industry best practices"""
    
    def __init__(
        self,
        db: AuthDatabase,
        jwt_manager: JWTManager,
        password_hasher: PasswordHasher
    ):
        self.db = db
        self.jwt = jwt_manager
        self.password_hasher = password_hasher
        
        # Security settings
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.password_reset_token_expiry = timedelta(hours=1)
    
    async def register(self, user_data: UserCreate) -> User:
        """
        Register a new user
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user (without password hash)
            
        Raises:
            AuthError: If registration fails
        """
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise AuthError(f"Password validation failed: {error_msg}")
        
        # Check if user exists
        existing = await self.db.get_user_by_email(user_data.email)
        if existing:
            raise AuthError("User with this email already exists")
        
        existing = await self.db.get_user_by_username(user_data.username)
        if existing:
            raise AuthError("User with this username already exists")
        
        # Hash password
        password_hash = self.password_hasher.hash(user_data.password)
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            full_name=user_data.full_name,
            role=user_data.role,
            status=UserStatus.PENDING_VERIFICATION,
            password_changed_at=datetime.utcnow()
        )
        
        created_user = await self.db.create_user(user)
        
        # Send verification email (would be implemented)
        # await self._send_verification_email(created_user)
        
        return created_user
    
    async def login(
        self,
        login_data: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> Tuple[Session, User]:
        """
        Authenticate user and create session
        
        Args:
            login_data: Login credentials
            ip_address: Client IP address
            user_agent: User agent string
            device_info: Device information
            
        Returns:
            Tuple of (session, user)
            
        Raises:
            AuthError: If login fails
        """
        # Get user
        user = await self.db.get_user_by_email(login_data.email)
        if not user:
            # Don't reveal if user exists (security best practice)
            raise AuthError("Invalid email or password")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
            raise AuthError(f"Account is locked. Try again in {remaining:.0f} minutes")
        
        # Check account status
        if user.status != UserStatus.ACTIVE:
            raise AuthError("Account is not active. Please verify your email or contact support")
        
        # Verify password
        if not self.password_hasher.verify(login_data.password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account after max attempts
            if user.failed_login_attempts >= self.max_login_attempts:
                user.locked_until = datetime.utcnow() + self.lockout_duration
                user.failed_login_attempts = 0
                await self.db.update_user(user)
                raise AuthError(
                    f"Too many failed login attempts. Account locked for "
                    f"{self.lockout_duration.total_seconds() / 60:.0f} minutes"
                )
            
            await self.db.update_user(user)
            raise AuthError("Invalid email or password")
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        await self.db.update_user(user)
        
        # Generate tokens
        access_token = self.jwt.generate_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        
        refresh_token = self.jwt.generate_refresh_token(user_id=user.id)
        
        # Create session
        session = Session(
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + self.jwt.access_token_expiry,
            refresh_expires_at=datetime.utcnow() + self.jwt.refresh_token_expiry
        )
        
        created_session = await self.db.create_session(session)
        
        return created_session, user
    
    async def logout(self, token: str) -> bool:
        """
        Logout user by revoking session
        
        Args:
            token: Access token to revoke
            
        Returns:
            True if logout successful
        """
        try:
            payload = self.jwt.verify_token(token, token_type="access")
            session = await self.db.get_session_by_token(token)
            
            if session:
                session.revoked = True
                await self.db.update_session(session)
            
            return True
        except JWTError:
            return False
    
    async def logout_all_sessions(self, user_id: int) -> int:
        """
        Revoke all sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions revoked
        """
        return await self.db.revoke_all_user_sessions(user_id)
    
    async def request_password_reset(self, request: PasswordResetRequest) -> bool:
        """
        Request password reset
        
        Args:
            request: Password reset request
            
        Returns:
            True if request processed (always returns True for security)
        """
        user = await self.db.get_user_by_email(request.email)
        
        # Always return True (don't reveal if user exists)
        if not user:
            return True
        
        # Generate reset token
        token = generate_secure_token(32)
        expires_at = datetime.utcnow() + self.password_reset_token_expiry
        
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )
        
        await self.db.create_password_reset_token(reset_token)
        
        # Send reset email (would be implemented)
        # await self._send_password_reset_email(user, token)
        
        return True
    
    async def reset_password(self, reset_data: PasswordReset) -> bool:
        """
        Reset password using token
        
        Args:
            reset_data: Password reset data
            
        Returns:
            True if password reset successful
            
        Raises:
            AuthError: If reset fails
        """
        # Get reset token
        reset_token = await self.db.get_password_reset_token(reset_data.token)
        
        if not reset_token:
            raise AuthError("Invalid or expired reset token")
        
        if reset_token.used:
            raise AuthError("Reset token has already been used")
        
        if reset_token.expires_at < datetime.utcnow():
            raise AuthError("Reset token has expired")
        
        # Get user
        user = await self.db.get_user_by_id(reset_token.user_id)
        if not user:
            raise AuthError("User not found")
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(reset_data.new_password)
        if not is_valid:
            raise AuthError(f"Password validation failed: {error_msg}")
        
        # Hash new password
        user.password_hash = self.password_hasher.hash(reset_data.new_password)
        user.password_changed_at = datetime.utcnow()
        user.failed_login_attempts = 0  # Reset failed attempts
        user.locked_until = None
        
        await self.db.update_user(user)
        
        # Mark token as used
        reset_token.used = True
        await self.db.update_password_reset_token(reset_token)
        
        # Revoke all existing sessions (security best practice)
        await self.db.revoke_all_user_sessions(user.id)
        
        return True
    
    async def change_password(
        self,
        user_id: int,
        change_data: PasswordChange
    ) -> bool:
        """
        Change password for authenticated user
        
        Args:
            user_id: User ID
            change_data: Password change data
            
        Returns:
            True if password changed successfully
            
        Raises:
            AuthError: If change fails
        """
        user = await self.db.get_user_by_id(user_id)
        if not user:
            raise AuthError("User not found")
        
        # Verify current password
        if not self.password_hasher.verify(change_data.current_password, user.password_hash):
            raise AuthError("Current password is incorrect")
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(change_data.new_password)
        if not is_valid:
            raise AuthError(f"Password validation failed: {error_msg}")
        
        # Check if new password is same as current
        if self.password_hasher.verify(change_data.new_password, user.password_hash):
            raise AuthError("New password must be different from current password")
        
        # Hash new password
        user.password_hash = self.password_hasher.hash(change_data.new_password)
        user.password_changed_at = datetime.utcnow()
        
        await self.db.update_user(user)
        
        # Revoke all sessions except current (optional, for security)
        # await self.db.revoke_all_user_sessions(user_id)
        
        return True
    
    async def verify_token(self, token: str) -> Optional[User]:
        """
        Verify access token and return user
        
        Args:
            token: Access token
            
        Returns:
            User if token is valid, None otherwise
        """
        try:
            payload = self.jwt.verify_token(token, token_type="access")
            user_id = payload["user_id"]
            
            # Check if session is revoked
            session = await self.db.get_session_by_token(token)
            if not session or session.revoked:
                return None
            
            # Update last used
            session.last_used_at = datetime.utcnow()
            await self.db.update_session(session)
            
            # Get user
            user = await self.db.get_user_by_id(user_id)
            if not user or user.status != UserStatus.ACTIVE:
                return None
            
            return user
            
        except JWTError:
            return None

