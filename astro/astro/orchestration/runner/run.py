"""Run and NodeOutput models for execution tracking."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Record of a tool call during execution."""

    tool_name: str
    arguments: dict[str, Any]
    result: str | None = None
    error: str | None = None


class NodeOutput(BaseModel):
    """Output and status for a single node execution."""

    node_id: str
    star_id: str
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending"
    )
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: str | None = None
    error: str | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)


RunStatus = Literal[
    "running", "awaiting_confirmation", "completed", "failed", "cancelled"
]


class Run(BaseModel):
    """Complete execution record for a constellation run."""

    id: str
    constellation_id: str
    constellation_name: str
    status: RunStatus = Field(default="running")
    variables: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime | None = None
    node_outputs: dict[str, NodeOutput] = Field(default_factory=dict)
    final_output: str | None = None
    error: str | None = None

    # Human-in-the-loop state
    awaiting_node_id: str | None = Field(
        default=None,
        description="Node ID where execution is paused awaiting confirmation",
    )
    awaiting_prompt: str | None = Field(
        default=None, description="Confirmation prompt shown to user"
    )

    # Additional context that may be injected during resume
    additional_context: str | None = Field(
        default=None, description="Context added by user on resume"
    )

    model_config = {"arbitrary_types_allowed": True}
