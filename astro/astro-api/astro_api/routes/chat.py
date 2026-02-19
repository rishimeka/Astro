"""Chat router - conversational interface wired to LaunchpadController (V2)."""

import asyncio
import json
import logging
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

from astro.core.file_processing import format_file_context_for_llm, process_file
from astro.launchpad import LaunchpadController, Response
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from astro_api.dependencies import (
    create_conversation,
    get_conversation,
    get_launchpad_controller,
)
from astro_api.schemas import ChatRequest

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

                elif event_type == "clarification_needed":
                    # Stream the questions as message content first
                    questions = event.get("questions", [])
                    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
                    response_text = f"I need more information to help you:\n\n{questions_text}"

                    words = response_text.split(" ")
                    for i, word in enumerate(words):
                        token = word if i == 0 else " " + word
                        yield sse_event("token", {"token": token})
                        await asyncio.sleep(0.02)

                    # Then send clarification request for the interactive card
                    yield sse_event("clarification_needed", {
                        "questions": event.get("questions", []),
                        "reasoning": event.get("reasoning", ""),
                        "round": event.get("round", 1),
                        "max_rounds": event.get("max_rounds", 3),
                    })
                    # Pipeline returned early waiting for user response
                    # Send done event and exit
                    yield sse_event("done", {})
                    return

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
    message: str = Form(...),
    conversation_id: str | None = Form(None),
    file: UploadFile | None = File(None),
    research_mode: bool = Query(
        default=False,
        description="Use constellation mode for thorough research (slower)",
    ),
    controller: LaunchpadController = Depends(get_launchpad_controller),
) -> StreamingResponse:
    """Process a chat message through the LaunchpadController with SSE streaming.

    Accepts optional file upload:
    - Excel files (.xlsx, .xls) are parsed into JSON
    - PDF files are made available to the model for native processing
    - Images are processed for vision capabilities

    Args:
        message: The chat message text
        conversation_id: Optional conversation ID to continue existing conversation
        file: Optional file upload
        research_mode: If True, use constellation pipeline. If False, use zero-shot.
        controller: LaunchpadController dependency.

    Returns:
        StreamingResponse with SSE events.
    """
    # Process file if provided
    file_context = None
    if file and file.filename:
        logger.info(f"Processing uploaded file in chat: {file.filename}")
        try:
            # Save to temporary file
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Process the file
            processed = process_file(tmp_path, file.filename)

            # Format file context for LLM
            file_context = format_file_context_for_llm(processed)
            logger.info(f"File processed: {file.filename} (type: {processed.file_type})")

        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}", exc_info=True)
            # Continue without file context rather than failing

    # Add file context to message if present
    if file_context:
        message = f"{file_context}\n\n{message}"

    # Create request object
    request = ChatRequest(message=message, conversation_id=conversation_id)

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
