"""Probes router - read-only access to registered probes."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from astro_api.dependencies import get_registry
from astro_api.schemas import ProbeResponse
from astro.core.registry import Registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[ProbeResponse])
async def list_probes(
    foundry: Registry = Depends(get_registry),
) -> List[ProbeResponse]:
    """List all registered probes."""
    logger.debug("Listing all probes")
    probes = foundry.list_probes()
    logger.debug(f"Found {len(probes)} probes")
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
    foundry: Registry = Depends(get_registry),
) -> ProbeResponse:
    """Get a probe by name."""
    logger.debug(f"Getting probe: {name}")
    probe = foundry.get_probe(name)
    if probe is None:
        logger.debug(f"Probe not found: {name}")
        raise HTTPException(status_code=404, detail=f"Probe '{name}' not found")
    return ProbeResponse(
        name=probe.name,
        description=probe.description,
        parameters=probe.parameters,
    )
