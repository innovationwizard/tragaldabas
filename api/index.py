"""Vercel serverless function handler for FastAPI"""

from mangum import Mangum
import sys
from pathlib import Path

# Add parent directory to path so we can import web.api
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.api import app

# Create Mangum handler for Vercel
# Note: WebSockets are not supported in Vercel serverless functions
# They will need to be handled differently or use a separate service
handler = Mangum(app, lifespan="off")

