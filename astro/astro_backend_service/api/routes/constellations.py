"""Constellations router - CRUD and execution endpoints."""

import asyncio
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from astro_backend_service.api.dependencies import get_foundry, get_runner

logger = logging.getLogger(__name__)
from astro_backend_service.api.schemas import (
    ConstellationCreate,
    ConstellationUpdate,
    ConstellationSummary,
    ConstellationResponse,
    RunRequest,
)
from astro_backend_service.foundry import Foundry, ValidationError
from astro_backend_service.executor import ConstellationRunner
from astro_backend_service.models import (
    Constellation,
    Position,
    StartNode,
    EndNode,
    StarNode,
    Edge,
    TemplateVariable,
)

router = APIRouter()


def _build_constellation(request: ConstellationCreate) -> Constellation:
    """Build a Constellation model from create request."""
    # Build start node
    start_data = request.start
    start = StartNode(
        id=start_data.get("id", "start"),
        position=Position(**start_data.get("position", {"x": 0, "y": 0})),
    )

    # Build end node
    end_data = request.end
    end = EndNode(
        id=end_data.get("id", "end"),
        position=Position(**end_data.get("position", {"x": 500, "y": 0})),
    )

    # Build star nodes
    nodes = []
    for node_data in request.nodes:
        node = StarNode(
            id=node_data["id"],
            star_id=node_data["star_id"],
            position=Position(**node_data.get("position", {"x": 0, "y": 0})),
            display_name=node_data.get("display_name"),
            requires_confirmation=node_data.get("requires_confirmation", False),
            confirmation_prompt=node_data.get("confirmation_prompt"),
        )
        nodes.append(node)

    # Build edges
    edges = []
    for edge_data in request.edges:
        edge = Edge(
            id=edge_data["id"],
            source=edge_data["source"],
            target=edge_data["target"],
            condition=edge_data.get("condition"),
        )
        edges.append(edge)

    return Constellation(
        id=request.id,
        name=request.name,
        description=request.description,
        start=start,
        end=end,
        nodes=nodes,
        edges=edges,
        max_loop_iterations=request.max_loop_iterations,
        max_retry_attempts=request.max_retry_attempts,
        retry_delay_base=request.retry_delay_base,
        metadata=request.metadata,
    )


@router.get("", response_model=List[ConstellationSummary])
async def list_constellations(
    foundry: Foundry = Depends(get_foundry),
) -> List[ConstellationSummary]:
    """List all constellations."""
    logger.debug("Listing all constellations")
    constellations = foundry.list_constellations()
    logger.debug(f"Found {len(constellations)} constellations")
    return [
        ConstellationSummary(
            id=c.id,
            name=c.name,
            description=c.description,
            node_count=len(c.nodes),
            tags=c.metadata.get("tags", []),
        )
        for c in constellations
    ]


@router.get("/{id}", response_model=Constellation)
async def get_constellation(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> Constellation:
    """Get a constellation by ID."""
    logger.debug(f"Getting constellation: {id}")
    constellation = foundry.get_constellation(id)
    if constellation is None:
        logger.debug(f"Constellation not found: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")
    return constellation


@router.get("/{id}/variables", response_model=List[TemplateVariable])
async def get_constellation_variables(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> List[TemplateVariable]:
    """Get required variables for a constellation."""
    try:
        variables = foundry.compute_constellation_variables(id)
        return variables
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "", response_model=ConstellationResponse, status_code=status.HTTP_201_CREATED
)
async def create_constellation(
    request: ConstellationCreate,
    foundry: Foundry = Depends(get_foundry),
) -> ConstellationResponse:
    """Create a new constellation."""
    logger.info(f"Creating constellation: id={request.id}, name={request.name}")
    constellation = _build_constellation(request)

    try:
        created, warnings = await foundry.create_constellation(constellation)
        logger.info(f"Constellation created: {created.id} with {len(warnings)} warnings")
        return ConstellationResponse(
            constellation=created.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        logger.warning(f"Validation error creating constellation {request.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=ConstellationResponse)
async def update_constellation(
    id: str,
    request: ConstellationUpdate,
    foundry: Foundry = Depends(get_foundry),
) -> ConstellationResponse:
    """Update a constellation."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        logger.debug(f"Update constellation {id}: no fields to update")
        raise HTTPException(status_code=400, detail="No fields to update")

    logger.info(f"Updating constellation: {id}, fields={list(updates.keys())}")
    try:
        updated, warnings = await foundry.update_constellation(id, updates)
        logger.info(f"Constellation updated: {id} with {len(warnings)} warnings")
        return ConstellationResponse(
            constellation=updated.model_dump(),
            warnings=[w.message for w in warnings],
        )
    except ValidationError as e:
        if "not found" in str(e).lower():
            logger.debug(f"Constellation not found for update: {id}")
            raise HTTPException(status_code=404, detail=str(e))
        logger.warning(f"Validation error updating constellation {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_constellation(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> None:
    """Delete a constellation."""
    logger.info(f"Deleting constellation: {id}")
    deleted = await foundry.delete_constellation(id)
    if not deleted:
        logger.debug(f"Constellation not found for deletion: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")
    logger.info(f"Constellation deleted: {id}")


@router.post("/{id}/run")
async def run_constellation(
    id: str,
    request: RunRequest,
    foundry: Foundry = Depends(get_foundry),
    runner: ConstellationRunner = Depends(get_runner),
):
    """Execute a constellation in the background and return run ID immediately.

    This endpoint starts the constellation execution and returns the run ID right away,
    allowing other requests to be processed concurrently. Use GET /runs/{run_id}/stream
    to monitor the execution progress via SSE.
    """
    from astro_backend_service.executor.runner import generate_run_id

    logger.info(f"Run request for constellation: {id}")
    # Verify constellation exists
    constellation = foundry.get_constellation(id)
    if constellation is None:
        logger.debug(f"Constellation not found for run: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")

    # Generate run ID upfront
    run_id = generate_run_id()

    # Start execution in background task - do NOT await
    async def execute_in_background():
        """Execute constellation in the background."""
        try:
            logger.debug(f"Starting background execution of constellation: {id}, run_id: {run_id}")
            await runner.run(
                constellation_id=id,
                variables=request.variables,
                original_query=request.variables.get("_query", ""),
                run_id=run_id,
            )
            logger.info(f"Background execution completed: run_id={run_id}")
        except Exception as e:
            logger.error(f"Error in background execution for constellation {id}: {e}", exc_info=True)

    # Start the task but don't wait for it
    asyncio.create_task(execute_in_background())

    # Return immediately with the run ID
    # The client should use /runs/{run_id}/stream to monitor progress
    return {
        "run_id": run_id,
        "constellation_id": id,
        "constellation_name": constellation.name,
        "status": "started",
        "message": f"Execution started in background. Use GET /runs/{run_id}/stream to monitor progress.",
    }
