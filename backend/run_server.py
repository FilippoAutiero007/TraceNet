"""
NetTrace Backend Server Entry Point
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

# Import app for uvicorn
from app.main import app

if __name__ == "__main__":
    # Get port from environment variable (Render compatibility)
    port = int(os.environ.get("PORT", 10000))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
