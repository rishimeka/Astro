"""ProbeRegistry for managing registered probes."""

from typing import ClassVar, Dict, List, Optional

from astro_backend_service.probes.exceptions import DuplicateProbeError
from astro_backend_service.probes.probe import Probe


class ProbeRegistry:
    """Global registry for probes.

    Probes are registered automatically when decorated with @probe.
    The registry provides lookup by name and enumeration of all probes.
    """

    _probes: ClassVar[Dict[str, Probe]] = {}

    @classmethod
    def register(cls, probe: Probe) -> None:
        """Register a probe. Fails immediately on duplicate name.

        Args:
            probe: The Probe instance to register.

        Raises:
            DuplicateProbeError: If probe name already registered.
        """
        if probe.name in cls._probes:
            existing = cls._probes[probe.name]
            raise DuplicateProbeError(
                f"Probe '{probe.name}' already registered.\n"
                f"  Existing: {existing.module_path}:{existing.function_name}\n"
                f"  Duplicate: {probe.module_path}:{probe.function_name}\n"
                "Each probe must have a unique name."
            )
        cls._probes[probe.name] = probe

    @classmethod
    def get(cls, name: str) -> Optional[Probe]:
        """Get a probe by name.

        Args:
            name: The probe name to look up.

        Returns:
            The Probe instance if found, None otherwise.
        """
        return cls._probes.get(name)

    @classmethod
    def all(cls) -> List[Probe]:
        """Get all registered probes.

        Returns:
            List of all registered Probe instances.
        """
        return list(cls._probes.values())

    @classmethod
    def count(cls) -> int:
        """Get the number of registered probes.

        Returns:
            The count of registered probes.
        """
        return len(cls._probes)

    @classmethod
    def clear(cls) -> None:
        """Clear the registry. Useful for testing."""
        cls._probes = {}
