"""Enhanced StarFoundry for the Execution Engine.

This module provides an enhanced Star Foundry that wraps the existing
StarRegistry and adds execution-specific functionality like content
resolution and hashing.
"""

import hashlib
from typing import Dict, List, Optional, Set

from star_foundry import Star, StarRegistry
from execution.models.constellation import Constellation


class ExecutionStarFoundry:
    """Enhanced Star Foundry for execution engine operations.

    Wraps the existing StarRegistry and adds:
    - Star content resolution (following references)
    - Content hashing for caching
    - Constellation loading and validation
    """

    def __init__(self, star_registry: StarRegistry):
        """Initialize the execution star foundry.

        Args:
            star_registry: The underlying StarRegistry instance
        """
        self._registry = star_registry
        self._content_cache: Dict[str, str] = {}
        self._hash_cache: Dict[str, str] = {}

    @property
    def registry(self) -> StarRegistry:
        """Get the underlying star registry."""
        return self._registry

    # ==================== Star Access ====================

    def get_by_id(self, star_id: str) -> Optional[Star]:
        """Get a Star by its ID.

        Args:
            star_id: The unique identifier of the Star

        Returns:
            Star instance if found, None otherwise
        """
        return self._registry.get(star_id)

    def get_by_name(self, name: str) -> Optional[Star]:
        """Get a Star by its name.

        Args:
            name: The name of the Star

        Returns:
            Star instance if found, None otherwise
        """
        for star in self._registry.list_stars():
            if star.name.lower() == name.lower():
                return star
        return None

    def list_all(self) -> List[Star]:
        """Get all registered Stars.

        Returns:
            List of all Star instances
        """
        return self._registry.list_stars()

    # ==================== Content Resolution ====================

    def resolve_star(self, star_id: str) -> str:
        """Resolve a Star to its full prompt content.

        Follows references and compiles into a single prompt.
        Results are cached for performance.

        Args:
            star_id: The ID of the Star to resolve

        Returns:
            The compiled prompt content

        Raises:
            ValueError: If the Star is not found
        """
        # Check cache first
        if star_id in self._content_cache:
            return self._content_cache[star_id]

        star = self.get_by_id(star_id)
        if not star:
            raise ValueError(f"Star not found: {star_id}")

        # Build content by following references
        content_parts: List[str] = []
        visited: Set[str] = set()

        self._collect_content(star_id, content_parts, visited)

        resolved_content = "\n\n".join(content_parts)

        # Cache the result
        self._content_cache[star_id] = resolved_content

        return resolved_content

    def _collect_content(
        self,
        star_id: str,
        content_parts: List[str],
        visited: Set[str],
    ) -> None:
        """Recursively collect content from Star and its references.

        Args:
            star_id: The ID of the Star to collect from
            content_parts: List to append content to
            visited: Set of already visited Star IDs
        """
        if star_id in visited:
            return
        visited.add(star_id)

        star = self.get_by_id(star_id)
        if not star:
            return

        # First, collect from referenced Stars (base content comes first)
        for ref_id in star.references:
            self._collect_content(ref_id, content_parts, visited)

        # Then add this Star's content
        if star.content:
            content_parts.append(star.content)

    def get_content_hash(self, star_id: str) -> str:
        """Get a hash of the resolved Star content.

        Useful for caching and detecting content changes.

        Args:
            star_id: The ID of the Star

        Returns:
            A 16-character hex hash of the content
        """
        # Check cache first
        if star_id in self._hash_cache:
            return self._hash_cache[star_id]

        content = self.resolve_star(star_id)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Cache the result
        self._hash_cache[star_id] = content_hash

        return content_hash

    def clear_cache(self, star_id: Optional[str] = None) -> None:
        """Clear the content and hash caches.

        Args:
            star_id: If provided, only clear cache for this Star.
                    If None, clear all caches.
        """
        if star_id:
            self._content_cache.pop(star_id, None)
            self._hash_cache.pop(star_id, None)
        else:
            self._content_cache.clear()
            self._hash_cache.clear()

    # ==================== Probe Access ====================

    def get_probes_for_star(self, star_id: str) -> List[str]:
        """Get all probe IDs authorized for a Star.

        Args:
            star_id: The ID of the Star

        Returns:
            List of authorized probe IDs
        """
        star = self.get_by_id(star_id)
        if not star:
            return []

        return star.probes.copy()

    def get_resolved_probes_for_star(self, star_id: str) -> List[dict]:
        """Get all resolved probe metadata for a Star.

        Args:
            star_id: The ID of the Star

        Returns:
            List of probe metadata dictionaries
        """
        star = self.get_by_id(star_id)
        if not star:
            return []

        return list(star.resolved_probes)

    # ==================== Constellation Methods ====================

    def validate_constellation(self, constellation: Constellation) -> List[str]:
        """Validate a Constellation's Star references.

        Args:
            constellation: The Constellation to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        for node in constellation.nodes:
            if not self.get_by_id(node.star_id):
                errors.append(
                    f"Node {node.node_id} references non-existent Star {node.star_id}"
                )

        # Check entry node exists
        if not any(n.node_id == constellation.entry_node for n in constellation.nodes):
            errors.append(f"Entry node {constellation.entry_node} not found in nodes")

        # Check exit nodes exist
        node_ids = {n.node_id for n in constellation.nodes}
        for exit_node in constellation.exit_nodes:
            if exit_node not in node_ids:
                errors.append(f"Exit node {exit_node} not found in nodes")

        # Check edges reference valid nodes
        for edge in constellation.edges:
            if edge.from_node not in node_ids:
                errors.append(f"Edge from_node {edge.from_node} not found in nodes")
            if edge.to_node not in node_ids:
                errors.append(f"Edge to_node {edge.to_node} not found in nodes")

        return errors

    def get_stars_for_constellation(
        self, constellation: Constellation
    ) -> Dict[str, Star]:
        """Get all Stars referenced by a Constellation.

        Args:
            constellation: The Constellation

        Returns:
            Dictionary mapping Star IDs to Star instances
        """
        stars = {}
        for node in constellation.nodes:
            star = self.get_by_id(node.star_id)
            if star:
                stars[node.star_id] = star
        return stars

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the Star Foundry.

        Returns:
            Dictionary with counts and cache stats
        """
        return {
            "total_stars": len(self._registry.list_stars()),
            "cached_content": len(self._content_cache),
            "cached_hashes": len(self._hash_cache),
        }
