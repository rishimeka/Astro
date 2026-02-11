"""Stars router - CRUD for stars."""

import logging

from astro.orchestration.models.star_types import StarType
from astro.orchestration.stars import (
    DocExStar,
    EvalStar,
    ExecutionStar,
    PlanningStar,
    SynthesisStar,
    WorkerStar,
)
from astro.orchestration.stars.base import BaseStar
from fastapi import APIRouter, Depends, HTTPException, status

from astro_api.dependencies import get_orchestration_storage
from astro_api.schemas import (
    StarCreate,
    StarResponse,
    StarSummary,
    StarUpdate,
)

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


@router.get("", response_model=list[StarSummary])
async def list_stars(
    storage = Depends(get_orchestration_storage),
) -> list[StarSummary]:
    """List all stars."""
    logger.debug("Listing all stars")
    stars = await storage.list_stars()
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
    storage = Depends(get_orchestration_storage),
) -> BaseStar:
    """Get a star by ID."""
    logger.debug(f"Getting star: {id}")
    star = await storage.get_star(id)
    if star is None:
        logger.debug(f"Star not found: {id}")
        raise HTTPException(status_code=404, detail=f"Star '{id}' not found")
    return star


@router.post("", response_model=StarResponse, status_code=status.HTTP_201_CREATED)
async def create_star(
    request: StarCreate,
    storage = Depends(get_orchestration_storage),
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
        created = await storage.save_star(star)
        logger.info(f"Star created: {created.id}")
        return StarResponse(
            star=created.model_dump(),
            warnings=[],  # OrchestrationStorage doesn't return warnings
        )
    except Exception as e:
        logger.warning(f"Error creating star {request.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=StarResponse)
async def update_star(
    id: str,
    request: StarUpdate,
    storage = Depends(get_orchestration_storage),
) -> StarResponse:
    """Update a star."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        logger.debug(f"Update star {id}: no fields to update")
        raise HTTPException(status_code=400, detail="No fields to update")

    logger.info(f"Updating star: {id}, fields={list(updates.keys())}")

    # Get existing star
    existing = await storage.get_star(id)
    if not existing:
        logger.debug(f"Star not found for update: {id}")
        raise HTTPException(status_code=404, detail=f"Star '{id}' not found")

    # Apply updates
    for key, value in updates.items():
        setattr(existing, key, value)

    try:
        updated = await storage.save_star(existing)
        logger.info(f"Star updated: {id}")
        return StarResponse(
            star=updated.model_dump(),
            warnings=[],
        )
    except Exception as e:
        logger.warning(f"Error updating star {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star(
    id: str,
    storage = Depends(get_orchestration_storage),
) -> None:
    """Delete a star."""
    logger.info(f"Deleting star: {id}")
    try:
        deleted = await storage.delete_star(id)
        if not deleted:
            logger.debug(f"Star not found for deletion: {id}")
            raise HTTPException(status_code=404, detail=f"Star '{id}' not found")
        logger.info(f"Star deleted: {id}")
    except Exception as e:
        logger.warning(f"Error deleting star {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
