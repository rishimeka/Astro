"""Validation logic for Layer 1 primitives (Directives and Probes only).

Layer 1 validation only covers Directives and Probes.
Stars and Constellations are Layer 2 concepts - their validation
belongs in astro.orchestration.validation.
"""

from typing import TYPE_CHECKING

from astro.core.models.directive import Directive

if TYPE_CHECKING:
    from astro.core.registry.indexes import RegistryIndexes


class ValidationError(Exception):
    """Raised when validation fails with a fatal error."""

    pass


class ValidationWarning:
    """Non-fatal validation issue."""

    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"ValidationWarning({self.message!r})"


def validate_directive(
    directive: Directive,
    indexes: "RegistryIndexes",
    existing_id: str | None = None,
) -> list[ValidationWarning]:
    """
    Validate a directive.

    Args:
        directive: The directive to validate
        indexes: Current registry indexes for reference checking
        existing_id: If updating, the ID being updated (for cycle detection)

    Returns:
        List of validation warnings.

    Raises:
        ValidationError: For fatal validation errors.
    """
    warnings: list[ValidationWarning] = []

    # Check for empty description
    if not directive.description or not directive.description.strip():
        raise ValidationError(
            f"Directive '{directive.id}' has no description (required for planner)"
        )

    # Check for empty content
    if not directive.content or not directive.content.strip():
        raise ValidationError(
            f"Directive '{directive.id}' has no content (nothing to give worker)"
        )

    # Check for missing probe references
    for probe_id in directive.probe_ids:
        if not indexes.probe_exists(probe_id):
            warnings.append(
                ValidationWarning(
                    f"Directive '{directive.id}' references probe '{probe_id}' "
                    "which isn't registered"
                )
            )

    # Check for missing directive references
    for ref_id in directive.reference_ids:
        if ref_id not in indexes.directives:
            warnings.append(
                ValidationWarning(
                    f"Directive '{directive.id}' references '{ref_id}' "
                    "which doesn't exist"
                )
            )

    # Check for cycles in reference_ids
    if _has_directive_cycle(directive, indexes, existing_id):
        raise ValidationError(
            f"Directive '{directive.id}' creates a cycle in reference_ids"
        )

    return warnings


def _has_directive_cycle(
    directive: Directive,
    indexes: "RegistryIndexes",
    existing_id: str | None = None,
) -> bool:
    """
    Check if adding/updating this directive would create a cycle.

    Uses DFS to detect cycles in the directive reference graph.

    Args:
        directive: The directive being added/updated
        indexes: Current registry indexes
        existing_id: If updating, the ID being updated

    Returns:
        True if a cycle would be created, False otherwise
    """
    # Build a temporary graph including the new directive
    graph: dict[str, list[str]] = {}

    # Add existing directives
    for d_id, d in indexes.directives.items():
        # Skip the directive being updated (we'll use the new version)
        if existing_id and d_id == existing_id:
            continue
        graph[d_id] = list(d.reference_ids)

    # Add the new/updated directive
    graph[directive.id] = list(directive.reference_ids)

    # DFS for cycle detection
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    # Check starting from the new directive
    return has_cycle(directive.id)
