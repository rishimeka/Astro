"""Sidekick trace models.

Traces are aggregated, structured records built from events.
A single execution run produces one ExecutionTrace containing
multiple PhaseTrace objects, each containing multiple WorkerTrace objects.

These models match the Nebula input schema exactly for seamless integration.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class ToolCall(BaseModel):
    """Record of a single tool invocation."""

    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    tool_result: str = ""
    success: bool = True
    error: Optional[str] = None
    latency_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkerTrace(BaseModel):
    """Complete trace for a single worker execution.

    Captures the full context of what a worker did:
    - What task it was assigned
    - What Star prompt it used
    - Full conversation history with the LLM
    - All tool calls and their results
    - Final output and metrics
    """

    worker_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    worker_name: str
    star_id: str = ""
    star_version: str = ""
    task_description: str = ""
    input_context: str = ""
    expected_output_format: str = ""

    # Full conversation history
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    # Tool usage
    tool_calls: List[ToolCall] = Field(default_factory=list)

    # Outcome
    final_output: str = ""
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: Optional[str] = None

    # Metrics
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tokens_used: Optional[int] = None
    duration_seconds: float = 0.0

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if worker has finished (successfully or with failure)."""
        return self.status in ("completed", "failed")


class PhaseTrace(BaseModel):
    """Complete trace for a phase execution.

    A phase contains multiple workers that execute in parallel.
    This captures the aggregate results and metrics for the phase.
    """

    phase_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phase_name: str
    phase_description: str = ""
    phase_index: int = 0

    # Workers in this phase
    workers: List[WorkerTrace] = Field(default_factory=list)

    # Outcome
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: Optional[str] = None

    # Metrics
    workers_completed: int = 0
    workers_failed: int = 0
    duration_seconds: float = 0.0

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if phase has finished (successfully or with failure)."""
        return self.status in ("completed", "failed")

    @property
    def total_workers(self) -> int:
        """Total number of workers in this phase."""
        return len(self.workers)

    @property
    def success_rate(self) -> float:
        """Percentage of workers that completed successfully."""
        if not self.workers:
            return 0.0
        return self.workers_completed / len(self.workers)


class ExecutionTrace(BaseModel):
    """Complete trace for an entire execution run.

    This is the top-level trace object that captures everything
    about a single execution. It contains:
    - The original query
    - All Stars used and their versions
    - All phases and their workers
    - Final output and aggregate metrics

    This format matches Nebula's expected input schema exactly.
    """

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Query
    original_query: str = ""

    # Stars used (star_id -> version mapping)
    stars_used: Dict[str, str] = Field(default_factory=dict)

    # Phases
    phases: List[PhaseTrace] = Field(default_factory=list)

    # Final outcome
    final_output: str = ""
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: Optional[str] = None

    # Aggregate metrics
    total_phases: int = 0
    total_workers: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens_used: Optional[int] = None
    total_duration_seconds: float = 0.0

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if execution has finished (successfully or with failure)."""
        return self.status in ("completed", "failed")

    def get_phase(self, phase_id: str) -> Optional[PhaseTrace]:
        """Get a phase by ID."""
        for phase in self.phases:
            if phase.phase_id == phase_id:
                return phase
        return None

    def get_worker(self, worker_id: str) -> Optional[WorkerTrace]:
        """Get a worker by ID from any phase."""
        for phase in self.phases:
            for worker in phase.workers:
                if worker.worker_id == worker_id:
                    return worker
        return None

    def to_summary(self) -> Dict[str, Any]:
        """Generate a human-readable summary of the trace."""
        return {
            "trace_id": self.trace_id,
            "query": (
                self.original_query[:100] + "..."
                if len(self.original_query) > 100
                else self.original_query
            ),
            "status": self.status,
            "duration_seconds": self.total_duration_seconds,
            "phases": self.total_phases,
            "workers": self.total_workers,
            "llm_calls": self.total_llm_calls,
            "tool_calls": self.total_tool_calls,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }
