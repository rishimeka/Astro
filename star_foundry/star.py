"""
Star data model definition for raw storage + enriched runtime fields.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from probes import Probe


class Star(BaseModel):
    """
    Represents a Star entity loaded from MongoDB and enriched by StarRegistry.
    """

    # ------------------
    # Stored in MongoDB
    # ------------------
    id: str = Field(description="Unique Star ID")
    name: str
    description: str
    content: str
    references: list[str] = Field(default_factory=list)
    probes: list[str] = Field(default_factory=list)
    created_on: datetime
    updated_on: datetime

    # ------------------
    # Runtime-only (NOT stored in Mongo)
    # These get populated by StarRegistry after load
    # ------------------
    resolved_references: list["Star"] = Field(default_factory=list)
    resolved_probes: list[Probe] = Field(default_factory=list)
    missing_references: list[str] = Field(default_factory=list)
    missing_probes: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"
