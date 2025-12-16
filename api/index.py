"""Vercel serverless function handler for FastAPI"""

import sys
from pathlib import Path

# Add parent directory to path so we can import web.api and config
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Lazy initialization to avoid issues with Vercel handler detection
_handler = None

def get_handler():
    global _handler
    if _handler is None:
        from web.api import app
        from mangum import Mangum
        _handler = Mangum(app, lifespan="off")
    return _handler

# Export handler for Vercel
handler = get_handler()

