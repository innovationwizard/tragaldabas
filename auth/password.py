"""Password hashing and validation utilities"""

import secrets
import hashlib
from typing import Tuple

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    from argon2 import PasswordHasher as Argon2Hasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    Argon2Hasher = None


class PasswordHasher:
    """Password hashing with multiple algorithm support"""
    
    def __init__(self, algorithm: str = "auto"):
        """
        Initialize password hasher
        
        Args:
            algorithm: "bcrypt", "argon2", or "auto" (prefers argon2)
        """
        self.algorithm = algorithm
        
        if algorithm == "auto":
            if ARGON2_AVAILABLE:
                self.algorithm = "argon2"
            elif BCRYPT_AVAILABLE:
                self.algorithm = "bcrypt"
            else:
                raise ValueError("No password hashing library available. Install bcrypt or argon2-cffi")
        
        if self.algorithm == "argon2" and not ARGON2_AVAILABLE:
            raise ValueError("argon2-cffi not installed")
        if self.algorithm == "bcrypt" and not BCRYPT_AVAILABLE:
            raise ValueError("bcrypt not installed")
        
        if self.algorithm == "argon2":
            self.hasher = Argon2Hasher()
        elif self.algorithm == "bcrypt":
            self.hasher = None  # Use bcrypt directly
    
    def hash(self, password: str) -> str:
        """
        Hash a password
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        if self.algorithm == "argon2":
            return self.hasher.hash(password)
        elif self.algorithm == "bcrypt":
            salt = bcrypt.gensalt(rounds=12)
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
    
    def verify(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password
            password_hash: Hashed password
            
        Returns:
            True if password matches
        """
        try:
            if self.algorithm == "argon2":
                self.hasher.verify(password_hash, password)
                return True
            elif self.algorithm == "bcrypt":
                return bcrypt.checkpw(
                    password.encode('utf-8'),
                    password_hash.encode('utf-8')
                )
            else:
                return False
        except (VerifyMismatchError, ValueError, Exception):
            return False
    
    def needs_rehash(self, password_hash: str) -> bool:
        """
        Check if password hash needs to be rehashed (for algorithm upgrades)
        
        Args:
            password_hash: Current password hash
            
        Returns:
            True if rehash needed
        """
        if self.algorithm == "argon2":
            try:
                self.hasher.check_needs_rehash(password_hash)
                return False
            except:
                return True
        elif self.algorithm == "bcrypt":
            # Check if using old rounds
            try:
                rounds = bcrypt._bcrypt.__bcrypt_rounds_from_salt(
                    password_hash.encode('utf-8')
                )
                return rounds < 12
            except:
                return True
        return False


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token
    
    Args:
        length: Token length in bytes (will be hex encoded, so 2x chars)
        
    Returns:
        Hex-encoded secure token
    """
    return secrets.token_hex(length)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not (has_upper and has_lower):
        return False, "Password must contain both uppercase and lowercase letters"
    
    if not has_digit:
        return False, "Password must contain at least one digit"
    
    if not has_special:
        return False, "Password must contain at least one special character"
    
    # Check for common patterns
    common_patterns = [
        "123456", "password", "qwerty", "abc123",
        "password123", "admin", "letmein"
    ]
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            return False, f"Password contains common pattern: {pattern}"
    
    return True, ""

