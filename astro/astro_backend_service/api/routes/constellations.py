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
    """Execute a constellation with SSE streaming."""
    logger.info(f"Run request for constellation: {id}")
    # Verify constellation exists
    constellation = foundry.get_constellation(id)
    if constellation is None:
        logger.debug(f"Constellation not found for run: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")

    async def event_generator():
        """Generate SSE events during execution."""
        queue: asyncio.Queue[Dict[str, Any] | None] = asyncio.Queue()

        async def execute():
            """Execute constellation and emit events."""
            try:
                logger.debug(f"Starting execution of constellation: {id}")
                # Emit run started
                await queue.put(
                    {
                        "event": "run_started",
                        "data": {"run_id": "pending", "status": "running"},
                    }
                )

                # Run the constellation
                run = await runner.run(
                    constellation_id=id,
                    variables=request.variables,
                    original_query=request.variables.get("_query", ""),
                )
                logger.info(f"Constellation {id} execution completed: run_id={run.id}, status={run.status}")

                # Emit node events
                for node_id, node_output in run.node_outputs.items():
                    if node_output.status == "completed":
                        await queue.put(
                            {
                                "event": "node_completed",
                                "data": {
                                    "node_id": node_id,
                                    "status": "completed",
                                    "output": node_output.output,
                                },
                            }
                        )
                    elif node_output.status == "failed":
                        await queue.put(
                            {
                                "event": "node_failed",
                                "data": {
                                    "node_id": node_id,
                                    "status": "failed",
                                    "error": node_output.error,
                                },
                            }
                        )

                # Emit final event based on status
                if run.status == "completed":
                    await queue.put(
                        {
                            "event": "run_completed",
                            "data": {
                                "run_id": run.id,
                                "status": "completed",
                                "final_output": run.final_output,
                            },
                        }
                    )
                elif run.status == "awaiting_confirmation":
                    await queue.put(
                        {
                            "event": "awaiting_confirmation",
                            "data": {
                                "run_id": run.id,
                                "node_id": run.awaiting_node_id,
                                "prompt": run.awaiting_prompt,
                            },
                        }
                    )
                elif run.status == "failed":
                    await queue.put(
                        {
                            "event": "run_failed",
                            "data": {
                                "run_id": run.id,
                                "status": "failed",
                                "error": run.error,
                            },
                        }
                    )

            except Exception as e:
                logger.error(f"Error executing constellation {id}: {e}", exc_info=True)
                await queue.put(
                    {
                        "event": "run_failed",
                        "data": {"error": str(e)},
                    }
                )
            finally:
                await queue.put(None)  # Signal end

        # Start execution in background
        asyncio.create_task(execute())

        # Stream events
        while True:
            event = await queue.get()
            if event is None:
                break
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())
