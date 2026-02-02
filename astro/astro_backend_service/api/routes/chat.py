"""Chat router - conversational interface wired to TriggeringAgent."""

import asyncio
import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from astro_backend_service.api.dependencies import (
    get_triggering_agent,
    get_conversation,
    create_conversation,
)
from astro_backend_service.api.schemas import ChatRequest
from astro_backend_service.executor import (
    AsyncQueueStream,
    StreamEvent,
    serialize_event_dict,
)
from astro_backend_service.launchpad import TriggeringAgent

router = APIRouter()


def sse_event(event_type: str, data: dict) -> str:
    """Format an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def stream_event_to_sse(event: StreamEvent) -> str:
    """Convert a StreamEvent to SSE format."""
    data = serialize_event_dict(event)
    return f"event: {event.event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    request: ChatRequest,
    agent: TriggeringAgent,
) -> AsyncGenerator[str, None]:
    """Stream chat response as SSE events with real-time execution updates."""
    # Get or create conversation
    if request.conversation_id:
        conversation = get_conversation(request.conversation_id)
        conversation_id = request.conversation_id
    else:
        conversation_id, conversation = create_conversation()

    # Send conversation_id first
    yield sse_event("conversation_id", {"conversation_id": conversation_id})

    # Create stream for real-time events
    stream = AsyncQueueStream()

    # Track if we've received execution events
    execution_started = False
    final_response: Optional[str] = None
    run_id: Optional[str] = None
    constellation_id: Optional[str] = None

    async def process_message():
        """Process message and put result when done."""
        nonlocal final_response, run_id, constellation_id
        try:
            response = await agent.process_message(
                message=request.message,
                conversation=conversation,
                stream=stream,
            )
            final_response = response.response
            run_id = response.run_id
            constellation_id = response.constellation_id
        except Exception as e:
            # Emit error through stream
            from astro_backend_service.executor.events import LogEvent

            await stream.emit(
                LogEvent(
                    run_id="error",
                    level="error",
                    message=str(e),
                )
            )
        finally:
            await stream.close()

    # Start processing in background
    process_task = asyncio.create_task(process_message())

    try:
        # Stream events as they come
        async for event in stream:
            execution_started = True
            yield stream_event_to_sse(event)

            # If this is a run_started event, also send in legacy format for compatibility
            if event.event_type == "run_started":
                yield sse_event(
                    "run_started",
                    {
                        "run_id": event.run_id,
                        "constellation_name": getattr(event, "constellation_name", ""),
                    },
                )

        # Wait for processing to complete
        await process_task

        # Send the final response
        if final_response:
            # If a constellation was invoked, send run info
            if run_id and constellation_id:
                constellation = agent.foundry.get_constellation(constellation_id)
                constellation_name = (
                    constellation.name if constellation else constellation_id
                )

                # Only send run_started if we didn't already from stream events
                if not execution_started:
                    yield sse_event(
                        "run_started",
                        {
                            "run_id": run_id,
                            "constellation_name": constellation_name,
                        },
                    )

            # Stream the response text as tokens
            words = final_response.split(" ")
            for i, word in enumerate(words):
                # Add space before word (except first)
                token = word if i == 0 else " " + word
                yield sse_event("token", {"token": token})
                # Small delay to simulate streaming
                await asyncio.sleep(0.02)

            # If there was a run, send run_completed
            if run_id:
                yield sse_event("run_completed", {"run_id": run_id})

        # Send done event
        yield sse_event("done", {})

    except Exception as e:
        yield sse_event("error", {"message": str(e)})
        yield sse_event("done", {})
    finally:
        # Ensure task is cancelled if we exit early
        if not process_task.done():
            process_task.cancel()
            try:
                await process_task
            except asyncio.CancelledError:
                pass


@router.post("")
async def chat(
    request: ChatRequest,
    agent: TriggeringAgent = Depends(get_triggering_agent),
) -> StreamingResponse:
    """Process a chat message through the TriggeringAgent with SSE streaming."""
    return StreamingResponse(
        stream_chat_response(request, agent),
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
    agent: TriggeringAgent = Depends(get_triggering_agent),
) -> StreamingResponse:
    """Start a new conversation with SSE streaming."""
    # Force new conversation by clearing conversation_id
    request_copy = ChatRequest(message=request.message, conversation_id=None)
    return StreamingResponse(
        stream_chat_response(request_copy, agent),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
