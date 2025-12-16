"""Vercel serverless function handler for FastAPI"""

import sys
from pathlib import Path

# Add parent directory to path so we can import web.api and config
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Also add current directory to path
current_dir = str(Path(__file__).parent)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import app after path is set up
from web.api import app

# Import Mangum after app is imported
from mangum import Mangum

# Create Mangum handler for Vercel
# Note: WebSockets are not supported in Vercel serverless functions
handler = Mangum(app, lifespan="off")

