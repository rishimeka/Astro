"""
Validator module for Star Foundry probes and constellations.

This module ensures:
- Stars reference valid probe IDs
- Constellations reference valid star IDs
- No circular loops inside Constellations (if using edges)
- Developers are warned when probes disappear
- The UI can display warnings proactively
"""

from probes import ProbeRegistry
from star_foundry import Star


def validate_star_probes(star: Star, probe_registry: ProbeRegistry) -> list[str]:
    """Validate that all probes referenced by a Star exist in the probe registry.

    Args:
        star: The Star object to validate
        probe_registry: The ProbeRegistry instance to check against

    Returns:
        List of missing probe IDs that are referenced by the star but not found in the registry
    """
    missing = []
    for pid in star.probes:
        if probe_registry.get_probe(pid) is None:
            missing.append(pid)
    return missing
