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
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,  # Fixed: matches Docker EXPOSE port
        reload=True
    )
