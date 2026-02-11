"""Node models for Constellation graph structure."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Type of node in a Constellation."""

    START = "start"
    END = "end"
    STAR = "star"


class Position(BaseModel):
    """UI position for React Flow."""

    x: float
    y: float


class BaseNode(BaseModel):
    """Base class for all nodes in a Constellation."""

    id: str
    type: NodeType
    position: Position


class StartNode(BaseNode):
    """Entry point. Holds original query at runtime."""

    type: NodeType = Field(default=NodeType.START, frozen=True)

    # Filled at runtime
    original_query: str | None = None
    constellation_purpose: str | None = Field(
        default=None, description="From constellation.description"
    )


class EndNode(BaseNode):
    """Completion marker."""

    type: NodeType = Field(default=NodeType.END, frozen=True)


class StarNode(BaseNode):
    """A Star instance with variable bindings."""

    type: NodeType = Field(default=NodeType.STAR, frozen=True)

    # What Star this node executes
    star_id: str = Field(..., description="Reference to Star definition")

    # Optional display override
    display_name: str | None = Field(
        None,
        description="Override name shown in UI. "
        "Useful when same Star appears multiple times.",
    )

    # Empty at creation, filled at runtime
    variable_bindings: dict[str, Any] = Field(default_factory=dict)

    # Human-in-the-loop support
    requires_confirmation: bool = Field(
        default=False,
        description="If true, executor pauses after this node completes "
        "and waits for user confirmation before continuing.",
    )
    confirmation_prompt: str | None = Field(
        default=None,
        description="Message shown to user when awaiting confirmation. "
        "E.g., 'Review the analysis above. Proceed with synthesis?'",
    )
