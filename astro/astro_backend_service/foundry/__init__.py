"""Astro Foundry - Central registry and persistence layer."""

from astro_backend_service.foundry.validation import ValidationError, ValidationWarning
from astro_backend_service.foundry.extractor import (
    extract_references,
    validate_at_syntax,
    render_content_with_variables,
)
from astro_backend_service.foundry.indexes import FoundryIndexes
from astro_backend_service.foundry.foundry import Foundry

__all__ = [
    # Core
    "Foundry",
    "FoundryIndexes",
    # Validation
    "ValidationError",
    "ValidationWarning",
    # Extraction
    "extract_references",
    "validate_at_syntax",
    "render_content_with_variables",
]
