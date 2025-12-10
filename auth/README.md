# Authentication System

Industry-standard authentication system with login, logout, and password recovery.

## Features

- **Secure Password Hashing**: Supports bcrypt and Argon2
- **JWT Tokens**: Access and refresh token support
- **Account Lockout**: Protection against brute force attacks
- **Password Recovery**: Secure token-based password reset
- **Session Management**: Track and revoke user sessions
- **Role-Based Access**: User roles (admin, user, viewer)
- **Password Strength Validation**: Enforces strong passwords

## Security Best Practices

✅ **Password Hashing**: Uses bcrypt (12 rounds) or Argon2  
✅ **JWT Tokens**: Secure token-based authentication  
✅ **Account Lockout**: 5 failed attempts = 30 minute lockout  
✅ **Password Requirements**: Minimum 12 chars, mixed case, numbers, special chars  
✅ **Token Expiration**: Short-lived access tokens (1 hour), longer refresh tokens (30 days)  
✅ **Session Revocation**: Can revoke individual or all sessions  
✅ **Password Reset**: Time-limited tokens (1 hour), single-use  
✅ **No Information Leakage**: Doesn't reveal if email exists during login/reset  

## Usage

### Register a new user

```bash
python main.py auth register
```

### Login

```bash
python main.py auth login
```

This will:
- Prompt for email and password
- Create a session
- Save access token to `~/.tragaldabas_token`
- Display tokens for API use

### Logout

```bash
python main.py auth logout
```

Revokes the current session and removes saved token.

### Request Password Reset

```bash
python main.py auth reset-password-request
```

Sends a password reset email (email integration required).

### Reset Password

```bash
python main.py auth reset-password
```

Use the token from the reset email to set a new password.

### Change Password

```bash
python main.py auth change-password
```

Change password for authenticated users (requires current password).

### Check Current User

```bash
python main.py auth whoami
```

Shows information about the currently authenticated user.

## Database Schema

The auth system creates three tables:

- **users**: User accounts with password hashes
- **sessions**: Active user sessions with JWT tokens
- **password_reset_tokens**: Password reset tokens

## Configuration

Add to `.env`:

```env
# JWT Configuration (optional - auto-generated if not set)
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRY_HOURS=1
JWT_REFRESH_TOKEN_EXPIRY_DAYS=30

# Database (required for auth)
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

## API Integration

For programmatic access:

```python
from auth.service import AuthService
from auth.database import AuthDatabase
from auth.password import PasswordHasher
from auth.jwt import JWTManager
from db import DatabaseManager

# Initialize
db = DatabaseManager("postgresql://...")
auth_db = AuthDatabase(db)
jwt = JWTManager(secret_key="...")
hasher = PasswordHasher()
auth_service = AuthService(auth_db, jwt, hasher)

# Login
session, user = await auth_service.login(login_data)

# Verify token
user = await auth_service.verify_token(token)

# Use middleware
from auth.middleware import AuthMiddleware
middleware = AuthMiddleware(auth_service)

@middleware.require_auth(roles=["admin"])
async def protected_function(token: str, user: User, ...):
    ...
```

## Password Requirements

- Minimum 12 characters
- Maximum 128 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Cannot contain common patterns

## Security Considerations

1. **Never store plain text passwords** - Always hashed
2. **Use HTTPS** - In production, always use HTTPS
3. **Rate Limiting** - Implement rate limiting for login endpoints
4. **Email Verification** - Users start with `pending_verification` status
5. **Token Storage** - Tokens saved to `~/.tragaldabas_token` (consider secure storage)
6. **Session Cleanup** - Periodically clean expired sessions
7. **Password History** - Consider implementing password history (not included)

## Email Integration

The system includes placeholders for email sending. To implement:

1. Configure SMTP settings in config
2. Implement `_send_verification_email()` in AuthService
3. Implement `_send_password_reset_email()` in AuthService

Example with SMTP:

```python
import smtplib
from email.mime.text import MIMEText

async def _send_password_reset_email(self, user: User, token: str):
    reset_url = f"https://yourapp.com/reset?token={token}"
    # Send email...
```

