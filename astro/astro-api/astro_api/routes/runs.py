"""Runs router - run history and confirmation endpoints."""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from astro_api.dependencies import get_registry, get_runner, get_orchestration_storage

logger = logging.getLogger(__name__)
from astro_api.schemas import (
    RunSummary,
    RunResponse,
    NodeOutputResponse,
    ConfirmRequest,
    ConfirmResponse,
)
from astro.core.registry import Registry
from astro.orchestration.runner import ConstellationRunner

router = APIRouter()


def sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.get("", response_model=List[RunSummary])
async def list_runs(
    constellation_id: str | None = None,
    storage = Depends(get_orchestration_storage),
) -> List[RunSummary]:
    """List past runs, optionally filtered by constellation."""
    logger.debug(f"Listing runs: constellation_id={constellation_id}")
    runs = await storage.list_runs(constellation_id)
    logger.debug(f"Found {len(runs)} runs")
    return [
        RunSummary(
            id=r.id,
            constellation_id=r.constellation_id,
            constellation_name=r.constellation_name,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/{id}", response_model=RunResponse)
async def get_run(
    id: str,
    storage = Depends(get_orchestration_storage),
) -> RunResponse:
    """Get a run by ID."""
    run = await storage.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    # Build node output responses
    node_outputs = {}
    for node_id, output in run.node_outputs.items():
        node_outputs[node_id] = NodeOutputResponse(
            node_id=output.node_id,
            star_id=output.star_id,
            status=output.status,
            started_at=output.started_at,
            completed_at=output.completed_at,
            output=output.output,
            error=output.error,
            tool_calls=output.tool_calls,
        )

    return RunResponse(
        id=run.id,
        constellation_id=run.constellation_id,
        constellation_name=run.constellation_name,
        status=run.status,
        variables=run.variables,
        started_at=run.started_at,
        completed_at=run.completed_at,
        node_outputs=node_outputs,
        final_output=run.final_output,
        error=run.error,
        awaiting_node_id=run.awaiting_node_id,
        awaiting_prompt=run.awaiting_prompt,
    )


@router.get("/{id}/nodes/{node_id}", response_model=NodeOutputResponse)
async def get_node_output(
    id: str,
    node_id: str,
    storage = Depends(get_orchestration_storage),
) -> NodeOutputResponse:
    """Get output for a specific node in a run."""
    run = await storage.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    output = run.node_outputs.get(node_id)
    if output is None:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found in run '{id}'",
        )

    return NodeOutputResponse(
        node_id=output.node_id,
        star_id=output.star_id,
        status=output.status,
        started_at=output.started_at,
        completed_at=output.completed_at,
        output=output.output,
        error=output.error,
        tool_calls=output.tool_calls,
    )


@router.post("/{id}/confirm", response_model=ConfirmResponse)
async def confirm_run(
    id: str,
    request: ConfirmRequest,
    storage = Depends(get_orchestration_storage),
    runner: ConstellationRunner = Depends(get_runner),
) -> ConfirmResponse:
    """Confirm or cancel a paused run."""
    logger.info(f"Confirm request for run: {id}, proceed={request.proceed}")
    run = await storage.get_run(id)
    if run is None:
        logger.debug(f"Run not found: {id}")
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    if run.status != "awaiting_confirmation":
        logger.warning(f"Run {id} not awaiting confirmation, status={run.status}")
        raise HTTPException(
            status_code=400,
            detail=f"Run is not awaiting confirmation (status: {run.status})",
        )

    if request.proceed:
        # Resume execution
        try:
            logger.info(f"Resuming run: {id}")
            await runner.resume_run(id, additional_context=request.additional_context)
            return ConfirmResponse(
                run_id=id,
                status="running",
                message="Execution resumed",
            )
        except Exception as e:
            logger.error(f"Error resuming run {id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Cancel execution
        logger.info(f"Cancelling run: {id}")
        await runner.cancel_run(id)
        return ConfirmResponse(
            run_id=id,
            status="cancelled",
            message="Execution cancelled by user",
        )


async def stream_run_status(
    run_id: str,
    storage,
) -> AsyncGenerator[str, None]:
    """Stream run status updates as SSE events."""
    last_status = None
    last_node_outputs: dict[str, Any] = {}

    # Poll for updates (in a real implementation, this would use pub/sub)
    while True:
        run = await storage.get_run(run_id)
        if run is None:
            yield sse_event("run_failed", {"error": "Run not found"})
            break

        current_status = run.status
        node_outputs = run.node_outputs

        # Send status change
        if current_status != last_status:
            if current_status == "running":
                # Check if this is a resume (previous status was awaiting_confirmation)
                if last_status == "awaiting_confirmation":
                    yield sse_event("run_resumed", {"run_id": run_id})
                else:
                    yield sse_event("run_started", {"run_id": run_id})
            elif current_status == "completed":
                yield sse_event(
                    "run_completed",
                    {
                        "run_id": run_id,
                        "final_output": run.final_output or "",
                    },
                )
                break
            elif current_status == "failed":
                yield sse_event(
                    "run_failed",
                    {
                        "run_id": run_id,
                        "error": run.error or "Unknown error",
                    },
                )
                break
            elif current_status == "cancelled":
                yield sse_event(
                    "run_failed",
                    {
                        "run_id": run_id,
                        "error": "Run was cancelled",
                    },
                )
                break
            elif current_status == "awaiting_confirmation":
                yield sse_event(
                    "awaiting_confirmation",
                    {
                        "run_id": run_id,
                        "node_id": run.awaiting_node_id,
                        "prompt": run.awaiting_prompt
                        or "Please confirm to proceed",
                    },
                )
            last_status = current_status

        # Send node updates
        for node_id, output in node_outputs.items():
            prev_output = last_node_outputs.get(node_id)
            prev_status = prev_output.status if prev_output else None
            curr_status = output.status

            if curr_status != prev_status:
                if curr_status == "running":
                    yield sse_event(
                        "node_started",
                        {
                            "node_id": node_id,
                            "star_id": output.star_id,
                        },
                    )
                elif curr_status == "completed":
                    yield sse_event(
                        "node_completed",
                        {
                            "node_id": node_id,
                            "output": output.output or "",
                        },
                    )
                elif curr_status == "failed":
                    yield sse_event(
                        "node_failed",
                        {
                            "node_id": node_id,
                            "error": output.error or "Unknown error",
                        },
                    )

        last_node_outputs = node_outputs.copy()

        # For already completed runs, exit immediately
        if current_status in ("completed", "failed", "cancelled"):
            break

        # Poll interval
        await asyncio.sleep(0.5)


@router.get("/{id}/stream")
async def stream_run(
    id: str,
    storage = Depends(get_orchestration_storage),
) -> StreamingResponse:
    """Stream run execution status via SSE."""
    # Verify run exists
    run = await storage.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    return StreamingResponse(
        stream_run_status(id, storage),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
