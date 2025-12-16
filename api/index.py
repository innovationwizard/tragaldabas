"""Vercel serverless function handler for FastAPI"""

import sys
from pathlib import Path

# Add parent directory to path so we can import web.api and config
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import app after path is set up
from web.api import app

# Vercel natively supports ASGI apps like FastAPI
# Export the FastAPI app - Vercel will detect it automatically
# Do not export as 'handler' - let Vercel auto-detect from 'app'

