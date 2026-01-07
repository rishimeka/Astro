"""Sidekick integration for execution engine.

This module provides the interface between the execution engine
and the full Sidekick observability system.

Backwards compatible with the original stub interface while
providing full Sidekick functionality when available.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import full Sidekick module
try:
    from sidekick import SidekickClient as FullSidekickClient
    from sidekick import SidekickCallback
    from sidekick.config import SidekickConfig

    SIDEKICK_AVAILABLE = True
except ImportError:
    FullSidekickClient = None
    SidekickCallback = None
    SidekickConfig = None
    SIDEKICK_AVAILABLE = False
    logger.info("Full Sidekick module not available, using stub implementation")


class SidekickClient:
    """Unified Sidekick client for execution engine.

    Uses full Sidekick implementation if available,
    falls back to stub/logging implementation otherwise.
    """

    def __init__(
        self,
        execution_id: str,
        original_query: str,
        stars_used: List[str],
        probes_available: List[str],
        config: Dict[str, Any],
        _full_client: Optional["FullSidekickClient"] = None,
    ):
        """Initialize the Sidekick client.

        Args:
            execution_id: Unique identifier for this execution
            original_query: The user's original query
            stars_used: List of Star IDs being used
            probes_available: List of available probe IDs
            config: Execution configuration
            _full_client: Optional full Sidekick client (internal use)
        """
        self.execution_id = execution_id
        self.original_query = original_query
        self.stars_used = stars_used
        self.probes_available = probes_available
        self.config = config
        self._full_client = _full_client
        self._current_phase_id: Optional[str] = None
        self._current_worker_id: Optional[str] = None
        self._events: List[Dict[str, Any]] = []

    @property
    def is_full_sidekick(self) -> bool:
        """Check if full Sidekick is being used."""
        return self._full_client is not None

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        original_query: str,
        stars_used: List[str],
        probes_available: List[str],
        config: Dict[str, Any],
        execution_id: Optional[str] = None,
        use_full_sidekick: bool = True,
    ):
        """Create a Sidekick client as an async context manager.

        Args:
            original_query: The user's original query
            stars_used: List of Star IDs being used
            probes_available: List of available probe IDs
            config: Execution configuration
            execution_id: Optional execution ID (generated if not provided)
            use_full_sidekick: Whether to use full Sidekick if available

        Yields:
            SidekickClient instance
        """
        import uuid

        exec_id = execution_id or str(uuid.uuid4())

        if use_full_sidekick and SIDEKICK_AVAILABLE:
            # Use full Sidekick implementation
            async with FullSidekickClient.create(
                original_query=original_query,
                stars_used=stars_used,
                probes_available=probes_available,
                config=config,
            ) as full_client:
                client = cls(
                    execution_id=full_client.trace_id,
                    original_query=original_query,
                    stars_used=stars_used,
                    probes_available=probes_available,
                    config=config,
                    _full_client=full_client,
                )
                try:
                    yield client
                except Exception as e:
                    full_client.emit_execution_failed(
                        error_message=str(e),
                        error_type=type(e).__name__,
                    )
                    raise
        else:
            # Use stub implementation
            client = cls(
                execution_id=exec_id,
                original_query=original_query,
                stars_used=stars_used,
                probes_available=probes_available,
                config=config,
            )
            client._log_event(
                "EXECUTION_STARTED",
                {
                    "query": original_query,
                    "stars_used": stars_used,
                    "probes_available": probes_available,
                },
            )

            try:
                yield client
            except Exception as e:
                client._log_event(
                    "EXECUTION_FAILED",
                    {
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log event (stub implementation)."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": self.execution_id,
            "phase_id": self._current_phase_id,
            "worker_id": self._current_worker_id,
            "data": data,
        }
        self._events.append(event)
        logger.debug(f"Sidekick event: {event_type} - {data}")

    # ==================== Execution Events ====================

    def emit_execution_completed(
        self,
        final_output: str,
        total_duration_seconds: float,
        total_llm_calls: int,
        total_tool_calls: int,
        total_tokens_used: Optional[int] = None,
    ) -> None:
        """Emit execution completed event."""
        if self._full_client:
            self._full_client.emit_execution_completed(
                final_output=final_output,
                total_duration_seconds=total_duration_seconds,
                total_llm_calls=total_llm_calls,
                total_tool_calls=total_tool_calls,
                total_tokens_used=total_tokens_used,
            )
        else:
            self._log_event(
                "EXECUTION_COMPLETED",
                {
                    "final_output": final_output[:500] if final_output else "",
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
        if self._full_client:
            self._full_client.emit_execution_failed(
                error_message=error_message,
                error_type=error_type,
                stack_trace=stack_trace,
                partial_output=partial_output,
            )
        else:
            self._log_event(
                "EXECUTION_FAILED",
                {
                    "error_message": error_message,
                    "error_type": error_type,
                    "stack_trace": stack_trace,
                },
            )

    # ==================== Phase Events ====================

    @asynccontextmanager
    async def phase(
        self,
        phase_name: str,
        phase_description: str,
        planned_workers: int,
        phase_index: int,
        phase_id: Optional[str] = None,
    ):
        """Context manager for phase lifecycle events."""
        import uuid

        if self._full_client:
            async with self._full_client.phase(
                phase_name=phase_name,
                phase_description=phase_description,
                planned_workers=planned_workers,
                phase_index=phase_index,
            ) as pid:
                self._current_phase_id = pid
                try:
                    yield pid
                finally:
                    self._current_phase_id = None
        else:
            pid = phase_id or str(uuid.uuid4())
            self._current_phase_id = pid
            self._log_event(
                "PHASE_STARTED",
                {
                    "phase_name": phase_name,
                    "phase_description": phase_description,
                    "planned_workers": planned_workers,
                    "phase_index": phase_index,
                },
            )

            try:
                yield pid
            finally:
                self._log_event("PHASE_COMPLETED", {"phase_name": phase_name})
                self._current_phase_id = None

    def emit_phase_started(
        self,
        phase_name: str,
        phase_description: str,
        planned_workers: int,
        phase_index: int,
    ) -> str:
        """Emit phase started event and return phase ID."""
        if self._full_client:
            return self._full_client.emit_phase_started(
                phase_name=phase_name,
                phase_description=phase_description,
                planned_workers=planned_workers,
                phase_index=phase_index,
            )
        else:
            import uuid

            pid = str(uuid.uuid4())
            self._current_phase_id = pid
            self._log_event(
                "PHASE_STARTED",
                {
                    "phase_name": phase_name,
                    "phase_description": phase_description,
                    "planned_workers": planned_workers,
                    "phase_index": phase_index,
                },
            )
            return pid

    def emit_phase_completed(
        self,
        phase_name: str,
        duration_seconds: float,
        workers_completed: int,
        workers_failed: int,
    ) -> None:
        """Emit phase completed event."""
        if self._full_client:
            self._full_client.emit_phase_completed(
                phase_name=phase_name,
                duration_seconds=duration_seconds,
                workers_completed=workers_completed,
                workers_failed=workers_failed,
            )
        else:
            self._log_event(
                "PHASE_COMPLETED",
                {
                    "phase_name": phase_name,
                    "duration_seconds": duration_seconds,
                    "workers_completed": workers_completed,
                    "workers_failed": workers_failed,
                },
            )
        self._current_phase_id = None

    # ==================== Worker Events ====================

    @asynccontextmanager
    async def worker(
        self,
        worker_name: str,
        star_id: str,
        task_description: str,
        star_version: str = "",
        input_context: str = "",
        expected_output_format: str = "",
        tools_available: Optional[List[str]] = None,
        worker_id: Optional[str] = None,
    ):
        """Context manager for worker lifecycle events."""
        import uuid

        if self._full_client:
            async with self._full_client.worker(
                worker_name=worker_name,
                task_description=task_description,
                star_id=star_id,
                star_version=star_version,
                input_context=input_context,
                expected_output_format=expected_output_format,
                tools_available=tools_available or [],
            ) as wid:
                self._current_worker_id = wid
                try:
                    yield wid
                finally:
                    self._current_worker_id = None
        else:
            wid = worker_id or str(uuid.uuid4())
            self._current_worker_id = wid
            self._log_event(
                "WORKER_STARTED",
                {
                    "worker_name": worker_name,
                    "star_id": star_id,
                    "task_description": task_description,
                },
            )

            try:
                yield wid
            finally:
                self._current_worker_id = None

    def emit_worker_started(
        self,
        worker_name: str,
        task_description: str,
        star_id: str,
        star_version: str = "",
        input_context: str = "",
        expected_output_format: str = "",
        tools_available: Optional[List[str]] = None,
    ) -> str:
        """Emit worker started event and return worker ID."""
        if self._full_client:
            return self._full_client.emit_worker_started(
                worker_name=worker_name,
                task_description=task_description,
                star_id=star_id,
                star_version=star_version,
                input_context=input_context,
                expected_output_format=expected_output_format,
                tools_available=tools_available or [],
            )
        else:
            import uuid

            wid = str(uuid.uuid4())
            self._current_worker_id = wid
            self._log_event(
                "WORKER_STARTED",
                {
                    "worker_name": worker_name,
                    "star_id": star_id,
                    "task_description": task_description,
                },
            )
            return wid

    def emit_worker_completed(
        self,
        worker_name: str,
        final_output: str,
        total_iterations: int,
        total_tool_calls: int,
        duration_seconds: float,
    ) -> None:
        """Emit worker completed event."""
        if self._full_client:
            self._full_client.emit_worker_completed(
                worker_name=worker_name,
                final_output=final_output,
                total_iterations=total_iterations,
                total_tool_calls=total_tool_calls,
                duration_seconds=duration_seconds,
            )
        else:
            self._log_event(
                "WORKER_COMPLETED",
                {
                    "worker_name": worker_name,
                    "final_output": final_output[:500] if final_output else "",
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
        if self._full_client:
            self._full_client.emit_worker_failed(
                worker_name=worker_name,
                error_message=error_message,
                error_type=error_type,
                iterations_completed=iterations_completed,
                partial_output=partial_output,
            )
        else:
            self._log_event(
                "WORKER_FAILED",
                {
                    "worker_name": worker_name,
                    "error_message": error_message,
                    "error_type": error_type,
                    "iterations_completed": iterations_completed,
                    "partial_output": partial_output[:500] if partial_output else None,
                },
            )
        self._current_worker_id = None

    # ==================== LLM Events ====================

    def emit_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        iteration: int,
    ) -> None:
        """Emit LLM call event."""
        if self._full_client:
            self._full_client.emit_llm_call(
                messages=messages,
                model=model,
                temperature=temperature,
                iteration=iteration,
            )
        else:
            self._log_event(
                "LLM_CALL",
                {
                    "message_count": len(messages),
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
        if self._full_client:
            self._full_client.emit_llm_response(
                response_content=response_content,
                tool_calls=tool_calls,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                iteration=iteration,
            )
        else:
            self._log_event(
                "LLM_RESPONSE",
                {
                    "response_length": len(response_content) if response_content else 0,
                    "has_tool_calls": bool(tool_calls),
                    "tool_call_count": len(tool_calls) if tool_calls else 0,
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "iteration": iteration,
                },
            )

    # ==================== Tool Events ====================

    def emit_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_call_id: str,
        iteration: int,
    ) -> None:
        """Emit tool call event."""
        if self._full_client:
            self._full_client.emit_tool_call(
                tool_name=tool_name,
                tool_args=tool_args,
                tool_call_id=tool_call_id,
                iteration=iteration,
            )
        else:
            self._log_event(
                "TOOL_CALL",
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
        if self._full_client:
            self._full_client.emit_tool_response(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                result=result,
                success=success,
                latency_ms=latency_ms,
                iteration=iteration,
                error=error,
            )
        else:
            self._log_event(
                "TOOL_RESPONSE",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "result_length": len(result) if result else 0,
                    "success": success,
                    "error": error,
                    "latency_ms": latency_ms,
                    "iteration": iteration,
                },
            )

    # ==================== Star Events ====================

    def emit_star_loaded(
        self,
        star_id: str,
        star_name: str,
        star_version: str,
        content_hash: str,
        probes: List[str],
    ) -> None:
        """Emit star loaded event."""
        if self._full_client:
            self._full_client.emit_star_loaded(
                star_id=star_id,
                star_name=star_name,
                star_version=star_version,
                content_hash=content_hash,
                probes=probes,
            )
        else:
            self._log_event(
                "STAR_LOADED",
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
        if self._full_client:
            self._full_client.emit_star_injected(
                star_id=star_id,
                worker_id=worker_id,
                injection_type=injection_type,
                injected_content=injected_content,
            )
        else:
            self._log_event(
                "STAR_INJECTED",
                {
                    "star_id": star_id,
                    "worker_id": worker_id,
                    "injection_type": injection_type,
                    "content_length": len(injected_content),
                },
            )

    # ==================== Utility Methods ====================

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all recorded events (stub implementation only)."""
        return self._events.copy()

    def get_event_count(self) -> int:
        """Get the total number of events recorded."""
        return len(self._events)


def get_sidekick_callback(
    worker_id: Optional[str] = None,
) -> Optional["SidekickCallback"]:
    """Get a SidekickCallback if full Sidekick is available.

    Args:
        worker_id: Optional worker ID for context

    Returns:
        SidekickCallback if available, None otherwise
    """
    if SIDEKICK_AVAILABLE:
        from sidekick.callback import create_sidekick_callback

        return create_sidekick_callback(worker_id)
    return None
