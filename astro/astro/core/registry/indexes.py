"""In-memory indexes for fast lookups of Layer 1 primitives."""

from dataclasses import dataclass, field
from typing import Any

from astro.core.models.directive import Directive


@dataclass
class Probe:
    """Probe definition for tool registration."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    handler: Any | None = None  # Callable, but typed as Any to avoid import cycles


@dataclass
class RegistryIndexes:
    """In-memory indexes for Layer 1 primitives (Directives and Probes only).

    Layer 1 (core) only manages Directives and Probes.
    Stars, Constellations are Layer 2 concepts managed by orchestration.
    """

    directives: dict[str, Directive] = field(default_factory=dict)
    probes: dict[str, Probe] = field(default_factory=dict)
    tags_index: dict[str, list[str]] = field(default_factory=dict)
    name_index: dict[str, str] = field(default_factory=dict)

    def clear(self) -> None:
        """Clear all indexes (except probes which are code-defined)."""
        self.directives.clear()
        self.tags_index.clear()
        self.name_index.clear()
        # Note: probes are not cleared as they are code-defined

    def index_directive(self, directive: Directive) -> None:
        """Add a directive to all secondary indexes."""
        # Name index (lowercase for case-insensitive lookup)
        self.name_index[directive.name.lower()] = directive.id

        # Tags index
        for tag in directive.tags:
            tag_lower = tag.lower()
            if tag_lower not in self.tags_index:
                self.tags_index[tag_lower] = []
            if directive.id not in self.tags_index[tag_lower]:
                self.tags_index[tag_lower].append(directive.id)

    def unindex_directive(self, directive: Directive) -> None:
        """Remove a directive from all secondary indexes."""
        # Name index
        name_key = directive.name.lower()
        if self.name_index.get(name_key) == directive.id:
            del self.name_index[name_key]

        # Tags index
        for tag in directive.tags:
            tag_lower = tag.lower()
            if tag_lower in self.tags_index:
                self.tags_index[tag_lower] = [
                    did for did in self.tags_index[tag_lower] if did != directive.id
                ]
                if not self.tags_index[tag_lower]:
                    del self.tags_index[tag_lower]

    def get_directive(self, id: str) -> Directive | None:
        """Get directive by ID."""
        return self.directives.get(id)

    def get_directive_ids_by_tag(self, tag: str) -> list[str]:
        """Get directive IDs matching a tag."""
        return self.tags_index.get(tag.lower(), [])

    def get_directive_id_by_name(self, name: str) -> str | None:
        """Get directive ID by name (case-insensitive)."""
        return self.name_index.get(name.lower())

    def get_probe(self, name: str) -> Probe | None:
        """Get probe by name."""
        return self.probes.get(name)

    def probe_exists(self, name: str) -> bool:
        """Check if probe is registered."""
        return name in self.probes
