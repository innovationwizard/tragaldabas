"""Authentication models"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(BaseModel):
    """User model"""
    id: Optional[int] = None
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password_hash: str  # Never expose this in API responses
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    email_verified: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    password_changed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model (no password hash)"""
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12)  # Enforce strong passwords
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str
    remember_me: bool = False


class Session(BaseModel):
    """User session model"""
    id: Optional[int] = None
    user_id: int
    token: str  # JWT token
    refresh_token: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    refresh_expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)


class PasswordResetToken(BaseModel):
    """Password reset token model"""
    id: Optional[int] = None
    user_id: int
    token: str  # Secure random token
    expires_at: datetime
    used: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Password reset submission"""
    token: str
    new_password: str = Field(min_length=12)


class PasswordChange(BaseModel):
    """Password change (for authenticated users)"""
    current_password: str
    new_password: str = Field(min_length=12)

