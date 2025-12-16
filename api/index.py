"""Vercel serverless function handler for FastAPI"""

import sys
from pathlib import Path

# Add parent directory to path so we can import web.api and config
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import app after path is set up
try:
    from web.api import app
except Exception as e:
    # If import fails, create a minimal app
    from fastapi import FastAPI
    app = FastAPI()
    print(f"Warning: Failed to import web.api: {e}")

# Import Mangum after app is imported
from mangum import Mangum

# Create Mangum handler for Vercel
# Note: WebSockets are not supported in Vercel serverless functions
handler = Mangum(app, lifespan="off")

# Ensure handler is callable
if not callable(handler):
    raise RuntimeError("Handler is not callable")

