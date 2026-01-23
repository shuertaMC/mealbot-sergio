"""FastAPI application initialization with middleware and routes."""

import time
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import setup_logging, get_logger
from app.routers import organizations

# Setup logging before creating the app
settings = get_settings()
use_json_logs = settings.environment == "prod"
setup_logging(log_level=settings.log_level, use_json=use_json_logs)

logger = get_logger(__name__)
logger.info(f"Starting Mealbot API in {settings.environment} environment")

# Initialize FastAPI application
app = FastAPI(
    title="Mealbot API",
    description="RESTful service for managing lunch/meal pairings for organizations",
    version="2.0.0",
)


# Custom exception handler to convert 422 validation errors to 400
# This matches Go implementation behavior where validation errors return 400 Bad Request
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Convert FastAPI validation errors (422) to 400 Bad Request.

    This handler ensures that validation errors return 400 status code
    to match the behavior of the Go implementation, which returns 400
    for all request validation failures.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()},
    )


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log incoming requests and responses with timing information.

    This middleware:
    - Logs request start (method, path, query params)
    - Measures request duration
    - Logs response completion (status code, duration)
    """
    start_time = time.time()

    # Log incoming request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else "",
        }
    )

    # Process the request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Request completed: {response.status_code}",
        extra={
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3),
            "method": request.method,
            "path": request.url.path,
        }
    )

    return response


# Configure CORS middleware to match Go implementation behavior
# From cors.go lines 19-21:
# - w.Header().Set("Access-Control-Allow-Origin", r.Header.Get("Origin"))
# - w.Header().Add("Access-Control-Allow-Headers", AccessControlAllowHeaders)
# - w.Header().Add("Access-Control-Allow-Methods", "GET, POST, DELETE")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mirrors any origin like the Go implementation
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Origin",
        "Accept",
        "token",
    ],
)

# Mount static files directory
# Using Path(__file__).parent to resolve static directory relative to this file
# This prevents path resolution issues when starting the server from different directories
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Register API routers
app.include_router(organizations.router, tags=["organizations"])


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicator showing the service is running
    """
    return {"status": "ok"}


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        dict: Welcome message with API documentation link
    """
    return {
        "message": "Mealbot API",
        "docs": "/docs",
    }
