"""
Global validator for Star objects in the Star Foundry system.

- detects missing refs globally
- detects missing probes globally
- detects cycles
- reports warnings

"""

import logging

from star_foundry import Star, StarRegistry
from probes import ProbeRegistry

logger = logging.getLogger(__name__)


class StarValidator:
    """Validator for Star objects, ensuring references and probes are valid."""

    def __init__(self, star_registry: StarRegistry, probe_registry: ProbeRegistry):
        self.star_registry = star_registry
        self.probe_registry = probe_registry

    def validate_references(self, star: Star):
        """Validate that all references in the given Star exist in the registry.

        Args:
            star: The Star instance whose references to validate

        Returns:
            List of available references
        """
        missing_refs = [
            r for r in star.references if r not in self.star_registry._stars
        ]
        star.missing_references = missing_refs
        logger.warning(f"Star {star.id} missing references: {missing_refs}")
        return [r for r in star.references if r in self.star_registry._stars]

    def validate_probes(self, star: Star):
        """Validate that all probes in the given Star exist in the ProbeRegistry.

        Args:
            star: The Star instance whose probes to validate

        Returns:
            List of available probe IDs
        """
        missing_probes = [
            p for p in star.probes if not self.probe_registry.get_probe(p)
        ]
        star.missing_probes = missing_probes
        logger.warning(f"Star {star.id} missing probes: {missing_probes}")
        return [p for p in star.probes if self.probe_registry.get_probe(p)]

    def detect_cycles(self):
        """Detect cycles in the Star references across the registry.

        Returns:
            list[list[str]]: List of cycles detected, each cycle is a list of Star IDs.
        """
        visited = set()
        recursion_stack = set()
        cycles = []

        def dfs(star_id, path):
            if star_id in recursion_stack:
                # Cycle found — return the cycle slice from where it started
                cycle_start = path.index(star_id)
                cycles.append(path[cycle_start:])
                return

            if star_id in visited:
                return

            visited.add(star_id)
            recursion_stack.add(star_id)

            star = self.star_registry._stars.get(star_id)
            if star:
                for ref_id in star.references:
                    dfs(ref_id, path + [ref_id])

            recursion_stack.remove(star_id)

        # run dfs from all nodes
        for star_id in self.star_registry._stars.keys():
            if star_id not in visited:
                dfs(star_id, [star_id])

        return cycles
