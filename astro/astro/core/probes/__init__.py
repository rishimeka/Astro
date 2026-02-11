"""Probe system for Astro V2.

This module exports the probe infrastructure and all registered probes.
Probes are tools that can be bound to LLMs for function calling.
"""

from astro.core.probes.probe import Probe
from astro.core.probes.registry import ProbeRegistry
from astro.core.probes.decorator import probe
from astro.core.probes.exceptions import DuplicateProbeError

# Import probe implementations to register them
from astro.core.probes import due_diligence, google_news, excel

__all__ = [
    "Probe",
    "ProbeRegistry",
    "probe",
    "DuplicateProbeError",
    "due_diligence",
    "google_news",
    "excel",
]
