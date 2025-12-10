"""CLI commands for authentication"""

import click
import asyncio
import getpass
from pathlib import Path

from .service import AuthService
from .database import AuthDatabase
from .password import PasswordHasher
from .jwt import JWTManager
from .models import UserCreate, UserLogin, PasswordResetRequest, PasswordReset, PasswordChange
from db import DatabaseManager
from config import settings
import secrets


def get_auth_service() -> AuthService:
    """Initialize auth service"""
    if not settings.DATABASE_URL:
        raise click.ClickException("DATABASE_URL not configured. Set it in .env file")
    
    db_manager = DatabaseManager(settings.DATABASE_URL)
    auth_db = AuthDatabase(db_manager)
    
    # Initialize components
    jwt_secret = getattr(settings, 'JWT_SECRET_KEY', None) or secrets.token_hex(32)
    jwt_manager = JWTManager(secret_key=jwt_secret)
    password_hasher = PasswordHasher()
    
    return AuthService(auth_db, jwt_manager, password_hasher)


@click.group()
def auth_cli():
    """Authentication commands"""
    pass


@auth_cli.command()
@click.option('--email', prompt=True, help='Email address')
@click.option('--username', prompt=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
@click.option('--full-name', prompt=True, help='Full name')
def register(email: str, username: str, password: str, full_name: str):
    """Register a new user"""
    async def _register():
        auth_service = get_auth_service()
        
        user_data = UserCreate(
            email=email,
            username=username,
            password=password,
            full_name=full_name
        )
        
        try:
            user = await auth_service.register(user_data)
            click.echo(f"✓ User registered successfully: {user.email}")
            click.echo(f"  User ID: {user.id}")
            click.echo(f"  Status: {user.status.value}")
            click.echo("  Note: Account is pending verification")
        except Exception as e:
            click.echo(f"✗ Registration failed: {e}", err=True)
            raise click.Abort()
    
    asyncio.run(_register())


@auth_cli.command()
@click.option('--email', prompt=True, help='Email address')
@click.option('--password', prompt=True, hide_input=True, help='Password')
def login(email: str, password: str):
    """Login and get access token"""
    async def _login():
        auth_service = get_auth_service()
        
        login_data = UserLogin(email=email, password=password)
        
        try:
            session, user = await auth_service.login(login_data)
            
            click.echo(f"✓ Login successful!")
            click.echo(f"  User: {user.email} ({user.username})")
            click.echo(f"  Role: {user.role.value}")
            click.echo(f"\n  Access Token:")
            click.echo(f"  {session.token}")
            click.echo(f"\n  Refresh Token:")
            click.echo(f"  {session.refresh_token}")
            click.echo(f"\n  Expires at: {session.expires_at}")
            
            # Save token to file (optional)
            token_file = Path.home() / '.tragaldabas_token'
            token_file.write_text(session.token)
            click.echo(f"\n  Token saved to: {token_file}")
            
        except Exception as e:
            click.echo(f"✗ Login failed: {e}", err=True)
            raise click.Abort()
    
    asyncio.run(_login())


@auth_cli.command()
@click.option('--token', help='Access token (or read from ~/.tragaldabas_token)')
def logout(token: str):
    """Logout and revoke session"""
    async def _logout():
        auth_service = get_auth_service()
        
        # Get token from file if not provided
        if not token:
            token_file = Path.home() / '.tragaldabas_token'
            if token_file.exists():
                token = token_file.read_text().strip()
            else:
                click.echo("✗ No token found. Please provide --token or login first", err=True)
                raise click.Abort()
        
        try:
            success = await auth_service.logout(token)
            if success:
                click.echo("✓ Logout successful")
                
                # Remove token file
                token_file = Path.home() / '.tragaldabas_token'
                if token_file.exists():
                    token_file.unlink()
            else:
                click.echo("✗ Logout failed: Invalid token", err=True)
        except Exception as e:
            click.echo(f"✗ Logout failed: {e}", err=True)
    
    asyncio.run(_logout())


@auth_cli.command()
@click.option('--email', prompt=True, help='Email address')
def reset_password_request(email: str):
    """Request password reset"""
    async def _request():
        auth_service = get_auth_service()
        
        request = PasswordResetRequest(email=email)
        
        try:
            await auth_service.request_password_reset(request)
            click.echo(f"✓ Password reset email sent to {email}")
            click.echo("  Check your email for reset instructions")
        except Exception as e:
            click.echo(f"✗ Request failed: {e}", err=True)
    
    asyncio.run(_request())


@auth_cli.command()
@click.option('--token', prompt=True, help='Reset token from email')
@click.option('--new-password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
def reset_password(token: str, new_password: str):
    """Reset password using token"""
    async def _reset():
        auth_service = get_auth_service()
        
        reset_data = PasswordReset(token=token, new_password=new_password)
        
        try:
            await auth_service.reset_password(reset_data)
            click.echo("✓ Password reset successful")
            click.echo("  You can now login with your new password")
        except Exception as e:
            click.echo(f"✗ Password reset failed: {e}", err=True)
            raise click.Abort()
    
    asyncio.run(_reset())


@auth_cli.command()
@click.option('--current-password', prompt=True, hide_input=True, help='Current password')
@click.option('--new-password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
@click.option('--token', help='Access token (or read from ~/.tragaldabas_token)')
def change_password(current_password: str, new_password: str, token: str):
    """Change password (requires authentication)"""
    async def _change():
        auth_service = get_auth_service()
        
        # Get token and user
        if not token:
            token_file = Path.home() / '.tragaldabas_token'
            if token_file.exists():
                token = token_file.read_text().strip()
            else:
                click.echo("✗ No token found. Please login first", err=True)
                raise click.Abort()
        
        user = await auth_service.verify_token(token)
        if not user:
            click.echo("✗ Invalid or expired token. Please login again", err=True)
            raise click.Abort()
        
        change_data = PasswordChange(
            current_password=current_password,
            new_password=new_password
        )
        
        try:
            await auth_service.change_password(user.id, change_data)
            click.echo("✓ Password changed successfully")
        except Exception as e:
            click.echo(f"✗ Password change failed: {e}", err=True)
            raise click.Abort()
    
    asyncio.run(_change())


@auth_cli.command()
@click.option('--token', help='Access token (or read from ~/.tragaldabas_token)')
def whoami(token: str):
    """Show current user information"""
    async def _whoami():
        auth_service = get_auth_service()
        
        if not token:
            token_file = Path.home() / '.tragaldabas_token'
            if token_file.exists():
                token = token_file.read_text().strip()
            else:
                click.echo("✗ No token found. Please login first", err=True)
                return
        
        user = await auth_service.verify_token(token)
        if not user:
            click.echo("✗ Invalid or expired token", err=True)
            return
        
        click.echo(f"User ID: {user.id}")
        click.echo(f"Email: {user.email}")
        click.echo(f"Username: {user.username}")
        click.echo(f"Full Name: {user.full_name or 'N/A'}")
        click.echo(f"Role: {user.role.value}")
        click.echo(f"Status: {user.status.value}")
        click.echo(f"Email Verified: {user.email_verified}")
        if user.last_login:
            click.echo(f"Last Login: {user.last_login}")
    
    asyncio.run(_whoami())

