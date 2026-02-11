"""Request and response schemas for API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from astro.orchestration.models.star_types import StarType


# =============================================================================
# Request Schemas
# =============================================================================


class DirectiveCreate(BaseModel):
    """Request schema for creating a directive."""

    id: str
    name: str
    description: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DirectiveUpdate(BaseModel):
    """Request schema for updating a directive."""

    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StarCreate(BaseModel):
    """Request schema for creating a star."""

    id: str
    name: str
    type: StarType
    directive_id: str
    probe_ids: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StarUpdate(BaseModel):
    """Request schema for updating a star."""

    name: Optional[str] = None
    probe_ids: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class NodeCreate(BaseModel):
    """Node creation schema."""

    id: str
    star_id: str
    position: Dict[str, float]
    display_name: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


class EdgeCreate(BaseModel):
    """Edge creation schema."""

    id: str
    source: str
    target: str
    condition: Optional[str] = None


class ConstellationCreate(BaseModel):
    """Request schema for creating a constellation."""

    id: str
    name: str
    description: str
    start: Dict[str, Any]
    end: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    max_loop_iterations: int = 3
    max_retry_attempts: int = 3
    retry_delay_base: float = 2.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConstellationUpdate(BaseModel):
    """Request schema for updating a constellation."""

    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    max_loop_iterations: Optional[int] = None
    max_retry_attempts: Optional[int] = None
    retry_delay_base: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class RunRequest(BaseModel):
    """Request schema for running a constellation."""

    variables: Dict[str, Any]


class ConfirmRequest(BaseModel):
    """Request schema for confirming/cancelling a paused run."""

    proceed: bool = Field(..., description="True to continue, False to cancel")
    additional_context: Optional[str] = Field(
        None,
        description="Optional additional context to inject into downstream nodes",
    )


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    message: str
    conversation_id: Optional[str] = None


# =============================================================================
# Response Schemas
# =============================================================================


class DirectiveSummary(BaseModel):
    """Summary schema for listing directives."""

    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)


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
    tags: List[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Summary schema for listing runs."""

    id: str
    constellation_id: str
    constellation_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None


class NodeOutputResponse(BaseModel):
    """Response schema for node output."""

    node_id: str
    star_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[str] = None
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class RunResponse(BaseModel):
    """Full response schema for a run."""

    id: str
    constellation_id: str
    constellation_name: str
    status: str
    variables: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    node_outputs: Dict[str, NodeOutputResponse]
    final_output: Optional[str] = None
    error: Optional[str] = None
    awaiting_node_id: Optional[str] = None
    awaiting_prompt: Optional[str] = None


class ConfirmResponse(BaseModel):
    """Response schema for confirm endpoint."""

    run_id: str
    status: str
    message: str


class DirectiveResponse(BaseModel):
    """Response schema with warnings for directive operations."""

    directive: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class StarResponse(BaseModel):
    """Response schema with warnings for star operations."""

    star: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class ConstellationResponse(BaseModel):
    """Response schema with warnings for constellation operations."""

    constellation: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None


class ProbeResponse(BaseModel):
    """Response schema for a probe."""

    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""

    action: str
    response: str
    constellation_id: Optional[str] = None
    run_id: Optional[str] = None
    missing_variables: List[str] = Field(default_factory=list)
    conversation_id: str
