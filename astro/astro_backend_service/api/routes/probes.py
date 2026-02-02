"""Probes router - read-only access to registered probes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from astro_backend_service.api.dependencies import get_foundry
from astro_backend_service.api.schemas import ProbeResponse
from astro_backend_service.foundry import Foundry

router = APIRouter()


@router.get("", response_model=List[ProbeResponse])
async def list_probes(
    foundry: Foundry = Depends(get_foundry),
) -> List[ProbeResponse]:
    """List all registered probes."""
    probes = foundry.list_probes()
    return [
        ProbeResponse(
            name=p.name,
            description=p.description,
            parameters=p.parameters,
        )
        for p in probes
    ]


@router.get("/{name}", response_model=ProbeResponse)
async def get_probe(
    name: str,
    foundry: Foundry = Depends(get_foundry),
) -> ProbeResponse:
    """Get a probe by name."""
    probe = foundry.get_probe(name)
    if probe is None:
        raise HTTPException(status_code=404, detail=f"Probe '{name}' not found")
    return ProbeResponse(
        name=probe.name,
        description=probe.description,
        parameters=probe.parameters,
    )
