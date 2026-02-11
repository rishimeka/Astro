"""FastAPI application entry point."""

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from astro_api.dependencies import cleanup, get_registry


def configure_logging() -> None:
    """Configure logging based on environment variables.

    Environment variables:
        LOG_LEVEL: Set the logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO
        LOG_FORMAT: Set the log format (simple, detailed). Default: detailed
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "detailed")

    # Map string to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(log_level, logging.INFO)

    # Choose format based on preference
    if log_format == "simple":
        format_str = "%(levelname)s: %(message)s"
    else:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_str,
        stream=sys.stdout,
    )

    # Set level for our modules
    logging.getLogger("astro").setLevel(level)
    logging.getLogger("astro_api").setLevel(level)

    # Reduce noise from third-party libraries unless DEBUG
    if level > logging.DEBUG:
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("langchain").setLevel(logging.WARNING)


# Configure logging on module load
configure_logging()

logger = logging.getLogger(__name__)
from astro.core.registry import ValidationError

from astro_api.routes import (
    chat_router,
    constellations_router,
    directives_router,
    files_router,
    probes_router,
    runs_router,
    stars_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    logger.info("Starting Astro V2 API application...")
    # Startup: initialize registry
    await get_registry()
    logger.info("Registry initialized successfully")
    yield
    # Shutdown: cleanup resources
    logger.info("Shutting down Astro API application...")
    await cleanup()
    logger.info("Cleanup complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Astro API",
        description="Modular AI Infrastructure & Multi-Agent Orchestration",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS middleware - configure ALLOWED_ORIGINS env var for production
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    logger.debug(f"Configuring CORS with allowed origins: {allowed_origins}")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Include routers
    application.include_router(probes_router, prefix="/probes", tags=["Probes"])
    application.include_router(
        directives_router, prefix="/directives", tags=["Directives"]
    )
    application.include_router(stars_router, prefix="/stars", tags=["Stars"])
    application.include_router(
        constellations_router, prefix="/constellations", tags=["Constellations"]
    )
    application.include_router(runs_router, prefix="/runs", tags=["Runs"])
    application.include_router(chat_router, prefix="/chat", tags=["Chat"])
    application.include_router(files_router, prefix="/files", tags=["Files"])

    # Exception handlers
    @application.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.warning(f"Validation error on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "VALIDATION_ERROR"},
        )

    @application.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        error_str = str(exc).lower()
        if "not found" in error_str:
            logger.debug(f"Not found on {request.method} {request.url.path}: {exc}")
            return JSONResponse(
                status_code=404,
                content={"detail": str(exc), "error_code": "NOT_FOUND"},
            )
        logger.warning(f"Value error on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "VALUE_ERROR"},
        )

    # Health check endpoint
    @application.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "2.0.0", "mode": "v2-launchpad"}

    return application


# Create app instance
app = create_app()
