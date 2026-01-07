"""Execution input models for the Astro Execution Engine.

This module defines the input configuration and parameters for
starting an execution run.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class ExecutionMode(str, Enum):
    """Execution mode determining how the workflow is traversed."""

    STRICT = "strict"  # Follow constellation exactly
    GUIDED = "guided"  # AI can optimize path
    DYNAMIC = "dynamic"  # AI constructs path from available Stars


class ExecutionConfig(BaseModel):
    """Configuration for an execution run."""

    # Execution behavior
    mode: ExecutionMode = Field(
        default=ExecutionMode.STRICT,
        description="How the workflow graph should be traversed",
    )
    max_phases: int = Field(
        default=10, ge=1, le=50, description="Maximum number of phases allowed"
    )
    max_workers_per_phase: int = Field(
        default=8, ge=1, le=20, description="Maximum parallel workers per phase"
    )
    max_iterations_per_worker: int = Field(
        default=10, ge=1, le=50, description="Maximum LLM iterations per worker"
    )

    # Timeouts (seconds)
    phase_timeout: float = Field(
        default=300.0, description="Timeout for a single phase in seconds"
    )
    worker_timeout: float = Field(
        default=120.0, description="Timeout for a single worker in seconds"
    )
    tool_timeout: float = Field(
        default=30.0, description="Timeout for a single tool call in seconds"
    )

    # LLM configuration
    default_model: str = Field(
        default="gpt-4-turbo-preview", description="Default LLM model to use"
    )
    default_temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Default temperature for LLM calls"
    )

    # Retry behavior
    max_worker_retries: int = Field(
        default=2, description="Maximum retries for a failed worker"
    )
    retry_delay_seconds: float = Field(
        default=1.0, description="Delay between retries in seconds"
    )

    # Feature flags
    enable_caching: bool = Field(
        default=True, description="Enable caching of LLM and tool responses"
    )
    enable_parallel_workers: bool = Field(
        default=True, description="Enable parallel execution of workers within a phase"
    )
    fail_fast_on_worker_error: bool = Field(
        default=False, description="Stop execution immediately on first worker error"
    )


class ExecutionInput(BaseModel):
    """Input to start an execution run."""

    # Required
    query: str = Field(description="The user's original query to process")

    # Workflow specification (one of these)
    constellation_id: Optional[str] = Field(
        default=None, description="ID of a predefined Constellation to execute"
    )
    star_ids: Optional[List[str]] = Field(
        default=None, description="List of Star IDs to use (for dynamic mode)"
    )

    # Optional context
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context passed to all workers"
    )

    # Configuration
    config: ExecutionConfig = Field(
        default_factory=ExecutionConfig, description="Execution configuration"
    )

    # Metadata
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this execution",
    )
    user_id: Optional[str] = Field(
        default=None, description="ID of the user initiating the execution"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session ID for grouping related executions"
    )
