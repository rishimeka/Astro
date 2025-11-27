from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class FoundrySettings(BaseSettings):
    """Configuration for the Star Foundry.

    Resolution order: programmatic, environment vars, .env files, defaults.
    """

    mongo_uri: str | None = Field(default=None, description="MongoDB connection URI")
    mongo_db: str = Field(default="astro", description="MongoDB database name")
    mongo_collection: str = Field(
        default="stars", description="MongoDB collection for stars"
    )
    load_source: str = Field(
        default="filesystem", description="Load source: mongo | filesystem | hybrid"
    )

    class Config:
        env_prefix = "ASTRO_"
