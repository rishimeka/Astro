"""Directive model - the core unit of agent behavior."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from astro_backend_service.models.template_variable import TemplateVariable


class Directive(BaseModel):
    """
    A Directive defines agent behavior through progressive disclosure.

    The description is shown to planners for routing decisions.
    The content is the full system prompt given to workers.
    """

    # Identity
    id: str = Field(..., description="Unique identifier, e.g. 'ic_memo_exec_summary'")
    name: str = Field(
        ..., description="Human-readable name, e.g. 'Executive Summary Slide'"
    )

    # Progressive disclosure
    description: str = Field(
        ...,
        description="Short summary (1-2 sentences) for planner discovery. "
        "This is what the planning agent sees when deciding how to route.",
    )
    content: str = Field(
        ...,
        description="Full system prompt injected into worker agent. "
        "Can be lengthy — includes instructions, examples, constraints, output format. "
        "Uses @ syntax for references (see below).",
    )

    # Relationships (extracted from content @ references)
    probe_ids: List[str] = Field(
        default_factory=list,
        description="List of probe names this directive can use. "
        "Worker agent only gets these tools, nothing else. "
        "Extracted from @probe:name references in content.",
    )
    reference_ids: List[str] = Field(
        default_factory=list,
        description="IDs of child directives available for sub-delegation. "
        "Planner sees these for spawning additional workers. "
        "Extracted from @directive:id references in content.",
    )
    template_variables: List[TemplateVariable] = Field(
        default_factory=list,
        description="Variables that must be filled at runtime. "
        "Extracted from @variable:name references in content. "
        "Propagates up to Constellation for user input.",
    )

    # Extensibility
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tags, author, created_at, domain, etc. "
        "Useful for filtering/search in Launchpad UI.",
    )
