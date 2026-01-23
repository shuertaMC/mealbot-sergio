"""FastAPI application initialization with middleware and routes."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import setup_logging, get_logger

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
