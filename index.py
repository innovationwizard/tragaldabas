"""Vercel serverless function handler for FastAPI"""

import sys
from pathlib import Path

# Add current directory to path so we can import web.api and config
current_dir = str(Path(__file__).parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import app after path is set up
from web.api import app

# Vercel natively supports ASGI apps like FastAPI
# Export the FastAPI app - Vercel will auto-detect it
# Routes will be at root level (e.g., /login, /api/auth/login)

