"""Edge model for Constellation graph connections."""

from typing import Optional

from pydantic import BaseModel, Field


class Edge(BaseModel):
    """Connection between nodes."""

    id: str = Field(..., description="Unique edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")

    # For EvalStar routing only
    condition: Optional[str] = Field(
        None,
        description="Only for edges from EvalStar. "
        "Values: 'continue' or 'loop'. "
        "Matches EvalDecision.decision output.",
    )
