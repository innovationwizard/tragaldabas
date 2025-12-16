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
# No need for Mangum adapter (which is for AWS Lambda)
# Export the FastAPI app directly - Vercel will handle it

# Optional: For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

