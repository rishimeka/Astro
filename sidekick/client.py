"""Sidekick Client for emitting events.

The client is what execution code uses to emit events. It is:
- Thread-safe
- Non-blocking (fire-and-forget)
- Singleton per execution
"""

import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
import logging

from sidekick.models.events import EventType, SidekickEvent
from sidekick.config import get_config, SidekickConfig

logger = logging.getLogger(__name__)


class SidekickClient:
    """Client for emitting events to Sidekick.

    Usage:
        async with SidekickClient.create(query="...") as sidekick:
            sidekick.emit_phase_started(...)
            # ... execution code ...

    Key design principle: Never block the main execution thread.
    Events are put on a queue and processed asynchronously.
    """

    _instance: Optional["SidekickClient"] = None

    def __init__(
        self,
        trace_id: str,
        original_query: str,
        queue: asyncio.Queue,
        config: Optional[SidekickConfig] = None,
    ):
        self.trace_id = trace_id
        self.original_query = original_query
        self._queue = queue
        self._config = config or get_config()
        self._current_phase_id: Optional[str] = None
        self._current_worker_id: Optional[str] = None
        self._enabled = True

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        original_query: str,
        stars_used: Optional[List[str]] = None,
        probes_available: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        sidekick_config: Optional[SidekickConfig] = None,
    ):
        """Create a Sidekick client for an execution run.

        Starts the background processor and cleans up on exit.

        Args:
            original_query: The user's query being executed
            stars_used: List of Star IDs loaded for this execution
            probes_available: List of Probe IDs available
            config: Execution configuration dict
            sidekick_config: Optional Sidekick configuration
        """
        from sidekick.processor import SidekickProcessor

        sk_config = sidekick_config or get_config()
        trace_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue(maxsize=sk_config.max_queue_size)

        client = cls(
            trace_id=trace_id,
            original_query=original_query,
            queue=queue,
            config=sk_config,
        )
        cls._instance = client

        # Start background processor
        processor = SidekickProcessor(queue, trace_id, sk_config)
        processor_task = asyncio.create_task(processor.run())

        # Emit execution started
        client.emit_execution_started(
            stars_used=stars_used or [],
            probes_available=probes_available or [],
            config=config or {},
        )

        try:
            yield client
        finally:
            # Signal processor to stop
            await queue.put(None)  # Sentinel value
            try:
                await asyncio.wait_for(processor_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Sidekick processor did not shut down cleanly")
                processor_task.cancel()
            cls._instance = None

    @classmethod
    def get(cls) -> Optional["SidekickClient"]:
        """Get the current Sidekick client instance."""
        return cls._instance

    def disable(self) -> None:
        """Disable event emission."""
        self._enabled = False

    def enable(self) -> None:
        """Enable event emission."""
        self._enabled = True

    def _emit(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        """Emit an event to the queue.

        Non-blocking: drops event if queue is full.
        """
        if not self._enabled:
            return

        event = SidekickEvent(
            event_type=event_type,
            trace_id=self.trace_id,
            phase_id=self._current_phase_id,
            worker_id=self._current_worker_id,
            payload=payload,
        )

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop event rather than blocking
            logger.warning(f"Sidekick queue full, dropping event: {event_type}")

    # ==================== Execution-level events ====================

    def emit_execution_started(
        self,
        stars_used: List[str],
        probes_available: List[str],
        config: Dict[str, Any],
    ) -> None:
        """Emit execution started event."""
        self._emit(
            EventType.EXECUTION_STARTED,
            {
                "original_query": self.original_query,
                "stars_used": stars_used,
                "probes_available": probes_available,
                "config": config,
            },
        )

    def emit_execution_completed(
        self,
        final_output: str,
        total_duration_seconds: float,
        total_llm_calls: int,
        total_tool_calls: int,
        total_tokens_used: Optional[int] = None,
    ) -> None:
        """Emit execution completed event."""
        self._emit(
            EventType.EXECUTION_COMPLETED,
            {
                "final_output": final_output,
                "total_duration_seconds": total_duration_seconds,
                "total_llm_calls": total_llm_calls,
                "total_tool_calls": total_tool_calls,
                "total_tokens_used": total_tokens_used,
            },
        )

    def emit_execution_failed(
        self,
        error_message: str,
        error_type: str,
        stack_trace: Optional[str] = None,
        partial_output: Optional[str] = None,
    ) -> None:
        """Emit execution failed event."""
        self._emit(
            EventType.EXECUTION_FAILED,
            {
                "error_message": error_message,
                "error_type": error_type,
                "stack_trace": stack_trace,
                "partial_output": partial_output,
            },
        )

    # ==================== Phase-level events ====================

    @asynccontextmanager
    async def phase(
        self,
        phase_name: str,
        phase_description: str,
        planned_workers: int,
        phase_index: int,
    ):
        """Context manager for tracking a phase.

        Usage:
            async with sidekick.phase("Research", "Initial research phase", 3, 1) as phase_id:
                # Execute workers in this phase
                pass
        """
        phase_id = str(uuid.uuid4())
        self._current_phase_id = phase_id

        self._emit(
            EventType.PHASE_STARTED,
            {
                "phase_name": phase_name,
                "phase_description": phase_description,
                "planned_workers": planned_workers,
                "phase_index": phase_index,
            },
        )

        start_time = datetime.utcnow()
        workers_completed = 0
        workers_failed = 0
        error_occurred = None

        try:
            yield phase_id
        except Exception as e:
            error_occurred = e
            self._emit(
                EventType.PHASE_FAILED,
                {
                    "phase_name": phase_name,
                    "error_message": str(e),
                    "workers_completed": workers_completed,
                    "workers_failed": workers_failed,
                },
            )
            raise
        finally:
            if error_occurred is None:
                duration = (datetime.utcnow() - start_time).total_seconds()
                self._emit(
                    EventType.PHASE_COMPLETED,
                    {
                        "phase_name": phase_name,
                        "duration_seconds": duration,
                        "workers_completed": workers_completed,
                        "workers_failed": workers_failed,
                    },
                )
            self._current_phase_id = None

    def emit_phase_started(
        self,
        phase_name: str,
        phase_description: str,
        planned_workers: int,
        phase_index: int,
    ) -> str:
        """Emit phase started event and return phase ID.

        Use this instead of the context manager for manual phase tracking.
        """
        phase_id = str(uuid.uuid4())
        self._current_phase_id = phase_id

        self._emit(
            EventType.PHASE_STARTED,
            {
                "phase_name": phase_name,
                "phase_description": phase_description,
                "planned_workers": planned_workers,
                "phase_index": phase_index,
            },
        )
        return phase_id

    def emit_phase_completed(
        self,
        phase_name: str,
        duration_seconds: float,
        workers_completed: int,
        workers_failed: int,
    ) -> None:
        """Emit phase completed event."""
        self._emit(
            EventType.PHASE_COMPLETED,
            {
                "phase_name": phase_name,
                "duration_seconds": duration_seconds,
                "workers_completed": workers_completed,
                "workers_failed": workers_failed,
            },
        )
        self._current_phase_id = None

    def emit_phase_failed(
        self,
        phase_name: str,
        error_message: str,
        workers_completed: int,
        workers_failed: int,
    ) -> None:
        """Emit phase failed event."""
        self._emit(
            EventType.PHASE_FAILED,
            {
                "phase_name": phase_name,
                "error_message": error_message,
                "workers_completed": workers_completed,
                "workers_failed": workers_failed,
            },
        )
        self._current_phase_id = None

    # ==================== Worker-level events ====================

    @asynccontextmanager
    async def worker(
        self,
        worker_name: str,
        task_description: str,
        star_id: str,
        star_version: str,
        input_context: str,
        expected_output_format: str,
        tools_available: List[str],
    ):
        """Context manager for tracking a worker.

        Usage:
            async with sidekick.worker("Research AI", "Research AI trends", ...) as worker_id:
                # Execute worker logic
                pass
        """
        worker_id = str(uuid.uuid4())
        self._current_worker_id = worker_id

        self._emit(
            EventType.WORKER_STARTED,
            {
                "worker_name": worker_name,
                "task_description": task_description,
                "star_id": star_id,
                "star_version": star_version,
                "input_context": input_context,
                "expected_output_format": expected_output_format,
                "tools_available": tools_available,
            },
        )

        start_time = datetime.utcnow()

        try:
            yield worker_id
        except Exception as e:
            self._emit(
                EventType.WORKER_FAILED,
                {
                    "worker_name": worker_name,
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "iterations_completed": 0,
                    "partial_output": None,
                },
            )
            raise
        finally:
            self._current_worker_id = None

    def emit_worker_started(
        self,
        worker_name: str,
        task_description: str,
        star_id: str,
        star_version: str,
        input_context: str,
        expected_output_format: str,
        tools_available: List[str],
    ) -> str:
        """Emit worker started event and return worker ID.

        Use this instead of the context manager for manual worker tracking.
        """
        worker_id = str(uuid.uuid4())
        self._current_worker_id = worker_id

        self._emit(
            EventType.WORKER_STARTED,
            {
                "worker_name": worker_name,
                "task_description": task_description,
                "star_id": star_id,
                "star_version": star_version,
                "input_context": input_context,
                "expected_output_format": expected_output_format,
                "tools_available": tools_available,
            },
        )
        return worker_id

    def emit_worker_completed(
        self,
        worker_name: str,
        final_output: str,
        total_iterations: int,
        total_tool_calls: int,
        duration_seconds: float,
    ) -> None:
        """Emit worker completed event."""
        self._emit(
            EventType.WORKER_COMPLETED,
            {
                "worker_name": worker_name,
                "final_output": final_output,
                "total_iterations": total_iterations,
                "total_tool_calls": total_tool_calls,
                "duration_seconds": duration_seconds,
            },
        )
        self._current_worker_id = None

    def emit_worker_failed(
        self,
        worker_name: str,
        error_message: str,
        error_type: str,
        iterations_completed: int,
        partial_output: Optional[str] = None,
    ) -> None:
        """Emit worker failed event."""
        self._emit(
            EventType.WORKER_FAILED,
            {
                "worker_name": worker_name,
                "error_message": error_message,
                "error_type": error_type,
                "iterations_completed": iterations_completed,
                "partial_output": partial_output,
            },
        )
        self._current_worker_id = None

    # ==================== LLM events ====================

    def emit_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        iteration: int,
    ) -> None:
        """Emit LLM call event."""
        # Truncate messages if too many
        if len(messages) > self._config.max_message_history:
            messages = messages[-self._config.max_message_history :]

        # Truncate individual message content if too large
        truncated_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if (
                isinstance(content, str)
                and len(content) > self._config.max_output_length
            ):
                msg = {
                    **msg,
                    "content": content[: self._config.max_output_length]
                    + "... [truncated]",
                }
            truncated_messages.append(msg)

        self._emit(
            EventType.WORKER_LLM_CALL,
            {
                "messages": truncated_messages,
                "model": model,
                "temperature": temperature,
                "iteration": iteration,
            },
        )

    def emit_llm_response(
        self,
        response_content: str,
        tool_calls: Optional[List[Dict[str, Any]]],
        tokens_used: Optional[int],
        latency_ms: int,
        iteration: int,
    ) -> None:
        """Emit LLM response event."""
        # Truncate response if too large
        if len(response_content) > self._config.max_output_length:
            response_content = (
                response_content[: self._config.max_output_length] + "... [truncated]"
            )

        self._emit(
            EventType.WORKER_LLM_RESPONSE,
            {
                "response_content": response_content,
                "tool_calls": tool_calls,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "iteration": iteration,
            },
        )

    # ==================== Tool events ====================

    def emit_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_call_id: str,
        iteration: int,
    ) -> None:
        """Emit tool call event."""
        self._emit(
            EventType.WORKER_TOOL_CALL,
            {
                "tool_name": tool_name,
                "tool_args": tool_args,
                "tool_call_id": tool_call_id,
                "iteration": iteration,
            },
        )

    def emit_tool_response(
        self,
        tool_name: str,
        tool_call_id: str,
        result: str,
        success: bool,
        latency_ms: int,
        iteration: int,
        error: Optional[str] = None,
    ) -> None:
        """Emit tool response event."""
        # Truncate result if too large
        if len(result) > self._config.max_output_length:
            result = result[: self._config.max_output_length] + "... [truncated]"

        self._emit(
            EventType.WORKER_TOOL_RESPONSE,
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "result": result,
                "success": success,
                "error": error,
                "latency_ms": latency_ms,
                "iteration": iteration,
            },
        )

    # ==================== Star events ====================

    def emit_star_loaded(
        self,
        star_id: str,
        star_name: str,
        star_version: str,
        content_hash: str,
        probes: List[str],
    ) -> None:
        """Emit star loaded event."""
        self._emit(
            EventType.STAR_LOADED,
            {
                "star_id": star_id,
                "star_name": star_name,
                "star_version": star_version,
                "content_hash": content_hash,
                "probes": probes,
            },
        )

    def emit_star_injected(
        self,
        star_id: str,
        worker_id: str,
        injection_type: str,
        injected_content: str,
    ) -> None:
        """Emit star injected event."""
        # Truncate content if too large
        if len(injected_content) > self._config.max_output_length:
            injected_content = (
                injected_content[: self._config.max_output_length] + "... [truncated]"
            )

        self._emit(
            EventType.STAR_INJECTED,
            {
                "star_id": star_id,
                "worker_id": worker_id,
                "injection_type": injection_type,
                "injected_content": injected_content,
            },
        )
