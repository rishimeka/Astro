"""Directive model - the core unit of agent behavior."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from astro.core.models.template_variable import TemplateVariable


class Directive(BaseModel):
    """A Directive defines agent behavior through progressive disclosure.

    Directives are the core unit of agent behavior in Astro. They define:
    - What the agent should do (description for discovery)
    - How the agent should do it (content for execution)
    - Which tools the agent can use (probe_ids)
    - Which sub-directives can be delegated to (reference_ids)
    - What variables need to be filled at runtime (template_variables)

    The description is shown to planners/interpreters for routing decisions.
    The content is the full system prompt given to execution agents.
    """

    # Identity
    id: str = Field(..., description="Unique identifier, e.g. 'financial_analysis'")
    name: str = Field(
        ..., description="Human-readable name, e.g. 'Financial Analysis'"
    )

    # Progressive disclosure
    description: str = Field(
        ...,
        description="Short summary (1-2 sentences) for discovery. "
        "This is what planners/interpreters see when selecting directives.",
    )
    content: str = Field(
        ...,
        description="Full system prompt for execution. "
        "Can be lengthy — includes instructions, examples, constraints, output format. "
        "Uses @ syntax for references (see extractor.py).",
    )

    # Relationships (extracted from content @ references)
    probe_ids: List[str] = Field(
        default_factory=list,
        description="List of probe names this directive can use. "
        "Agent only gets these tools, nothing else. "
        "Extracted from @probe:name references in content.",
    )
    reference_ids: List[str] = Field(
        default_factory=list,
        description="IDs of sub-directives available for delegation. "
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
