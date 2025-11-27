"""Data model for representing a star in the star foundry."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    text = "text"
    markdown = "md"
    xml = "xml"


class StarMetadata(BaseModel):
    description: str = Field(description="Purpose and human-readable summary of the star")
    content_type: ContentType = Field(description="File or text type of the content")
    tags: list[str] = Field(default_factory=list, description="Categorization labels")
    version: str = Field(description="Semantic version of the star")
    created_by: str = Field(description="Creator identifier")
    created_on: datetime = Field(description="Creation timestamp in ISO format")
    updated_by: str = Field(description="Identifier of the last updater")
    updated_on: datetime = Field(description="Last update timestamp")


class Star(BaseModel):
    id: str = Field(description="Unique identifier for the star")
    name: str = Field(description="Human-readable name of the star")
    metadata: StarMetadata = Field(description="Metadata associated with the star")
    content: str = Field(description="The full prompt text of the star")
    references: list[str] = Field(default_factory=list, description="IDs of referenced stars")
    tools: list[str] = Field(default_factory=list, description="Tool IDs used by this star")
    parents: list[str] = Field(default_factory=list, description="Reverse edges populated by Astro")
    file_path: str | None = Field(default=None, description="Source storage path, if applicable")
