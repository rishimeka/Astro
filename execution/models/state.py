"""Execution state models for the Astro Execution Engine.

This module defines the state tracking models used during execution,
including worker state, phase state, and overall execution state.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid

from execution.models.input import ExecutionConfig


class WorkerStatus(str, Enum):
    """Status of a worker."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class PhaseStatus(str, Enum):
    """Status of a phase."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some workers succeeded, some failed


class ExecutionStatus(str, Enum):
    """Status of an execution run."""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCallRecord(BaseModel):
    """Record of a tool invocation."""

    tool_call_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this tool call",
    )
    probe_id: str = Field(description="ID of the probe that was called")
    probe_name: str = Field(description="Name of the probe that was called")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Arguments passed to the probe"
    )
    result: Optional[str] = Field(
        default=None, description="Result returned by the probe"
    )
    success: bool = Field(default=False, description="Whether the tool call succeeded")
    error: Optional[str] = Field(
        default=None, description="Error message if the call failed"
    )
    latency_ms: int = Field(
        default=0, description="Latency of the tool call in milliseconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the tool call was made"
    )


class WorkerState(BaseModel):
    """State of a single worker."""

    worker_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this worker",
    )
    worker_name: str = Field(description="Human-readable name for this worker")
    phase_id: str = Field(description="ID of the phase this worker belongs to")

    # Star binding
    star_id: str = Field(description="ID of the Star providing the prompt")
    star_version: str = Field(default="", description="Version of the Star being used")
    compiled_prompt: str = Field(
        default="", description="The full prompt after Star resolution"
    )

    # Task
    task_description: str = Field(
        default="", description="Specific task for this worker"
    )
    input_context: str = Field(default="", description="Context from previous phases")
    expected_output_format: str = Field(
        default="", description="Expected format for the output"
    )

    # Execution state
    status: WorkerStatus = Field(
        default=WorkerStatus.PENDING, description="Current status of the worker"
    )
    current_iteration: int = Field(
        default=0, description="Current LLM iteration number"
    )

    # Conversation history
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Message history for this worker"
    )

    # Tool usage
    tool_calls: List[ToolCallRecord] = Field(
        default_factory=list, description="Record of all tool calls made"
    )
    available_probes: List[str] = Field(
        default_factory=list, description="Probe IDs this worker can use"
    )

    # Output
    final_output: Optional[str] = Field(
        default=None, description="Final output from the worker"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if worker failed"
    )

    # Metrics
    total_tokens_used: int = Field(
        default=0, description="Total tokens used by this worker"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="When the worker started"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="When the worker completed"
    )

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the worker in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


class PhaseState(BaseModel):
    """State of a single phase."""

    phase_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this phase",
    )
    phase_name: str = Field(description="Human-readable name for this phase")
    phase_index: int = Field(description="Index of this phase in the execution")
    phase_description: str = Field(
        default="", description="Description of what this phase accomplishes"
    )

    # Workers
    workers: List[WorkerState] = Field(
        default_factory=list, description="Workers in this phase"
    )

    # Status
    status: PhaseStatus = Field(
        default=PhaseStatus.PENDING, description="Current status of the phase"
    )

    # Aggregated output
    phase_output: Optional[str] = Field(
        default=None, description="Combined output from all workers"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if phase failed"
    )

    # Metrics
    workers_completed: int = Field(
        default=0, description="Number of workers that completed successfully"
    )
    workers_failed: int = Field(default=0, description="Number of workers that failed")
    started_at: Optional[datetime] = Field(
        default=None, description="When the phase started"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="When the phase completed"
    )

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the phase in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


class ExecutionPlan(BaseModel):
    """The plan generated by the Planner."""

    phases: List[Dict[str, Any]] = Field(
        default_factory=list, description="Phase definitions"
    )
    reasoning: str = Field(default="", description="Why this plan was chosen")
    estimated_duration_seconds: float = Field(
        default=0.0, description="Estimated total duration"
    )
    estimated_total_workers: int = Field(
        default=0, description="Estimated total number of workers"
    )


class ExecutionState(BaseModel):
    """Complete state of an execution run."""

    # Identity
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this execution",
    )

    # Input
    query: str = Field(description="The original query")
    constellation_id: Optional[str] = Field(
        default=None, description="ID of the constellation being executed"
    )
    config: ExecutionConfig = Field(
        default_factory=ExecutionConfig, description="Execution configuration"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )

    # Plan
    plan: Optional[ExecutionPlan] = Field(
        default=None, description="The execution plan"
    )

    # Execution state
    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING, description="Current status of the execution"
    )
    current_phase_index: int = Field(
        default=0, description="Index of the current phase"
    )
    phases: List[PhaseState] = Field(
        default_factory=list, description="All phases in the execution"
    )

    # Evaluation
    evaluation_feedback: Optional[str] = Field(
        default=None, description="Feedback from evaluation"
    )
    needs_replanning: bool = Field(
        default=False, description="Whether replanning is needed"
    )
    replan_count: int = Field(
        default=0, description="Number of times replanning has occurred"
    )
    max_replans: int = Field(default=3, description="Maximum allowed replans")

    # Final output
    final_output: Optional[str] = Field(
        default=None, description="Final synthesized output"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )

    # Aggregate metrics
    total_phases: int = Field(default=0, description="Total number of phases executed")
    total_workers: int = Field(
        default=0, description="Total number of workers executed"
    )
    total_llm_calls: int = Field(default=0, description="Total LLM calls made")
    total_tool_calls: int = Field(default=0, description="Total tool calls made")
    total_tokens_used: int = Field(default=0, description="Total tokens used")

    # Timestamps
    started_at: Optional[datetime] = Field(
        default=None, description="When execution started"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="When execution completed"
    )

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the execution in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
