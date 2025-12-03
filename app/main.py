"""FastAPI application entry point for ElevenLabs OpenMemory Integration.

This module initializes the FastAPI application with:
- Title and description for API documentation
- Startup configuration validation
- Health check endpoint
- Webhook routers for client-data, search-data, and post-call
- CORS configuration for development
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_startup_configuration, ConfigurationError
from app.webhooks.client_data import router as client_data_router
from app.webhooks.search_data import router as search_data_router
from app.webhooks.post_call import router as post_call_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Validates configuration
    - Shutdown: Cleanup resources
    """
    # Startup
    logger.info("Starting ElevenLabs OpenMemory Integration...")
    try:
        validate_startup_configuration()
        logger.info("Configuration validated successfully")
    except ConfigurationError as e:
        logger.warning(f"Configuration validation skipped in dev mode: {e}")

    yield

    # Shutdown
    logger.info("Shutting down ElevenLabs OpenMemory Integration...")
    try:
        from app.memory.client import close_client
        close_client()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="ElevenLabs OpenMemory Integration",
    description=(
        "FastAPI backend integrating ElevenLabs Agents Platform with OpenMemory "
        "for persistent caller profiles and personalized voice AI conversations. "
        "Uses phone numbers as the primary identifier for user profiles."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint for service monitoring.

    Returns:
        A dictionary with health status and timestamp.
    """
    return {
        "status": "healthy",
        "service": "elevenlabs-openmemory-integration",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include webhook routers
app.include_router(
    client_data_router,
    prefix="/webhook",
    tags=["Webhooks"]
)
app.include_router(
    search_data_router,
    prefix="/webhook",
    tags=["Webhooks"]
)
app.include_router(
    post_call_router,
    prefix="/webhook",
    tags=["Webhooks"]
)


# Root endpoint for basic info
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint providing basic API information.

    Returns:
        A dictionary with API name and documentation URLs.
    """
    return {
        "name": "ElevenLabs OpenMemory Integration API",
        "docs": "/docs",
        "health": "/health",
    }