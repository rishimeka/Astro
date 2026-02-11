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

    def clear(self) -> None:
        """Clear all indexes (except probes which are code-defined)."""
        self.directives.clear()
        # Note: probes are not cleared as they are code-defined

    def get_directive(self, id: str) -> Directive | None:
        """Get directive by ID."""
        return self.directives.get(id)

    def get_probe(self, name: str) -> Probe | None:
        """Get probe by name."""
        return self.probes.get(name)

    def probe_exists(self, name: str) -> bool:
        """Check if probe is registered."""
        return name in self.probes
