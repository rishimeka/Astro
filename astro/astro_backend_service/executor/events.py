"""Stream events for real-time execution updates.

This module defines a hierarchy of events that can be emitted during
constellation execution. Events are consumed by stream handlers
(SSE, WebSocket, logging, etc.) for real-time UI updates.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class StreamEvent(BaseModel):
    """Base class for all stream events.

    All events have a type discriminator, timestamp, and run_id for routing.
    """

    event_type: str = Field(..., description="Event type discriminator")
    timestamp: datetime = Field(default_factory=utc_now, description="Event timestamp")
    run_id: str = Field(..., description="Run ID this event belongs to")

    class Config:
        frozen = True


# =============================================================================
# Run Lifecycle Events
# =============================================================================


class RunStartedEvent(StreamEvent):
    """Emitted when a constellation run begins."""

    event_type: Literal["run_started"] = "run_started"
    constellation_id: str = Field(..., description="Constellation being executed")
    constellation_name: str = Field(
        ..., description="Human-readable constellation name"
    )
    total_nodes: int = Field(..., description="Total number of nodes to execute")
    node_names: List[str] = Field(
        default_factory=list, description="Ordered list of node names"
    )


class RunCompletedEvent(StreamEvent):
    """Emitted when a constellation run completes successfully."""

    event_type: Literal["run_completed"] = "run_completed"
    final_output: Optional[str] = Field(None, description="Final output from the run")
    duration_ms: Optional[int] = Field(
        None, description="Total execution time in milliseconds"
    )


class RunFailedEvent(StreamEvent):
    """Emitted when a constellation run fails."""

    event_type: Literal["run_failed"] = "run_failed"
    error: str = Field(..., description="Error message")
    failed_node_id: Optional[str] = Field(
        None, description="Node that caused the failure"
    )


class RunPausedEvent(StreamEvent):
    """Emitted when a run pauses for human confirmation."""

    event_type: Literal["run_paused"] = "run_paused"
    node_id: str = Field(..., description="Node awaiting confirmation")
    node_name: str = Field(..., description="Human-readable node name")
    prompt: str = Field(..., description="Confirmation prompt to show user")


# =============================================================================
# Node Lifecycle Events
# =============================================================================


class NodeStartedEvent(StreamEvent):
    """Emitted when a node begins execution."""

    event_type: Literal["node_started"] = "node_started"
    node_id: str = Field(..., description="Node ID")
    node_name: str = Field(..., description="Human-readable node name")
    star_id: str = Field(..., description="Star ID being executed")
    star_type: str = Field(..., description="Type of star (planning, execution, etc.)")
    node_index: int = Field(..., description="Position in execution order (1-based)")
    total_nodes: int = Field(..., description="Total number of nodes")


class NodeCompletedEvent(StreamEvent):
    """Emitted when a node completes successfully."""

    event_type: Literal["node_completed"] = "node_completed"
    node_id: str = Field(..., description="Node ID")
    node_name: str = Field(..., description="Human-readable node name")
    output_preview: Optional[str] = Field(None, description="Truncated output preview")
    duration_ms: int = Field(..., description="Execution time in milliseconds")


class NodeFailedEvent(StreamEvent):
    """Emitted when a node fails."""

    event_type: Literal["node_failed"] = "node_failed"
    node_id: str = Field(..., description="Node ID")
    node_name: str = Field(..., description="Human-readable node name")
    error: str = Field(..., description="Error message")
    duration_ms: int = Field(..., description="Time until failure in milliseconds")


# =============================================================================
# Tool/Probe Events
# =============================================================================


class ToolCallEvent(StreamEvent):
    """Emitted when a tool/probe is invoked."""

    event_type: Literal["tool_call"] = "tool_call"
    node_id: str = Field(..., description="Node making the tool call")
    tool_name: str = Field(..., description="Name of the tool/probe")
    tool_input: Dict[str, Any] = Field(
        default_factory=dict, description="Tool input parameters"
    )
    call_id: str = Field(..., description="Unique ID for this tool call")


class ToolResultEvent(StreamEvent):
    """Emitted when a tool/probe returns a result."""

    event_type: Literal["tool_result"] = "tool_result"
    node_id: str = Field(..., description="Node that made the tool call")
    tool_name: str = Field(..., description="Name of the tool/probe")
    call_id: str = Field(..., description="Matching call_id from ToolCallEvent")
    success: bool = Field(..., description="Whether the tool call succeeded")
    result_preview: Optional[str] = Field(None, description="Truncated result preview")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(..., description="Tool execution time in milliseconds")


# =============================================================================
# LLM Streaming Events
# =============================================================================


class ThoughtEvent(StreamEvent):
    """Emitted for LLM reasoning/thinking tokens (real-time streaming).

    These represent the model's internal reasoning process, streamed
    as tokens are generated.
    """

    event_type: Literal["thought"] = "thought"
    node_id: str = Field(..., description="Node generating the thought")
    content: str = Field(..., description="Thought content (may be partial token)")
    is_complete: bool = Field(False, description="Whether this completes the thought")


class TokenEvent(StreamEvent):
    """Emitted for output tokens during synthesis/generation.

    Used for streaming the final response to the user.
    """

    event_type: Literal["token"] = "token"
    node_id: Optional[str] = Field(None, description="Node generating the token")
    content: str = Field(..., description="Token content")


# =============================================================================
# Progress/Status Events
# =============================================================================


class ProgressEvent(StreamEvent):
    """Emitted for progress updates within a long-running operation."""

    event_type: Literal["progress"] = "progress"
    node_id: str = Field(..., description="Node reporting progress")
    message: str = Field(..., description="Progress message")
    percent: Optional[int] = Field(None, description="Completion percentage (0-100)")


class LogEvent(StreamEvent):
    """Emitted for debug/info logging during execution."""

    event_type: Literal["log"] = "log"
    level: Literal["debug", "info", "warning", "error"] = Field(
        "info", description="Log level"
    )
    message: str = Field(..., description="Log message")
    node_id: Optional[str] = Field(None, description="Associated node if any")


# =============================================================================
# Type Union for All Events
# =============================================================================

AnyStreamEvent = Union[
    RunStartedEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunPausedEvent,
    NodeStartedEvent,
    NodeCompletedEvent,
    NodeFailedEvent,
    ToolCallEvent,
    ToolResultEvent,
    ThoughtEvent,
    TokenEvent,
    ProgressEvent,
    LogEvent,
]


def truncate_output(text: Optional[str], max_length: int = 200) -> Optional[str]:
    """Truncate text for preview fields."""
    if text is None:
        return None
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
