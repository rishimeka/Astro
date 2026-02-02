"""Output models for Star execution results."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Record of a tool invocation."""

    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None


class WorkerOutput(BaseModel):
    """Output from a WorkerStar execution."""

    result: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    iterations: int = Field(default=1, ge=1)
    status: str = Field(default="completed")  # "completed", "failed", "max_iterations"


class Task(BaseModel):
    """A single task in an execution plan."""

    id: str
    description: str
    directive_id: Optional[str] = Field(
        default=None, description="Directive to use, if known"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Task IDs this task depends on"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Output from a PlanningStar - structured execution plan."""

    tasks: List[Task]
    context: str = Field(
        default="", description="Additional context for task execution"
    )
    success_criteria: str = Field(
        default="", description="How to evaluate if the plan succeeded"
    )


class EvalDecision(BaseModel):
    """Output from an EvalStar - routing decision."""

    decision: Literal["continue", "loop"] = Field(
        ..., description="Whether to continue to next node or loop back"
    )
    reasoning: str = Field(default="", description="Explanation for the decision")
    loop_target: Optional[str] = Field(
        default=None, description="PlanningStar ID if looping"
    )


class SynthesisOutput(BaseModel):
    """Output from a SynthesisStar - aggregated and formatted result."""

    formatted_result: str
    format_type: str = Field(default="text")  # "text", "markdown", "json", etc.
    sources: List[str] = Field(
        default_factory=list, description="Star IDs that contributed to this output"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Output from an ExecutionStar - collected worker outputs."""

    worker_outputs: List[WorkerOutput] = Field(default_factory=list)
    status: str = Field(default="completed")  # "completed", "partial", "failed"
    errors: List[str] = Field(default_factory=list)


class DocumentExtraction(BaseModel):
    """Extraction result for a single document."""

    doc_id: str
    extracted_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocExResult(BaseModel):
    """Output from a DocExStar - document extraction results."""

    documents: List[DocumentExtraction] = Field(default_factory=list)
