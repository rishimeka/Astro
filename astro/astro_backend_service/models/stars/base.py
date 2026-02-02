"""Base Star classes - abstract foundations for all Star types."""

from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, Field

from astro_backend_service.models.star_types import StarType

if TYPE_CHECKING:
    from astro_backend_service.models.directive import Directive


class ValidationError(Exception):
    """Raised when Star validation fails."""

    pass


class BaseStar(ABC, BaseModel):
    """Abstract base for all Star types."""

    # Identity
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    type: StarType = Field(..., description="Execution pattern")

    # Relationships
    directive_id: str = Field(
        ..., description="ID of Directive providing prompt content"
    )

    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)

    # Lineage
    ai_generated: bool = Field(
        default=False, description="True if created by planning agent at runtime"
    )

    # Extensibility
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def validate_star(self) -> List[str]:
        """
        Validate Star configuration. Override to add type-specific rules.

        Returns list of error messages. Empty list means valid.
        Full validation logic implemented in Foundry.
        """
        errors: List[str] = []
        # Common validation: directive exists, etc. (done by Foundry)
        return errors


class AtomicStar(BaseStar):
    """
    Stars that make direct LLM calls.
    Can have probes and consume upstream outputs.
    """

    probe_ids: List[str] = Field(
        default_factory=list,
        description="Additional probes beyond Directive. "
        "Final set = Directive.probe_ids ∪ Star.probe_ids",
    )

    def resolve_probes(self, directive: "Directive") -> List[str]:
        """Compute final probe set (deduplicated)."""
        return list(set(directive.probe_ids + self.probe_ids))


class OrchestratorStar(BaseStar):
    """
    Stars that spawn and manage worker Stars.
    Do not make direct LLM calls themselves.
    """

    # No probe_ids — workers have probes, not orchestrators
    pass
