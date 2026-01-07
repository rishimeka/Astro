"""Sidekick Processor for consuming events and building traces.

The processor runs in the background, consuming events from the queue
and aggregating them into structured traces.
"""

import asyncio
from typing import Optional, Dict, List
import logging
import json
from pathlib import Path

from sidekick.models.events import EventType, SidekickEvent
from sidekick.models.traces import ExecutionTrace, PhaseTrace, WorkerTrace, ToolCall
from sidekick.config import SidekickConfig, get_config

logger = logging.getLogger(__name__)


class SidekickProcessor:
    """Background processor that consumes events and builds traces.

    Design principles:
    - Never crash the main execution
    - Degrade gracefully if MongoDB is down
    - Drop rather than block if overwhelmed
    - Partial traces are better than no traces
    """

    def __init__(
        self,
        queue: asyncio.Queue,
        trace_id: str,
        config: Optional[SidekickConfig] = None,
    ):
        self._queue = queue
        self._trace_id = trace_id
        self._config = config or get_config()
        self._trace: Optional[ExecutionTrace] = None
        self._phases: Dict[str, PhaseTrace] = {}
        self._workers: Dict[str, WorkerTrace] = {}
        self._persistence: Optional["SidekickPersistence"] = None
        self._local_buffer: List[SidekickEvent] = []
        self._tool_call_args: Dict[str, Dict] = {}  # Store args from TOOL_CALL events

    async def _get_persistence(self) -> "SidekickPersistence":
        """Lazy load persistence layer."""
        if self._persistence is None:
            from sidekick.persistence import SidekickPersistence

            self._persistence = SidekickPersistence(self._config)
        return self._persistence

    async def run(self) -> None:
        """Main processing loop."""
        while True:
            try:
                event = await self._queue.get()

                # Sentinel value signals shutdown
                if event is None:
                    break

                await self._process_event(event)
                self._queue.task_done()
            except Exception as e:
                # Log error but don't crash
                logger.error(f"Sidekick processor error: {e}")

        # Final persistence on shutdown
        await self._finalize()

    async def _process_event(self, event: SidekickEvent) -> None:
        """Route event to appropriate handler."""
        try:
            handlers = {
                EventType.EXECUTION_STARTED: self._handle_execution_started,
                EventType.EXECUTION_COMPLETED: self._handle_execution_completed,
                EventType.EXECUTION_FAILED: self._handle_execution_failed,
                EventType.PHASE_STARTED: self._handle_phase_started,
                EventType.PHASE_COMPLETED: self._handle_phase_completed,
                EventType.PHASE_FAILED: self._handle_phase_failed,
                EventType.WORKER_STARTED: self._handle_worker_started,
                EventType.WORKER_LLM_CALL: self._handle_llm_call,
                EventType.WORKER_LLM_RESPONSE: self._handle_llm_response,
                EventType.WORKER_TOOL_CALL: self._handle_tool_call,
                EventType.WORKER_TOOL_RESPONSE: self._handle_tool_response,
                EventType.WORKER_COMPLETED: self._handle_worker_completed,
                EventType.WORKER_FAILED: self._handle_worker_failed,
                EventType.STAR_LOADED: self._handle_star_loaded,
                EventType.STAR_INJECTED: self._handle_star_injected,
            }

            handler = handlers.get(event.event_type)
            if handler:
                await handler(event)
        except Exception as e:
            # Buffer event for potential retry
            if len(self._local_buffer) < 1000:
                self._local_buffer.append(event)
            logger.error(f"Failed to process event {event.event_id}: {e}")

    # ==================== Event Handlers ====================

    async def _handle_execution_started(self, event: SidekickEvent) -> None:
        """Handle execution started event."""
        payload = event.payload
        self._trace = ExecutionTrace(
            trace_id=self._trace_id,
            timestamp=event.timestamp,
            original_query=payload.get("original_query", ""),
            started_at=event.timestamp,
            status="running",
        )
        # Store star IDs (versions will be filled in by STAR_LOADED events)
        for star_id in payload.get("stars_used", []):
            self._trace.stars_used[star_id] = "unknown"

    async def _handle_execution_completed(self, event: SidekickEvent) -> None:
        """Handle execution completed event."""
        if not self._trace:
            return

        payload = event.payload
        self._trace.final_output = payload.get("final_output", "")
        self._trace.total_duration_seconds = payload.get("total_duration_seconds", 0.0)
        self._trace.total_llm_calls = payload.get("total_llm_calls", 0)
        self._trace.total_tool_calls = payload.get("total_tool_calls", 0)
        self._trace.total_tokens_used = payload.get("total_tokens_used")
        self._trace.completed_at = event.timestamp
        self._trace.status = "completed"

    async def _handle_execution_failed(self, event: SidekickEvent) -> None:
        """Handle execution failed event."""
        if not self._trace:
            return

        payload = event.payload
        self._trace.error = payload.get("error_message", "")
        self._trace.final_output = payload.get("partial_output", "")
        self._trace.completed_at = event.timestamp
        self._trace.status = "failed"

    async def _handle_phase_started(self, event: SidekickEvent) -> None:
        """Handle phase started event."""
        if not self._trace:
            return

        payload = event.payload
        phase = PhaseTrace(
            phase_id=event.phase_id or "",
            phase_name=payload.get("phase_name", ""),
            phase_description=payload.get("phase_description", ""),
            phase_index=payload.get("phase_index", 0),
            started_at=event.timestamp,
            status="running",
        )
        if event.phase_id:
            self._phases[event.phase_id] = phase
        self._trace.phases.append(phase)
        self._trace.total_phases += 1

    async def _handle_phase_completed(self, event: SidekickEvent) -> None:
        """Handle phase completed event."""
        phase = self._phases.get(event.phase_id) if event.phase_id else None
        if not phase:
            return

        payload = event.payload
        phase.duration_seconds = payload.get("duration_seconds", 0.0)
        phase.workers_completed = payload.get("workers_completed", 0)
        phase.workers_failed = payload.get("workers_failed", 0)
        phase.completed_at = event.timestamp
        phase.status = "completed"

    async def _handle_phase_failed(self, event: SidekickEvent) -> None:
        """Handle phase failed event."""
        phase = self._phases.get(event.phase_id) if event.phase_id else None
        if not phase:
            return

        payload = event.payload
        phase.error = payload.get("error_message", "")
        phase.workers_completed = payload.get("workers_completed", 0)
        phase.workers_failed = payload.get("workers_failed", 0)
        phase.completed_at = event.timestamp
        phase.status = "failed"

    async def _handle_worker_started(self, event: SidekickEvent) -> None:
        """Handle worker started event."""
        phase = self._phases.get(event.phase_id) if event.phase_id else None
        if not phase:
            return

        payload = event.payload
        worker = WorkerTrace(
            worker_id=event.worker_id or "",
            worker_name=payload.get("worker_name", ""),
            star_id=payload.get("star_id", ""),
            star_version=payload.get("star_version", ""),
            task_description=payload.get("task_description", ""),
            input_context=payload.get("input_context", ""),
            expected_output_format=payload.get("expected_output_format", ""),
            started_at=event.timestamp,
            status="running",
        )
        if event.worker_id:
            self._workers[event.worker_id] = worker
        phase.workers.append(worker)
        if self._trace:
            self._trace.total_workers += 1

    async def _handle_llm_call(self, event: SidekickEvent) -> None:
        """Handle LLM call event."""
        worker = self._workers.get(event.worker_id) if event.worker_id else None
        if not worker:
            return

        payload = event.payload
        # Store the messages for this iteration
        worker.messages = payload.get("messages", [])
        if self._trace:
            self._trace.total_llm_calls += 1

    async def _handle_llm_response(self, event: SidekickEvent) -> None:
        """Handle LLM response event."""
        worker = self._workers.get(event.worker_id) if event.worker_id else None
        if not worker:
            return

        payload = event.payload
        # Append assistant response to messages
        worker.messages.append(
            {
                "role": "assistant",
                "content": payload.get("response_content", ""),
                "tool_calls": payload.get("tool_calls"),
            }
        )

        tokens_used = payload.get("tokens_used")
        if tokens_used:
            if worker.total_tokens_used is None:
                worker.total_tokens_used = 0
            worker.total_tokens_used += tokens_used

        worker.total_iterations = payload.get("iteration", 0)

    async def _handle_tool_call(self, event: SidekickEvent) -> None:
        """Handle tool call event."""
        payload = event.payload
        tool_call_id = payload.get("tool_call_id", "")
        # Store args for when we get the response
        self._tool_call_args[tool_call_id] = payload.get("tool_args", {})

    async def _handle_tool_response(self, event: SidekickEvent) -> None:
        """Handle tool response event."""
        worker = self._workers.get(event.worker_id) if event.worker_id else None
        if not worker:
            return

        payload = event.payload
        tool_call_id = payload.get("tool_call_id", "")
        tool_args = self._tool_call_args.pop(tool_call_id, {})

        tool_call = ToolCall(
            tool_name=payload.get("tool_name", ""),
            tool_args=tool_args,
            tool_result=payload.get("result", ""),
            success=payload.get("success", True),
            error=payload.get("error"),
            latency_ms=payload.get("latency_ms", 0),
            timestamp=event.timestamp,
        )
        worker.tool_calls.append(tool_call)
        worker.total_tool_calls += 1
        if self._trace:
            self._trace.total_tool_calls += 1

    async def _handle_worker_completed(self, event: SidekickEvent) -> None:
        """Handle worker completed event."""
        worker = self._workers.get(event.worker_id) if event.worker_id else None
        if not worker:
            return

        payload = event.payload
        worker.final_output = payload.get("final_output", "")
        worker.total_iterations = payload.get("total_iterations", 0)
        worker.total_tool_calls = payload.get("total_tool_calls", 0)
        worker.duration_seconds = payload.get("duration_seconds", 0.0)
        worker.completed_at = event.timestamp
        worker.status = "completed"

    async def _handle_worker_failed(self, event: SidekickEvent) -> None:
        """Handle worker failed event."""
        worker = self._workers.get(event.worker_id) if event.worker_id else None
        if not worker:
            return

        payload = event.payload
        worker.error = payload.get("error_message", "")
        worker.total_iterations = payload.get("iterations_completed", 0)
        worker.final_output = payload.get("partial_output", "")
        worker.completed_at = event.timestamp
        worker.status = "failed"

    async def _handle_star_loaded(self, event: SidekickEvent) -> None:
        """Handle star loaded event."""
        if not self._trace:
            return

        payload = event.payload
        star_id = payload.get("star_id", "")
        star_version = payload.get("star_version", "")
        if star_id:
            self._trace.stars_used[star_id] = star_version

    async def _handle_star_injected(self, event: SidekickEvent) -> None:
        """Handle star injected event."""
        # Could store injection details if needed for debugging
        pass

    async def _finalize(self) -> None:
        """Save final trace to persistence."""
        if not self._trace:
            return

        # Update final metrics
        self._trace.total_phases = len(self._trace.phases)
        self._trace.total_workers = sum(len(p.workers) for p in self._trace.phases)

        # Try to save to MongoDB
        for attempt in range(self._config.max_retries):
            try:
                persistence = await self._get_persistence()
                await persistence.save_trace(self._trace)
                logger.info(f"Sidekick: Saved trace {self._trace.trace_id}")
                return
            except Exception as e:
                if attempt < self._config.max_retries - 1:
                    logger.warning(f"Sidekick: Retry {attempt + 1} saving trace: {e}")
                    await asyncio.sleep(self._config.retry_interval_seconds)
                else:
                    logger.error(
                        f"Sidekick: Failed to save trace after {self._config.max_retries} attempts: {e}"
                    )
                    # Fall back to local file
                    await self._save_to_local_file()

    async def _save_to_local_file(self) -> None:
        """Fallback: save trace to local JSON file."""
        if not self._trace:
            return

        fallback_dir = Path(self._config.fallback_dir)
        fallback_dir.mkdir(exist_ok=True)

        filepath = fallback_dir / f"{self._trace.trace_id}.json"
        try:
            with open(filepath, "w") as f:
                json.dump(self._trace.model_dump(), f, default=str, indent=2)
            logger.info(f"Sidekick: Saved trace to fallback file: {filepath}")
        except Exception as e:
            logger.error(f"Sidekick: Failed to save fallback file: {e}")
