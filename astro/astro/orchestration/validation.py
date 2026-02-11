"""Validation logic for orchestration primitives (Stars and Constellations).

This module contains validation for Layer 2 (orchestration) primitives only.
Directive and Probe validation belong in astro.core.registry.validation.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Set

from astro.orchestration.models import Constellation, StarType
from astro.orchestration.stars.base import AtomicStar, BaseStar

if TYPE_CHECKING:
    from astro.core.registry.indexes import RegistryIndexes as FoundryIndexes


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


def validate_star(
    star: BaseStar,
    indexes: "FoundryIndexes",
) -> List[ValidationWarning]:
    """Validate a star.

    Args:
        star: The star to validate
        indexes: Current foundry/registry indexes

    Returns:
        List of validation warnings.

    Raises:
        ValidationError: For fatal validation errors.
    """
    warnings: List[ValidationWarning] = []

    # Check directive exists
    if star.directive_id not in indexes.directives:
        raise ValidationError(
            f"Star '{star.id}' references Directive '{star.directive_id}' "
            "which doesn't exist"
        )

    # Check probe_ids exist (for AtomicStar)
    if isinstance(star, AtomicStar):
        for probe_id in star.probe_ids:
            if not indexes.probe_exists(probe_id):
                warnings.append(
                    ValidationWarning(
                        f"Star '{star.id}' references Probe '{probe_id}' "
                        "which isn't registered"
                    )
                )

    return warnings


def validate_constellation(
    constellation: Constellation,
    indexes: "FoundryIndexes",
) -> List[ValidationWarning]:
    """Validate constellation graph structure and star relationships.

    Args:
        constellation: The constellation to validate
        indexes: Current foundry/registry indexes

    Returns:
        List of validation warnings.

    Raises:
        ValidationError: For fatal validation errors.
    """
    warnings: List[ValidationWarning] = []

    # Basic structure checks
    if not constellation.start:
        raise ValidationError("Constellation must have a start node")
    if not constellation.end:
        raise ValidationError("Constellation must have an end node")

    # Check for incoming edges to start
    for edge in constellation.edges:
        if edge.target == constellation.start.id:
            raise ValidationError("Start node cannot have incoming edges")
        if edge.source == constellation.end.id:
            raise ValidationError("End node cannot have outgoing edges")

    # Check all star_ids exist
    for node in constellation.nodes:
        if node.star_id not in indexes.stars:
            raise ValidationError(
                f"Node '{node.id}' references Star '{node.star_id}' "
                "which doesn't exist"
            )

    # Check for orphan nodes
    connected_ids: Set[str] = set()
    for edge in constellation.edges:
        connected_ids.add(edge.source)
        connected_ids.add(edge.target)

    for node in constellation.nodes:
        if node.id not in connected_ids:
            raise ValidationError(f"Node '{node.id}' has no connections")

    # Check for cycles (except EvalStar loops)
    cycle_path = _detect_cycle(constellation, indexes)
    if cycle_path:
        raise ValidationError(
            f"Cycle detected: {cycle_path}. Only EvalStar can route backwards."
        )

    # Validate star type relationships
    relationship_warnings = _validate_star_relationships(constellation, indexes)
    warnings.extend(relationship_warnings)

    # Validate EvalStar edges have conditions
    _validate_eval_star_edges(constellation, indexes)

    # Validate confirmation nodes
    confirmation_warnings = validate_confirmation_nodes(constellation, indexes)
    warnings.extend(confirmation_warnings)

    return warnings


def _detect_cycle(
    constellation: Constellation,
    indexes: "FoundryIndexes",
) -> Optional[str]:
    """Detect cycles in constellation graph.

    EvalStar loop edges (condition='loop') are allowed and excluded from check.

    Returns:
        Path string if cycle found, None otherwise.
    """
    # Build adjacency list excluding loop edges
    all_node_ids = (
        [constellation.start.id]
        + [n.id for n in constellation.nodes]
        + [constellation.end.id]
    )
    adjacency: Dict[str, List[str]] = {node_id: [] for node_id in all_node_ids}

    for edge in constellation.edges:
        # Skip loop edges from EvalStar
        if edge.condition == "loop":
            continue
        if edge.source in adjacency:
            adjacency[edge.source].append(edge.target)

    # DFS for cycle detection
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found cycle - add the neighbor to show the loop
                path.append(neighbor)
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    for node_id in all_node_ids:
        if node_id not in visited:
            if has_cycle(node_id):
                return " -> ".join(path)

    return None


def _validate_star_relationships(
    constellation: Constellation,
    indexes: "FoundryIndexes",
) -> List[ValidationWarning]:
    """Validate star type relationships in constellation."""
    warnings: List[ValidationWarning] = []

    # Build node -> star type mapping
    node_star_type: Dict[str, StarType] = {}
    for node in constellation.nodes:
        star = indexes.get_star(node.star_id)
        if star:
            node_star_type[node.id] = star.type

    # Build adjacency (forward edges only, no loops)
    forward_edges: Dict[str, List[str]] = {n.id: [] for n in constellation.nodes}
    forward_edges[constellation.start.id] = []
    forward_edges[constellation.end.id] = []

    backward_edges: Dict[str, List[str]] = {n.id: [] for n in constellation.nodes}
    backward_edges[constellation.start.id] = []
    backward_edges[constellation.end.id] = []

    for edge in constellation.edges:
        if edge.condition != "loop":
            if edge.source in forward_edges:
                forward_edges[edge.source].append(edge.target)
            if edge.target in backward_edges:
                backward_edges[edge.target].append(edge.source)

    # Get entry nodes (from start)
    entry_node_ids = set(forward_edges.get(constellation.start.id, []))

    for node in constellation.nodes:
        star_type = node_star_type.get(node.id)
        if not star_type:
            continue

        downstream = forward_edges.get(node.id, [])
        upstream = backward_edges.get(node.id, [])

        # PlanningStar must have ExecutionStar downstream
        if star_type == StarType.PLANNING:
            has_execution_downstream = any(
                node_star_type.get(d) == StarType.EXECUTION for d in downstream
            )
            if not has_execution_downstream:
                raise ValidationError(
                    f"PlanningStar '{node.id}' must connect to an ExecutionStar"
                )

        # ExecutionStar must have PlanningStar upstream
        if star_type == StarType.EXECUTION:
            has_planning_upstream = any(
                node_star_type.get(u) == StarType.PLANNING for u in upstream
            )
            if not has_planning_upstream:
                raise ValidationError(
                    f"ExecutionStar '{node.id}' requires a PlanningStar upstream"
                )

        # SynthesisStar cannot be entry point
        if star_type == StarType.SYNTHESIS:
            if node.id in entry_node_ids:
                raise ValidationError(
                    f"SynthesisStar '{node.id}' cannot be entry point — "
                    "must have upstream"
                )
            # SynthesisStar must have upstream
            if not upstream or all(u == constellation.start.id for u in upstream):
                raise ValidationError(
                    f"SynthesisStar '{node.id}' must have at least one upstream Star"
                )

        # EvalStar must have PlanningStar in constellation for loop routing
        if star_type == StarType.EVAL:
            has_planning_in_constellation = any(
                node_star_type.get(n.id) == StarType.PLANNING
                for n in constellation.nodes
            )
            if not has_planning_in_constellation:
                raise ValidationError(
                    f"EvalStar '{node.id}' must have PlanningStar in Constellation "
                    "for loop routing"
                )

    # Warning: ExecutionStar without downstream SynthesisStar
    for node in constellation.nodes:
        star_type = node_star_type.get(node.id)
        if star_type == StarType.EXECUTION:
            downstream = forward_edges.get(node.id, [])
            has_synthesis_downstream = any(
                node_star_type.get(d) == StarType.SYNTHESIS for d in downstream
            )
            if not has_synthesis_downstream:
                warnings.append(
                    ValidationWarning(
                        f"ExecutionStar '{node.id}' has no SynthesisStar "
                        "to aggregate results"
                    )
                )

    return warnings


def _validate_eval_star_edges(
    constellation: Constellation,
    indexes: "FoundryIndexes",
) -> None:
    """Validate EvalStar edges have conditions, others don't."""
    # Build node -> star type mapping
    node_star_type: Dict[str, StarType] = {}
    for node in constellation.nodes:
        star = indexes.get_star(node.star_id)
        if star:
            node_star_type[node.id] = star.type

    for edge in constellation.edges:
        source_type = node_star_type.get(edge.source)

        if source_type == StarType.EVAL:
            # EvalStar edges must have condition
            if edge.condition is None:
                raise ValidationError(
                    f"Edge from EvalStar '{edge.source}' must have condition "
                    "('continue' or 'loop')"
                )
            # Loop edge must target PlanningStar
            if edge.condition == "loop":
                target_type = node_star_type.get(edge.target)
                if target_type != StarType.PLANNING:
                    raise ValidationError(
                        f"EvalStar loop edge must target a PlanningStar, "
                        f"not '{edge.target}'"
                    )
        else:
            # Non-EvalStar edges must not have condition
            if edge.condition is not None:
                raise ValidationError(
                    f"Only EvalStar edges can have conditions, "
                    f"but edge from '{edge.source}' has condition '{edge.condition}'"
                )


def validate_confirmation_nodes(
    constellation: Constellation,
    indexes: "FoundryIndexes",
) -> List[ValidationWarning]:
    """Validate confirmation nodes have proper prompts.

    Returns warnings for nodes that require confirmation but lack prompts.
    """
    warnings: List[ValidationWarning] = []

    for node in constellation.nodes:
        if node.requires_confirmation and not node.confirmation_prompt:
            warnings.append(
                ValidationWarning(
                    f"Node '{node.id}' requires confirmation but has no "
                    "confirmation_prompt defined"
                )
            )

    return warnings
