"""API route modules."""

from astro_api.routes.chat import router as chat_router
from astro_api.routes.constellations import (
    router as constellations_router,
)
from astro_api.routes.directives import router as directives_router
from astro_api.routes.files import router as files_router
from astro_api.routes.probes import router as probes_router
from astro_api.routes.runs import router as runs_router
from astro_api.routes.stars import router as stars_router

__all__ = [
    "probes_router",
    "directives_router",
    "stars_router",
    "constellations_router",
    "runs_router",
    "chat_router",
    "files_router",
]
