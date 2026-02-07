"""Probes module - tool wrappers with self-registration.

Probes are the atomic units of capability - web search, document extraction,
API calls, etc. They extend LangGraph's @tool decorator with automatic
registration into a global probe registry.

Example:
    from astro_backend_service.probes import probe, ProbeRegistry

    @probe
    def search_web(query: str) -> str:
        '''Search the web for information.'''
        ...

    # Later, retrieve the probe
    web_search = ProbeRegistry.get("search_web")
    result = web_search.invoke(query="python tutorials")
"""

from astro_backend_service.probes.decorator import probe
from astro_backend_service.probes.exceptions import DuplicateProbeError
from astro_backend_service.probes.probe import Probe
from astro_backend_service.probes.registry import ProbeRegistry

# Import probe modules to trigger registration
from astro_backend_service.probes import google_news  # noqa: F401
from astro_backend_service.probes import due_diligence  # noqa: F401
from astro_backend_service.probes import excel  # noqa: F401

__all__ = [
    "probe",
    "Probe",
    "ProbeRegistry",
    "DuplicateProbeError",
]
