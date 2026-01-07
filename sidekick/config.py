"""Sidekick configuration."""

from pydantic import BaseModel
from typing import Optional
import os


class SidekickConfig(BaseModel):
    """Configuration for Sidekick observability system.

    All settings can be overridden via environment variables
    with the SIDEKICK_ prefix.
    """

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "astro"
    traces_collection: str = "execution_traces"

    # Queue
    max_queue_size: int = 10000
    drop_policy: str = "oldest"  # "oldest" or "newest"

    # Persistence
    batch_size: int = 100  # Number of events to batch before writing
    flush_interval_seconds: float = 1.0  # Max time between flushes

    # Retention
    trace_retention_days: int = 30  # How long to keep traces

    # Performance
    enable_compression: bool = True  # Compress large payloads
    max_message_size_bytes: int = 1_000_000  # 1MB max per message
    truncate_large_outputs: bool = True
    max_output_length: int = 50000  # Truncate outputs longer than this
    max_message_history: int = 100  # Max messages to keep in trace

    # Fallback
    fallback_dir: str = "./sidekick_fallback"  # Directory for fallback files

    # Retry
    max_retries: int = 3
    retry_interval_seconds: float = 5.0

    class Config:
        env_prefix = "SIDEKICK_"

    @classmethod
    def from_env(cls) -> "SidekickConfig":
        """Create config from environment variables."""
        return cls(
            mongodb_uri=os.getenv("SIDEKICK_MONGODB_URI", "mongodb://localhost:27017"),
            database_name=os.getenv("SIDEKICK_DATABASE_NAME", "astro"),
            traces_collection=os.getenv(
                "SIDEKICK_TRACES_COLLECTION", "execution_traces"
            ),
            max_queue_size=int(os.getenv("SIDEKICK_MAX_QUEUE_SIZE", "10000")),
            drop_policy=os.getenv("SIDEKICK_DROP_POLICY", "oldest"),
            batch_size=int(os.getenv("SIDEKICK_BATCH_SIZE", "100")),
            flush_interval_seconds=float(
                os.getenv("SIDEKICK_FLUSH_INTERVAL_SECONDS", "1.0")
            ),
            trace_retention_days=int(os.getenv("SIDEKICK_TRACE_RETENTION_DAYS", "30")),
            enable_compression=os.getenv("SIDEKICK_ENABLE_COMPRESSION", "true").lower()
            == "true",
            max_message_size_bytes=int(
                os.getenv("SIDEKICK_MAX_MESSAGE_SIZE_BYTES", "1000000")
            ),
            truncate_large_outputs=os.getenv(
                "SIDEKICK_TRUNCATE_LARGE_OUTPUTS", "true"
            ).lower()
            == "true",
            max_output_length=int(os.getenv("SIDEKICK_MAX_OUTPUT_LENGTH", "50000")),
            max_message_history=int(os.getenv("SIDEKICK_MAX_MESSAGE_HISTORY", "100")),
            fallback_dir=os.getenv("SIDEKICK_FALLBACK_DIR", "./sidekick_fallback"),
            max_retries=int(os.getenv("SIDEKICK_MAX_RETRIES", "3")),
            retry_interval_seconds=float(
                os.getenv("SIDEKICK_RETRY_INTERVAL_SECONDS", "5.0")
            ),
        )


# Global config instance
_config: Optional[SidekickConfig] = None


def get_config() -> SidekickConfig:
    """Get the global Sidekick config instance."""
    global _config
    if _config is None:
        _config = SidekickConfig.from_env()
    return _config


def set_config(config: SidekickConfig) -> None:
    """Set the global Sidekick config instance."""
    global _config
    _config = config
