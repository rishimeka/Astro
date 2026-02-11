"""Request and response schemas for API endpoints."""

from datetime import datetime
from typing import Any

from astro.orchestration.models.star_types import StarType
from pydantic import BaseModel, Field

# =============================================================================
# Request Schemas
# =============================================================================


class DirectiveCreate(BaseModel):
    """Request schema for creating a directive."""

    id: str
    name: str
    description: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DirectiveUpdate(BaseModel):
    """Request schema for updating a directive."""

    name: str | None = None
    description: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None


class StarCreate(BaseModel):
    """Request schema for creating a star."""

    id: str
    name: str
    type: StarType
    directive_id: str
    probe_ids: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StarUpdate(BaseModel):
    """Request schema for updating a star."""

    name: str | None = None
    probe_ids: list[str] | None = None
    config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class NodeCreate(BaseModel):
    """Node creation schema."""

    id: str
    star_id: str
    position: dict[str, float]
    display_name: str | None = None
    requires_confirmation: bool = False
    confirmation_prompt: str | None = None


class EdgeCreate(BaseModel):
    """Edge creation schema."""

    id: str
    source: str
    target: str
    condition: str | None = None


class ConstellationCreate(BaseModel):
    """Request schema for creating a constellation."""

    id: str
    name: str
    description: str
    start: dict[str, Any]
    end: dict[str, Any]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    max_loop_iterations: int = 3
    max_retry_attempts: int = 3
    retry_delay_base: float = 2.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConstellationUpdate(BaseModel):
    """Request schema for updating a constellation."""

    name: str | None = None
    description: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    max_loop_iterations: int | None = None
    max_retry_attempts: int | None = None
    retry_delay_base: float | None = None
    metadata: dict[str, Any] | None = None


class RunRequest(BaseModel):
    """Request schema for running a constellation."""

    variables: dict[str, Any]


class ConfirmRequest(BaseModel):
    """Request schema for confirming/cancelling a paused run."""

    proceed: bool = Field(..., description="True to continue, False to cancel")
    additional_context: str | None = Field(
        None,
        description="Optional additional context to inject into downstream nodes",
    )


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    message: str
    conversation_id: str | None = None


# =============================================================================
# Response Schemas
# =============================================================================


class DirectiveSummary(BaseModel):
    """Summary schema for listing directives."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)


class StarSummary(BaseModel):
    """Summary schema for listing stars."""

    id: str
    name: str
    type: StarType
    directive_id: str


class ConstellationSummary(BaseModel):
    """Summary schema for listing constellations."""

    id: str
    name: str
    description: str
    node_count: int
    tags: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Summary schema for listing runs."""

    id: str
    constellation_id: str
    constellation_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None


class NodeOutputResponse(BaseModel):
    """Response schema for node output."""

    node_id: str
    star_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: str | None = None
    error: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class RunResponse(BaseModel):
    """Full response schema for a run."""

    id: str
    constellation_id: str
    constellation_name: str
    status: str
    variables: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None = None
    node_outputs: dict[str, NodeOutputResponse]
    final_output: str | None = None
    error: str | None = None
    awaiting_node_id: str | None = None
    awaiting_prompt: str | None = None


class ConfirmResponse(BaseModel):
    """Response schema for confirm endpoint."""

    run_id: str
    status: str
    message: str


class DirectiveResponse(BaseModel):
    """Response schema with warnings for directive operations."""

    directive: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class StarResponse(BaseModel):
    """Response schema with warnings for star operations."""

    star: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class ConstellationResponse(BaseModel):
    """Response schema with warnings for constellation operations."""

    constellation: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: str | None = None


class ProbeResponse(BaseModel):
    """Response schema for a probe."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""

    action: str
    response: str
    constellation_id: str | None = None
    run_id: str | None = None
    missing_variables: list[str] = Field(default_factory=list)
    conversation_id: str
