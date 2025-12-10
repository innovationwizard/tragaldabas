"""JWT token management"""

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from core.exceptions import TragaldabasError


class JWTError(TragaldabasError):
    """JWT-related error"""
    pass


class JWTManager:
    """JWT token generation and validation"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expiry: timedelta = timedelta(hours=1),
        refresh_token_expiry: timedelta = timedelta(days=30)
    ):
        """
        Initialize JWT manager
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (HS256, RS256, etc.)
            access_token_expiry: Access token expiration time
            refresh_token_expiry: Refresh token expiration time
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry
    
    def generate_access_token(self, user_id: int, email: str, role: str) -> str:
        """
        Generate access token
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            
        Returns:
            JWT access token
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": datetime.utcnow() + self.access_token_expiry,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def generate_refresh_token(self, user_id: int) -> str:
        """
        Generate refresh token
        
        Args:
            user_id: User ID
            
        Returns:
            JWT refresh token
        """
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "jti": secrets.token_hex(16),  # JWT ID for revocation
            "exp": datetime.utcnow() + self.refresh_token_expiry,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            Decoded token payload
            
        Raises:
            JWTError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                raise JWTError(f"Invalid token type. Expected {token_type}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise JWTError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise JWTError(f"Invalid token: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
        """
        payload = self.verify_token(refresh_token, token_type="refresh")
        user_id = payload["user_id"]
        
        # Get user info from database (would need DB access)
        # For now, return a token with minimal info
        # In practice, you'd fetch user from DB
        return self.generate_access_token(
            user_id=user_id,
            email=payload.get("email", ""),
            role=payload.get("role", "user")
        )

