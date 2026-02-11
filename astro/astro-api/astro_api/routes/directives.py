"""Directives router - CRUD for directives."""

import logging

from astro.core.models import Directive
from astro.core.registry import Registry, ValidationError
from fastapi import APIRouter, Depends, HTTPException, status

from astro_api.dependencies import get_registry
from astro_api.schemas import (
    DirectiveCreate,
    DirectiveResponse,
    DirectiveSummary,
    DirectiveUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[DirectiveSummary])
async def list_directives(
    foundry: Registry = Depends(get_registry),
) -> list[DirectiveSummary]:
    """List all directives."""
    logger.debug("Listing all directives")
    directives = foundry.list_directives()
    logger.debug(f"Found {len(directives)} directives")
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
    foundry: Registry = Depends(get_registry),
) -> Directive:
    """Get a directive by ID."""
    logger.debug(f"Getting directive: {id}")
    directive = foundry.get_directive(id)
    if directive is None:
        logger.debug(f"Directive not found: {id}")
        raise HTTPException(status_code=404, detail=f"Directive '{id}' not found")
    return directive


@router.post("", response_model=DirectiveResponse, status_code=status.HTTP_201_CREATED)
async def create_directive(
    request: DirectiveCreate,
    foundry: Registry = Depends(get_registry),
) -> DirectiveResponse:
    """Create a new directive."""
    logger.info(f"Creating directive: id={request.id}, name={request.name}")
    directive = Directive(
        id=request.id,
        name=request.name,
        description=request.description,
        content=request.content,
        metadata=request.metadata,
    )
    try:
        created, warnings = await foundry.create_directive(directive)
        logger.info(f"Directive created: {created.id} with {len(warnings)} warnings")
        return DirectiveResponse(
            directive=created.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        logger.warning(f"Validation error creating directive {request.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=DirectiveResponse)
async def update_directive(
    id: str,
    request: DirectiveUpdate,
    foundry: Registry = Depends(get_registry),
) -> DirectiveResponse:
    """Update a directive."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        logger.debug(f"Update directive {id}: no fields to update")
        raise HTTPException(status_code=400, detail="No fields to update")

    logger.info(f"Updating directive: {id}, fields={list(updates.keys())}")
    try:
        updated, warnings = await foundry.update_directive(id, updates)
        logger.info(f"Directive updated: {id} with {len(warnings)} warnings")
        return DirectiveResponse(
            directive=updated.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        if "not found" in str(e).lower():
            logger.debug(f"Directive not found for update: {id}")
            raise HTTPException(status_code=404, detail=str(e))
        logger.warning(f"Validation error updating directive {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_directive(
    id: str,
    foundry: Registry = Depends(get_registry),
) -> None:
    """Delete a directive."""
    logger.info(f"Deleting directive: {id}")
    try:
        deleted = await foundry.delete_directive(id)
        if not deleted:
            logger.debug(f"Directive not found for deletion: {id}")
            raise HTTPException(status_code=404, detail=f"Directive '{id}' not found")
        logger.info(f"Directive deleted: {id}")
    except ValidationError as e:
        if "referenced by" in str(e).lower():
            logger.warning(f"Cannot delete directive {id}: still referenced")
            raise HTTPException(status_code=409, detail=str(e))
        logger.warning(f"Validation error deleting directive {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
