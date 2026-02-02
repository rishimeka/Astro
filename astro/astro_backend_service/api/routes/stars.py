"""Stars router - CRUD for stars."""

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
    stars = foundry.list_stars()
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
    star = foundry.get_star(id)
    if star is None:
        raise HTTPException(status_code=404, detail=f"Star '{id}' not found")
    return star


@router.post("", response_model=StarResponse, status_code=status.HTTP_201_CREATED)
async def create_star(
    request: StarCreate,
    foundry: Foundry = Depends(get_foundry),
) -> StarResponse:
    """Create a new star."""
    star_class = STAR_TYPE_CLASSES.get(request.type)
    if star_class is None:
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
        return StarResponse(
            star=created.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
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
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated, warnings = await foundry.update_star(id, updates)
        return StarResponse(
            star=updated.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> None:
    """Delete a star."""
    try:
        deleted = await foundry.delete_star(id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Star '{id}' not found")
    except ValidationError as e:
        if "referenced by" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
