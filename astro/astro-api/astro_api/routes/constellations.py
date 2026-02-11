"""Constellations router - CRUD and execution endpoints."""

import asyncio
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from astro_api.dependencies import get_registry, get_runner, get_orchestration_storage

logger = logging.getLogger(__name__)
from astro_api.schemas import (
    ConstellationCreate,
    ConstellationUpdate,
    ConstellationSummary,
    ConstellationResponse,
    RunRequest,
)
from astro.core.registry import Registry, ValidationError
from astro.orchestration.runner import ConstellationRunner
from astro.orchestration.models import (
    Constellation,
    Position,
    StartNode,
    EndNode,
    StarNode,
    Edge,
)
from astro.core.models import TemplateVariable

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
    storage = Depends(get_orchestration_storage),
) -> List[ConstellationSummary]:
    """List all constellations."""
    logger.debug("Listing all constellations")
    constellations = await storage.list_constellations()
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
    storage = Depends(get_orchestration_storage),
) -> Constellation:
    """Get a constellation by ID."""
    logger.debug(f"Getting constellation: {id}")
    constellation = await storage.get_constellation(id)
    if constellation is None:
        logger.debug(f"Constellation not found: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")
    return constellation


@router.get("/{id}/variables", response_model=List[TemplateVariable])
async def get_constellation_variables(
    id: str,
    foundry: Registry = Depends(get_registry),
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
    storage = Depends(get_orchestration_storage),
) -> ConstellationResponse:
    """Create a new constellation."""
    logger.info(f"Creating constellation: id={request.id}, name={request.name}")
    constellation = _build_constellation(request)

    try:
        created = await storage.save_constellation(constellation)
        logger.info(f"Constellation created: {created.id}")
        return ConstellationResponse(
            constellation=created.model_dump(),
            warnings=[],  # OrchestrationStorage doesn't return warnings
        )
    except Exception as e:
        logger.warning(f"Error creating constellation {request.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=ConstellationResponse)
async def update_constellation(
    id: str,
    request: ConstellationUpdate,
    storage = Depends(get_orchestration_storage),
) -> ConstellationResponse:
    """Update a constellation."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        logger.debug(f"Update constellation {id}: no fields to update")
        raise HTTPException(status_code=400, detail="No fields to update")

    logger.info(f"Updating constellation: {id}, fields={list(updates.keys())}")

    # Get existing constellation
    existing = await storage.get_constellation(id)
    if not existing:
        logger.debug(f"Constellation not found for update: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")

    # Apply updates
    for key, value in updates.items():
        setattr(existing, key, value)

    try:
        updated = await storage.save_constellation(existing)
        logger.info(f"Constellation updated: {id}")
        return ConstellationResponse(
            constellation=updated.model_dump(),
            warnings=[],
        )
    except Exception as e:
        logger.warning(f"Error updating constellation {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_constellation(
    id: str,
    storage = Depends(get_orchestration_storage),
) -> None:
    """Delete a constellation."""
    logger.info(f"Deleting constellation: {id}")
    deleted = await storage.delete_constellation(id)
    if not deleted:
        logger.debug(f"Constellation not found for deletion: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")
    logger.info(f"Constellation deleted: {id}")


@router.post("/{id}/run")
async def run_constellation(
    id: str,
    request: RunRequest,
    storage = Depends(get_orchestration_storage),
    runner: ConstellationRunner = Depends(get_runner),
):
    """Execute a constellation in the background and return run ID immediately.

    This endpoint starts the constellation execution and returns the run ID right away,
    allowing other requests to be processed concurrently. Use GET /runs/{run_id}/stream
    to monitor the execution progress via SSE.
    """
    from astro.orchestration.runner.runner import generate_run_id

    logger.info(f"Run request for constellation: {id}")
    # Verify constellation exists
    constellation = await storage.get_constellation(id)
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
