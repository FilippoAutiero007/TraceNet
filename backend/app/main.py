"""
NetTrace - FastAPI Backend
Converts natural language to Cisco Packet Tracer configurations
"""

import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.logger import setup_logger
from app.utils.errors import build_error_payload

load_dotenv()

# Configure logging on startup
log_level = settings.log_level
logger = setup_logger("tracenet", log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Log startup checks using the FastAPI lifespan API."""
    runtime_checks = settings.validate_runtime()
    logger.info(
        "TraceNet API starting up",
        extra={
            "environment": settings.environment,
            "log_level": log_level,
            "runtime_checks": runtime_checks,
        },
    )
    yield


app = FastAPI(
    title="NetTrace API",
    description="Convert natural language to Cisco network configurations",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = (exc.headers or {}).get("X-Error-Code", f"HTTP_{exc.status_code}")
    logger.warning(
        "HTTP exception",
        extra={
            "request_id": request.state.request_id,
            "path": request.url.path,
            "status_code": exc.status_code,
            "error_code": code,
        },
    )
    payload = build_error_payload(request=request, code=code, message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Request validation failed",
        extra={
            "request_id": request.state.request_id,
            "path": request.url.path,
            "status_code": 422,
            "error_code": "SEC_INVALID_SCHEMA",
            "validation_errors": exc.errors(),
        },
    )
    payload = build_error_payload(
        request=request,
        code="SEC_INVALID_SCHEMA",
        message="Invalid request payload.",
    )
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={
            "request_id": request.state.request_id,
            "path": request.url.path,
            "status_code": 500,
            "error_code": "INTERNAL_SERVER_ERROR",
        },
        exc_info=True,
    )
    payload = build_error_payload(
        request=request,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error.",
    )
    return JSONResponse(status_code=500, content=payload)


# CORS middleware for frontend
# Allow localhost for dev + Vercel production/preview domains
origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
# Security: Anchor the regex with $ to prevent subdomain suffixing bypasses
origin_regex = r"https://(?:tracenet|nettrace)(?:-git-[^.]+)?\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
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
        "version": "1.0.0",
    }


@app.get("/api/pka2xml-status")
def check_pka2xml():
    """Check availability of pka2xml encoding tool"""
    import shutil

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
        "details": version_info,
    }


# Import and include routers
from app.routers import generate

app.include_router(generate.router, prefix="/api")









