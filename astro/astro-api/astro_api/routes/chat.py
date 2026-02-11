"""Chat router - conversational interface wired to LaunchpadController (V2)."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from astro_api.dependencies import (
    get_launchpad_controller,
    get_conversation,
    create_conversation,
)
from astro_api.schemas import ChatRequest
from astro.launchpad import LaunchpadController, Response

logger = logging.getLogger(__name__)

router = APIRouter()


def sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    request: ChatRequest,
    controller: LaunchpadController,
    research_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream chat response as SSE events with V2 launchpad.

    Args:
        request: Chat request with message and conversation_id.
        controller: LaunchpadController for routing execution.
        research_mode: If True, use constellation mode. If False, use zero-shot mode.

    Yields:
        SSE formatted events.
    """
    # Get or create conversation
    if request.conversation_id:
        conversation = get_conversation(request.conversation_id)
        conversation_id = request.conversation_id
        logger.debug(f"Using existing conversation: {conversation_id}")
    else:
        conversation_id, conversation = create_conversation()
        logger.debug(f"Created new conversation: {conversation_id}")

    logger.info(
        f"Processing chat message: conversation={conversation_id}, "
        f"message_preview={request.message[:50]}..., research_mode={research_mode}"
    )

    # Send conversation_id first
    yield sse_event("conversation_id", {"conversation_id": conversation_id})

    # Send mode indicator
    mode = "constellation" if research_mode else "zero_shot"
    yield sse_event("mode", {"mode": mode})

    try:
        # Execute through launchpad controller with event streaming
        logger.debug(f"Starting controller.handle_message for conversation={conversation_id}")

        # Check if we can use event streaming (zero-shot mode only for now)
        if not research_mode:
            # Use zero-shot pipeline with event streaming
            from astro_api.dependencies import get_zero_shot_pipeline

            pipeline = await get_zero_shot_pipeline()

            final_output = None
            async for event in pipeline.execute_with_events(request.message, conversation):
                event_type = event.get("type")

                if event_type == "thinking":
                    # Send thinking event
                    yield sse_event("thinking", {"message": event.get("message", "")})

                elif event_type == "directive_selected":
                    # Send directive selection
                    yield sse_event("directive_selected", {
                        "directives": event.get("directive_ids", []),
                        "reasoning": event.get("reasoning", ""),
                    })

                elif event_type == "tools_bound":
                    # Send tool binding info
                    yield sse_event("tools_bound", {
                        "tools": event.get("tools", []),
                        "count": len(event.get("tools", [])),
                    })

                elif event_type == "directive_generation_offered":
                    # Send directive generation notification
                    yield sse_event("directive_generation_offered", {
                        "message": event.get("message", ""),
                    })

                elif event_type == "directive_generated":
                    # Send directive generated confirmation
                    yield sse_event("directive_generated", {
                        "directive_id": event.get("directive_id"),
                        "message": event.get("message", ""),
                    })

                elif event_type == "directive_similar_found":
                    # Send similar directive found
                    yield sse_event("directive_similar_found", {
                        "directive_id": event.get("directive_id"),
                        "similarity_score": event.get("similarity_score", 0.0),
                        "message": event.get("message", ""),
                    })

                elif event_type == "output":
                    # This is the final output
                    final_output = event.get("output")

            if not final_output:
                raise ValueError("No output received from pipeline")

            # Stream the response text as tokens
            words = final_output.content.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                yield sse_event("token", {"token": token})
                await asyncio.sleep(0.02)

            # Send metadata
            logger.info(
                f"Controller response complete: mode=zero_shot, "
                f"metadata={{'iterations': {final_output.iterations}, 'tool_calls': {len(final_output.tool_calls)}}}"
            )

        else:
            # Constellation mode - use existing logic
            response: Response = await controller.handle_message(
                message=request.message,
                conversation=conversation,
                research_mode=research_mode,
            )

            logger.info(
                f"Controller response complete: mode={response.mode}, "
                f"metadata={response.metadata}"
            )

            # Send metadata if constellation execution
            if response.mode == "constellation":
                run_id = response.metadata.get("run_id")
                constellation_name = response.metadata.get("constellation_name")

                if run_id and constellation_name:
                    yield sse_event(
                        "run_started",
                        {"run_id": run_id, "constellation_name": constellation_name},
                    )

            # Stream the response text as tokens
            words = response.content.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                yield sse_event("token", {"token": token})
                await asyncio.sleep(0.02)

            # If there was a run, send run_completed
            if response.mode == "constellation":
                run_id = response.metadata.get("run_id")
                if run_id:
                    yield sse_event("run_completed", {"run_id": run_id})

        # Send done event
        yield sse_event("done", {})

    except Exception as e:
        logger.error(
            f"Error in chat stream for conversation={conversation_id}: {e}",
            exc_info=True,
        )
        yield sse_event("error", {"message": str(e)})
        yield sse_event("done", {})


@router.post("")
async def chat(
    request: ChatRequest,
    research_mode: bool = Query(
        default=False,
        description="Use constellation mode for thorough research (slower)",
    ),
    controller: LaunchpadController = Depends(get_launchpad_controller),
) -> StreamingResponse:
    """Process a chat message through the LaunchpadController with SSE streaming.

    Args:
        request: Chat request with message and optional conversation_id.
        research_mode: If True, use constellation pipeline. If False, use zero-shot.
        controller: LaunchpadController dependency.

    Returns:
        StreamingResponse with SSE events.
    """
    return StreamingResponse(
        stream_chat_response(request, controller, research_mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/new")
async def new_conversation(
    request: ChatRequest,
    research_mode: bool = Query(
        default=False,
        description="Use constellation mode for thorough research (slower)",
    ),
    controller: LaunchpadController = Depends(get_launchpad_controller),
) -> StreamingResponse:
    """Start a new conversation with SSE streaming.

    Args:
        request: Chat request with message.
        research_mode: If True, use constellation pipeline. If False, use zero-shot.
        controller: LaunchpadController dependency.

    Returns:
        StreamingResponse with SSE events.
    """
    # Force new conversation by clearing conversation_id
    request_copy = ChatRequest(message=request.message, conversation_id=None)
    return StreamingResponse(
        stream_chat_response(request_copy, controller, research_mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
