"""Stars router - CRUD for stars."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from astro_backend_service.api.dependencies import get_foundry
from astro_backend_service.api.schemas import (
    StarCreate,
    StarUpdate,
    StarSummary,
    StarResponse,
)
from astro_backend_service.foundry import Foundry, ValidationError
from astro_backend_service.models import (
    WorkerStar,
    PlanningStar,
    EvalStar,
    SynthesisStar,
    ExecutionStar,
    DocExStar,
    StarType,
)
from astro_backend_service.models.stars.base import BaseStar

logger = logging.getLogger(__name__)

router = APIRouter()


# Star type to class mapping
STAR_TYPE_CLASSES = {
    StarType.WORKER: WorkerStar,
    StarType.PLANNING: PlanningStar,
    StarType.EVAL: EvalStar,
    StarType.SYNTHESIS: SynthesisStar,
    StarType.EXECUTION: ExecutionStar,
    StarType.DOCEX: DocExStar,
}


@router.get("", response_model=List[StarSummary])
async def list_stars(
    foundry: Foundry = Depends(get_foundry),
) -> List[StarSummary]:
    """List all stars."""
    logger.debug("Listing all stars")
    stars = foundry.list_stars()
    logger.debug(f"Found {len(stars)} stars")
    return [
        StarSummary(
            id=s.id,
            name=s.name,
            type=s.type,
            directive_id=s.directive_id,
        )
        for s in stars
    ]


@router.get("/{id}")
async def get_star(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> BaseStar:
    """Get a star by ID."""
    logger.debug(f"Getting star: {id}")
    star = foundry.get_star(id)
    if star is None:
        logger.debug(f"Star not found: {id}")
        raise HTTPException(status_code=404, detail=f"Star '{id}' not found")
    return star


@router.post("", response_model=StarResponse, status_code=status.HTTP_201_CREATED)
async def create_star(
    request: StarCreate,
    foundry: Foundry = Depends(get_foundry),
) -> StarResponse:
    """Create a new star."""
    logger.info(f"Creating star: id={request.id}, name={request.name}, type={request.type}")
    star_class = STAR_TYPE_CLASSES.get(request.type)
    if star_class is None:
        logger.warning(f"Unknown star type: {request.type}")
        raise HTTPException(
            status_code=400, detail=f"Unknown star type: {request.type}"
        )

    star = star_class(
        id=request.id,
        name=request.name,
        directive_id=request.directive_id,
        probe_ids=request.probe_ids if hasattr(star_class, "probe_ids") else [],
        config=request.config,
        metadata=request.metadata,
    )

    try:
        created, warnings = await foundry.create_star(star)
        logger.info(f"Star created: {created.id} with {len(warnings)} warnings")
        return StarResponse(
            star=created.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        logger.warning(f"Validation error creating star {request.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=StarResponse)
async def update_star(
    id: str,
    request: StarUpdate,
    foundry: Foundry = Depends(get_foundry),
) -> StarResponse:
    """Update a star."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        logger.debug(f"Update star {id}: no fields to update")
        raise HTTPException(status_code=400, detail="No fields to update")

    logger.info(f"Updating star: {id}, fields={list(updates.keys())}")
    try:
        updated, warnings = await foundry.update_star(id, updates)
        logger.info(f"Star updated: {id} with {len(warnings)} warnings")
        return StarResponse(
            star=updated.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        if "not found" in str(e).lower():
            logger.debug(f"Star not found for update: {id}")
            raise HTTPException(status_code=404, detail=str(e))
        logger.warning(f"Validation error updating star {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> None:
    """Delete a star."""
    logger.info(f"Deleting star: {id}")
    try:
        deleted = await foundry.delete_star(id)
        if not deleted:
            logger.debug(f"Star not found for deletion: {id}")
            raise HTTPException(status_code=404, detail=f"Star '{id}' not found")
        logger.info(f"Star deleted: {id}")
    except ValidationError as e:
        if "referenced by" in str(e).lower():
            logger.warning(f"Cannot delete star {id}: still referenced")
            raise HTTPException(status_code=409, detail=str(e))
        logger.warning(f"Validation error deleting star {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
