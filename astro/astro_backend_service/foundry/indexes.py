"""In-memory indexes for fast lookups."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from astro_backend_service.models import Directive, Constellation
from astro_backend_service.models.stars.base import BaseStar


@dataclass
class Probe:
    """Probe definition for tool registration."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Any] = None  # Callable, but typed as Any to avoid import cycles


@dataclass
class FoundryIndexes:
    """In-memory indexes for all Astro primitives."""

    directives: Dict[str, Directive] = field(default_factory=dict)
    stars: Dict[str, BaseStar] = field(default_factory=dict)
    constellations: Dict[str, Constellation] = field(default_factory=dict)
    probes: Dict[str, Probe] = field(default_factory=dict)

    def clear(self) -> None:
        """Clear all indexes."""
        self.directives.clear()
        self.stars.clear()
        self.constellations.clear()
        # Note: probes are not cleared as they are code-defined

    def get_directive(self, id: str) -> Optional[Directive]:
        """Get directive by ID."""
        return self.directives.get(id)

    def get_star(self, id: str) -> Optional[BaseStar]:
        """Get star by ID."""
        return self.stars.get(id)

    def get_constellation(self, id: str) -> Optional[Constellation]:
        """Get constellation by ID."""
        return self.constellations.get(id)

    def get_probe(self, name: str) -> Optional[Probe]:
        """Get probe by name."""
        return self.probes.get(name)

    def probe_exists(self, name: str) -> bool:
        """Check if probe is registered."""
        return name in self.probes
