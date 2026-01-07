"""Sidekick event models.

Events are individual occurrences emitted by the execution code.
Examples: "Worker started", "Tool called", "LLM response received".
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid


class EventType(str, Enum):
    """Types of events that can be emitted during execution."""

    # Execution-level events
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"

    # Phase-level events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"

    # Worker-level events
    WORKER_STARTED = "worker_started"
    WORKER_LLM_CALL = "worker_llm_call"
    WORKER_LLM_RESPONSE = "worker_llm_response"
    WORKER_TOOL_CALL = "worker_tool_call"
    WORKER_TOOL_RESPONSE = "worker_tool_response"
    WORKER_COMPLETED = "worker_completed"
    WORKER_FAILED = "worker_failed"

    # Star-level events (prompt tracking)
    STAR_LOADED = "star_loaded"
    STAR_INJECTED = "star_injected"


class SidekickEvent(BaseModel):
    """A single event emitted during execution.

    Events are the raw data points captured during execution.
    They are aggregated into Traces for persistence and analysis.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Hierarchy identifiers (for aggregation)
    trace_id: str  # Execution-level ID
    phase_id: Optional[str] = None  # Phase-level ID (if applicable)
    worker_id: Optional[str] = None  # Worker-level ID (if applicable)

    # Event payload (varies by event type)
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# ==================== Event Payload Models ====================


class ExecutionStartedPayload(BaseModel):
    """Payload for EXECUTION_STARTED event."""

    original_query: str
    stars_used: List[str]  # Star IDs loaded for this execution
    probes_available: List[str]  # Probe IDs available
    config: Dict[str, Any]  # Execution configuration


class ExecutionCompletedPayload(BaseModel):
    """Payload for EXECUTION_COMPLETED event."""

    final_output: str
    total_duration_seconds: float
    total_llm_calls: int
    total_tool_calls: int
    total_tokens_used: Optional[int] = None


class ExecutionFailedPayload(BaseModel):
    """Payload for EXECUTION_FAILED event."""

    error_message: str
    error_type: str
    stack_trace: Optional[str] = None
    partial_output: Optional[str] = None


class PhaseStartedPayload(BaseModel):
    """Payload for PHASE_STARTED event."""

    phase_name: str
    phase_description: str
    planned_workers: int
    phase_index: int  # 1-indexed position in execution


class PhaseCompletedPayload(BaseModel):
    """Payload for PHASE_COMPLETED event."""

    phase_name: str
    duration_seconds: float
    workers_completed: int
    workers_failed: int


class PhaseFailedPayload(BaseModel):
    """Payload for PHASE_FAILED event."""

    phase_name: str
    error_message: str
    workers_completed: int
    workers_failed: int


class WorkerStartedPayload(BaseModel):
    """Payload for WORKER_STARTED event."""

    worker_name: str
    task_description: str
    star_id: str  # Which Star's prompt is being used
    star_version: str
    input_context: str  # What the worker received as input
    expected_output_format: str
    tools_available: List[str]  # Probe IDs this worker can use


class WorkerLLMCallPayload(BaseModel):
    """Payload for WORKER_LLM_CALL event."""

    messages: List[Dict[str, Any]]  # Full message history sent to LLM
    model: str
    temperature: float
    iteration: int  # Which iteration of the worker loop


class WorkerLLMResponsePayload(BaseModel):
    """Payload for WORKER_LLM_RESPONSE event."""

    response_content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None  # If LLM requested tool calls
    tokens_used: Optional[int] = None
    latency_ms: int
    iteration: int


class WorkerToolCallPayload(BaseModel):
    """Payload for WORKER_TOOL_CALL event."""

    tool_name: str
    tool_args: Dict[str, Any]
    tool_call_id: str
    iteration: int


class WorkerToolResponsePayload(BaseModel):
    """Payload for WORKER_TOOL_RESPONSE event."""

    tool_name: str
    tool_call_id: str
    result: str
    success: bool
    error: Optional[str] = None
    latency_ms: int
    iteration: int


class WorkerCompletedPayload(BaseModel):
    """Payload for WORKER_COMPLETED event."""

    worker_name: str
    final_output: str
    total_iterations: int
    total_tool_calls: int
    duration_seconds: float


class WorkerFailedPayload(BaseModel):
    """Payload for WORKER_FAILED event."""

    worker_name: str
    error_message: str
    error_type: str
    iterations_completed: int
    partial_output: Optional[str] = None


class StarLoadedPayload(BaseModel):
    """Payload for STAR_LOADED event."""

    star_id: str
    star_name: str
    star_version: str
    content_hash: str  # For detecting changes
    probes: List[str]


class StarInjectedPayload(BaseModel):
    """Payload for STAR_INJECTED event."""

    star_id: str
    worker_id: str
    injection_type: str  # "system_prompt", "nudge", etc.
    injected_content: str  # The actual prompt content used
