"""
NetTrace - FastAPI Backend
Converts natural language to Cisco Packet Tracer configurations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="NetTrace API",
    description="Convert natural language to Cisco network configurations",
    version="1.0.0"
)

# CORS middleware for frontend
# CORS middleware for frontend
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
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

@app.get("/api")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to NetTrace API",
        "docs": "/docs",
        "health": "/api/health"
    }

# Import and include routers
from app.routers import generate
app.include_router(generate.router, prefix="/api")
