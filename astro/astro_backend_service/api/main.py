"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from astro_backend_service.api.dependencies import cleanup, get_foundry
from astro_backend_service.api.routes import (
    probes_router,
    directives_router,
    stars_router,
    constellations_router,
    runs_router,
    chat_router,
)
from astro_backend_service.foundry import ValidationError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup: initialize foundry
    await get_foundry()
    yield
    # Shutdown: cleanup resources
    await cleanup()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Astro API",
        description="Modular AI Agent Orchestration System",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    # Exception handlers
    @application.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "VALIDATION_ERROR"},
        )

    @application.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        error_str = str(exc).lower()
        if "not found" in error_str:
            return JSONResponse(
                status_code=404,
                content={"detail": str(exc), "error_code": "NOT_FOUND"},
            )
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "VALUE_ERROR"},
        )

    # Health check endpoint
    @application.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    return application


# Create app instance
app = create_app()
