from __future__ import annotations

from typing import Dict, List, Any
from .probes.probe_base import Probe


class ProbeRegistrationError(Exception):
    pass


class ProbeBay:
    """Registry for probes. Register probes and run them by id.

    Usage:
        bay = ProbeBay()
        bay.register(my_probe)
        await bay.run('foundry.list_stars')
    """

    def __init__(self) -> None:
        self._probes: Dict[str, Probe] = {}

    def register(self, probe: Probe) -> None:
        if probe.id in self._probes:
            raise ProbeRegistrationError(f"Probe already registered: {probe.id}")
        self._probes[probe.id] = probe

    def list_probes(self) -> List[Dict[str, str]]:
        return [{"id": p.id, "description": getattr(p, "description", "")} for p in self._probes.values()]

    def get(self, probe_id: str) -> Probe | None:
        return self._probes.get(probe_id)

    async def run(self, probe_id: str, **kwargs: Any):
        probe = self.get(probe_id)
        if not probe:
            raise KeyError(f"Unknown probe: {probe_id}")
        return await probe.run(**kwargs)
