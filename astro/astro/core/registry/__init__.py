"""Registry module for Layer 1 primitives (Directives and Probes).

This module provides the central registry for managing directives and probes,
with validation, @ syntax extraction, and persistence via CoreStorageBackend.
"""

from astro.core.registry.extractor import (
    create_template_variables,
    extract_references,
    render_content_with_variables,
    validate_at_syntax,
)
from astro.core.registry.indexes import Probe, RegistryIndexes
from astro.core.registry.registry import Registry
from astro.core.registry.validation import ValidationError, ValidationWarning

__all__ = [
    "Registry",
    "ValidationError",
    "ValidationWarning",
    "Probe",
    "RegistryIndexes",
    "extract_references",
    "create_template_variables",
    "render_content_with_variables",
    "validate_at_syntax",
]
