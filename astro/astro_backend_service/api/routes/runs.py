"""Runs router - run history and confirmation endpoints."""

import asyncio
import json
from typing import Any, AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from astro_backend_service.api.dependencies import get_foundry, get_runner
from astro_backend_service.api.schemas import (
    RunSummary,
    RunResponse,
    NodeOutputResponse,
    ConfirmRequest,
    ConfirmResponse,
)
from astro_backend_service.foundry import Foundry
from astro_backend_service.executor import ConstellationRunner

router = APIRouter()


def sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.get("", response_model=List[RunSummary])
async def list_runs(
    constellation_id: str | None = None,
    foundry: Foundry = Depends(get_foundry),
) -> List[RunSummary]:
    """List past runs, optionally filtered by constellation."""
    runs = await foundry.list_runs(constellation_id)
    return [
        RunSummary(
            id=r["id"],
            constellation_id=r["constellation_id"],
            constellation_name=r["constellation_name"],
            status=r["status"],
            started_at=r["started_at"],
            completed_at=r.get("completed_at"),
        )
        for r in runs
    ]


@router.get("/{id}", response_model=RunResponse)
async def get_run(
    id: str,
    foundry: Foundry = Depends(get_foundry),
) -> RunResponse:
    """Get a run by ID."""
    run = await foundry.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    # Build node output responses
    node_outputs = {}
    for node_id, output in run.get("node_outputs", {}).items():
        if isinstance(output, dict):
            node_outputs[node_id] = NodeOutputResponse(
                node_id=output.get("node_id", node_id),
                star_id=output.get("star_id", ""),
                status=output.get("status", "pending"),
                started_at=output.get("started_at"),
                completed_at=output.get("completed_at"),
                output=output.get("output"),
                error=output.get("error"),
                tool_calls=output.get("tool_calls", []),
            )

    return RunResponse(
        id=run["id"],
        constellation_id=run["constellation_id"],
        constellation_name=run["constellation_name"],
        status=run["status"],
        variables=run.get("variables", {}),
        started_at=run["started_at"],
        completed_at=run.get("completed_at"),
        node_outputs=node_outputs,
        final_output=run.get("final_output"),
        error=run.get("error"),
        awaiting_node_id=run.get("awaiting_node_id"),
        awaiting_prompt=run.get("awaiting_prompt"),
    )


@router.get("/{id}/nodes/{node_id}", response_model=NodeOutputResponse)
async def get_node_output(
    id: str,
    node_id: str,
    foundry: Foundry = Depends(get_foundry),
) -> NodeOutputResponse:
    """Get output for a specific node in a run."""
    run = await foundry.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    node_outputs = run.get("node_outputs", {})
    output = node_outputs.get(node_id)
    if output is None:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found in run '{id}'",
        )

    if isinstance(output, dict):
        return NodeOutputResponse(
            node_id=output.get("node_id", node_id),
            star_id=output.get("star_id", ""),
            status=output.get("status", "pending"),
            started_at=output.get("started_at"),
            completed_at=output.get("completed_at"),
            output=output.get("output"),
            error=output.get("error"),
            tool_calls=output.get("tool_calls", []),
        )

    raise HTTPException(status_code=500, detail="Invalid node output format")


@router.post("/{id}/confirm", response_model=ConfirmResponse)
async def confirm_run(
    id: str,
    request: ConfirmRequest,
    foundry: Foundry = Depends(get_foundry),
    runner: ConstellationRunner = Depends(get_runner),
) -> ConfirmResponse:
    """Confirm or cancel a paused run."""
    run = await foundry.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    if run.get("status") != "awaiting_confirmation":
        raise HTTPException(
            status_code=400,
            detail=f"Run is not awaiting confirmation (status: {run.get('status')})",
        )

    if request.proceed:
        # Resume execution
        try:
            await runner.resume_run(id, additional_context=request.additional_context)
            return ConfirmResponse(
                run_id=id,
                status="running",
                message="Execution resumed",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Cancel execution
        await runner.cancel_run(id)
        return ConfirmResponse(
            run_id=id,
            status="cancelled",
            message="Execution cancelled by user",
        )


async def stream_run_status(
    run_id: str,
    foundry: Foundry,
) -> AsyncGenerator[str, None]:
    """Stream run status updates as SSE events."""
    last_status = None
    last_node_outputs: dict[str, Any] = {}

    # Poll for updates (in a real implementation, this would use pub/sub)
    while True:
        run = await foundry.get_run(run_id)
        if run is None:
            yield sse_event("run_failed", {"error": "Run not found"})
            break

        current_status = run.get("status")
        node_outputs = run.get("node_outputs", {})

        # Send status change
        if current_status != last_status:
            if current_status == "running":
                yield sse_event("run_started", {"run_id": run_id})
            elif current_status == "completed":
                yield sse_event(
                    "run_completed",
                    {
                        "run_id": run_id,
                        "final_output": run.get("final_output") or "",
                    },
                )
                break
            elif current_status == "failed":
                yield sse_event(
                    "run_failed",
                    {
                        "run_id": run_id,
                        "error": run.get("error") or "Unknown error",
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
                        "node_id": run.get("awaiting_node_id"),
                        "prompt": run.get("awaiting_prompt")
                        or "Please confirm to proceed",
                    },
                )
            last_status = current_status

        # Send node updates
        for node_id, output in node_outputs.items():
            if isinstance(output, dict):
                prev_output = last_node_outputs.get(node_id, {})
                prev_status = (
                    prev_output.get("status") if isinstance(prev_output, dict) else None
                )
                curr_status = output.get("status")

                if curr_status != prev_status:
                    if curr_status == "running":
                        yield sse_event(
                            "node_started",
                            {
                                "node_id": node_id,
                                "star_id": output.get("star_id", ""),
                            },
                        )
                    elif curr_status == "completed":
                        yield sse_event(
                            "node_completed",
                            {
                                "node_id": node_id,
                                "output": output.get("output") or "",
                            },
                        )
                    elif curr_status == "failed":
                        yield sse_event(
                            "node_failed",
                            {
                                "node_id": node_id,
                                "error": output.get("error") or "Unknown error",
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
    foundry: Foundry = Depends(get_foundry),
) -> StreamingResponse:
    """Stream run execution status via SSE."""
    # Verify run exists
    run = await foundry.get_run(id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{id}' not found")

    return StreamingResponse(
        stream_run_status(id, foundry),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
