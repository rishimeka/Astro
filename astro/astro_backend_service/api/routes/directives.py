"""Directives router - CRUD for directives."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from astro_backend_service.api.dependencies import get_foundry
from astro_backend_service.api.schemas import (
    DirectiveCreate,
    DirectiveUpdate,
    DirectiveSummary,
    DirectiveResponse,
)
from astro_backend_service.foundry import Foundry, ValidationError
from astro_backend_service.models import Directive

router = APIRouter()


@router.get("", response_model=List[DirectiveSummary])
async def list_directives(
    foundry: Foundry = Depends(get_foundry),
) -> List[DirectiveSummary]:
    """List all directives."""
    directives = foundry.list_directives()
    return [
        DirectiveSummary(
            id=d.id,
            name=d.name,
            description=d.description,
            tags=d.metadata.get("tags", []),
        )
        for d in directives
    ]


@router.get("/{id}", response_model=Directive)
async def get_directive(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> Directive:
    """Get a directive by ID."""
    directive = foundry.get_directive(id)
    if directive is None:
        raise HTTPException(status_code=404, detail=f"Directive '{id}' not found")
    return directive


@router.post("", response_model=DirectiveResponse, status_code=status.HTTP_201_CREATED)
async def create_directive(
    request: DirectiveCreate,
    foundry: Foundry = Depends(get_foundry),
) -> DirectiveResponse:
    """Create a new directive."""
    directive = Directive(
        id=request.id,
        name=request.name,
        description=request.description,
        content=request.content,
        metadata=request.metadata,
    )
    try:
        created, warnings = await foundry.create_directive(directive)
        return DirectiveResponse(
            directive=created.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=DirectiveResponse)
async def update_directive(
    id: str,
    request: DirectiveUpdate,
    foundry: Foundry = Depends(get_foundry),
) -> DirectiveResponse:
    """Update a directive."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated, warnings = await foundry.update_directive(id, updates)
        return DirectiveResponse(
            directive=updated.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_directive(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> None:
    """Delete a directive."""
    try:
        deleted = await foundry.delete_directive(id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Directive '{id}' not found")
    except ValidationError as e:
        if "referenced by" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
