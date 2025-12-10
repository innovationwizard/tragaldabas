"""Authentication middleware"""

from typing import Optional, Callable, Any
from functools import wraps

from .service import AuthService
from .models import User
from core.exceptions import TragaldabasError


class AuthError(TragaldabasError):
    """Authentication error"""
    pass


class AuthMiddleware:
    """Authentication middleware for protecting routes/functions"""
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
    
    async def authenticate(self, token: str) -> Optional[User]:
        """
        Authenticate token and return user
        
        Args:
            token: JWT access token
            
        Returns:
            User if authenticated, None otherwise
        """
        return await self.auth_service.verify_token(token)
    
    def require_auth(self, roles: Optional[list] = None):
        """
        Decorator to require authentication
        
        Args:
            roles: Optional list of allowed roles
            
        Usage:
            @middleware.require_auth(roles=["admin"])
            async def protected_function(token: str, ...):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract token from kwargs or first arg
                token = kwargs.get('token') or (args[0] if args else None)
                
                if not token:
                    raise AuthError("Authentication required")
                
                user = await self.authenticate(token)
                if not user:
                    raise AuthError("Invalid or expired token")
                
                # Check roles if specified
                if roles and user.role.value not in roles:
                    raise AuthError(f"Access denied. Required roles: {roles}")
                
                # Add user to kwargs
                kwargs['user'] = user
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator

