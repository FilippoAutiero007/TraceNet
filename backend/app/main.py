"""
NetTrace - FastAPI Backend
Converts natural language to Cisco Packet Tracer configurations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from app.utils.logger import setup_logger

load_dotenv()

# Configure logging on startup
log_level = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logger("tracenet", log_level)

app = FastAPI(
    title="NetTrace API",
    description="Convert natural language to Cisco network configurations",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    logger.info("TraceNet API starting up", extra={
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": log_level
    })

# CORS middleware for frontend
# Allow localhost for dev + Vercel production/preview domains
origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,https://tracenet.vercel.app,https://tracenet-git-*.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NetTrace API",
        "version": "1.0.0"
    }

@app.get("/api/pka2xml-status")
def check_pka2xml():
    """Check availability of pka2xml encoding tool"""
    import shutil
    import subprocess
    pka_path = shutil.which("pka2xml")
    
    version_info = "Unknown"
    if pka_path:
        try:
            # pka2xml might not offer --version via CLI easily but we can try running it
            # or just confirm its presence
            version_info = "Available (Binary found)"
        except Exception:
            pass
            
    return {
        "available": bool(pka_path), 
        "path": pka_path,
        "details": version_info
    }

# Import and include routers
from app.routers import generate
app.include_router(generate.router, prefix="/api")
