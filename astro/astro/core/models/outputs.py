"""Output models for execution results.

This module contains foundational output types used by both Layer 1 (core)
and Layer 2 (orchestration). Layer 2-specific outputs (Plan, EvalDecision, etc.)
will be in orchestration/models/outputs.py.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Record of a tool invocation.

    Captures both the input (tool_name, arguments) and output (result or error)
    of a single tool call during execution.
    """

    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None


class WorkerOutput(BaseModel):
    """Output from a worker execution.

    This is the foundational output type for any execution that uses tools
    and operates in a ReAct loop. Used by both zero-shot execution (Layer 3)
    and WorkerStar (Layer 2).
    """

    result: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    iterations: int = Field(default=1, ge=1)
    status: str = Field(default="completed")  # "completed", "failed", "max_iterations"
