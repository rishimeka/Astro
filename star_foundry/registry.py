"""
Registry for storing and retrieving Star entities.
"""

import logging
from typing import List, Optional
from star_foundry import Star
from probes import ProbeRegistry

logger = logging.getLogger(__name__)


class StarRegistry:
    """
    Registry for storing and retrieving Star entities.
    """

    def __init__(self, probe_registry: ProbeRegistry, validator=None):
        """
        Initialize an empty star registry.
        """
        self._stars = {}
        self.probe_registry = probe_registry
        self.validator = validator

    def register(self, star: Star):
        self._stars[star.id] = star
        logger.debug(f"Registered Star: {star.id} - {star.name}")

    def finalize(self):
        """
        Finalize the registry by resolving all references and probes for each Star.
        """
        logger.info("Finalizing StarRegistry: resolving references and probes.")
        for star in self._stars.values():
            self.resolve_references(star)
            self.resolve_probes(star)
        logger.info("Checking for cycles in Star references.")
        if self.validator:
            cycles = self.validator.detect_cycles()
            if cycles:
                for cycle in cycles:
                    logger.warning(
                        f"Cycle detected in Star references: {' -> '.join(cycle)}"
                    )
        logger.info("StarRegistry finalized: all references and probes resolved.")

    def get(self, star_id: str) -> Optional[Star]:
        """
        Retrieve a specific Star by its ID.

        Args:
            star_id: The unique identifier of the Star

        Returns:
            Star instance if found, None otherwise
        """
        return self._stars.get(star_id)

    def list_stars(self) -> List[Star]:
        """Get a list of all registered Stars.

        Returns:
            List of Star instances
        """
        return list(self._stars.values())

    def resolve_references(self, star: Star):
        """Resolve and retrieve all Stars referenced by the given Star.

        Args:
            star: The Star instance whose references to resolve
        Returns:
            None
        """
        if self.validator:
            valid_refs = self.validator.validate_references(star)
        else:
            # Fallback if no validator is provided
            valid_refs = [r for r in star.references if r in self._stars]
        star.resolved_references = [self._stars[r] for r in valid_refs]
        logger.debug(f"Star {star.id} resolved references: {valid_refs}")
        return None

    def resolve_probes(self, star: Star):
        """Retrieve all probe IDs associated with the given Star.

        Args:
            star: The Star instance whose probes to retrieve

        Returns:
            None
        """
        if self.validator:
            valid_probes = self.validator.validate_probes(star)
        else:
            # Fallback if no validator is provided
            valid_probes = [p for p in star.probes if self.probe_registry.get_probe(p)]
        star.resolved_probes = [self.probe_registry.get_probe(p) for p in valid_probes]
        logger.debug(f"Star {star.id} resolved probes: {valid_probes}")
        return None
