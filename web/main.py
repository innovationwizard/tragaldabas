"""Web application entry point"""

import uvicorn
from web.api import app

if __name__ == "__main__":
    uvicorn.run(
        "web.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

