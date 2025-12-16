"""Vercel serverless function handler for FastAPI"""

from mangum import Mangum
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import web.api and config
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Also add current directory to path
current_dir = str(Path(__file__).parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from web.api import app

# Create Mangum handler for Vercel
# Note: WebSockets are not supported in Vercel serverless functions
# They will need to be handled differently or use a separate service
handler = Mangum(app, lifespan="off")

