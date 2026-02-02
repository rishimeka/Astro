"""Generic constellation for handling unmatched queries."""

from typing import Any, Optional

# Cache for the generic constellation
_generic_constellation: Optional[Any] = None


def create_generic_constellation(foundry: Any) -> Any:
    """Create the generic constellation for fallback handling.

    Structure:
        StartNode
            ↓
        PlanningStar (creates plan from rich context)
            ↓
        ExecutionStar (spawns workers, creates Stars/Directives as needed)
            ↓
        SynthesisStar (formats output)
            ↓
        EndNode

    Args:
        foundry: The Foundry instance for creating and registering.

    Returns:
        The created Constellation.
    """
    from astro_backend_service.models import (
        Constellation,
        Directive,
        Edge,
        EndNode,
        ExecutionStar,
        NodeType,
        PlanningStar,
        Position,
        StarNode,
        StartNode,
        StarType,
        SynthesisStar,
        TemplateVariable,
    )

    # Create directives for each star
    planning_directive = Directive(
        id="_generic_planning_directive",
        name="Generic Planning",
        description="Create an execution plan for the user's query",
        content="""You are a planning agent. Given the user's query and context,
create a structured plan to address their request.

Consider:
- The original query and any clarifications
- Similar constellations and why they weren't triggered
- Available probes/tools suggested
- Break down into clear, actionable tasks

Output a plan with tasks, success criteria, and any context needed for execution.""",
        template_variables=[
            TemplateVariable(
                name="query_context",
                description="Rich context from triggering agent",
                required=True,
            )
        ],
        metadata={"hidden": True, "ai_internal": True},
    )

    execution_directive = Directive(
        id="_generic_execution_directive",
        name="Generic Execution",
        description="Execute the plan by spawning workers",
        content="""You are an execution agent. Given a plan, spawn workers
to complete each task. You may create new Stars and Directives as needed.

Mark any created Stars with ai_generated=True.""",
        template_variables=[],
        metadata={"hidden": True, "ai_internal": True},
    )

    synthesis_directive = Directive(
        id="_generic_synthesis_directive",
        name="Generic Synthesis",
        description="Format and synthesize execution results",
        content="""You are a synthesis agent. Given the execution results,
create a coherent, well-formatted response for the user.

Apply any user preferences for tone, format, and length.""",
        template_variables=[],
        metadata={"hidden": True, "ai_internal": True},
    )

    # Create stars
    planning_star = PlanningStar(
        id="_generic_planning_star",
        name="Generic Planner",
        type=StarType.PLANNING,
        directive_id=planning_directive.id,
        metadata={"hidden": True},
    )

    execution_star = ExecutionStar(
        id="_generic_execution_star",
        name="Generic Executor",
        type=StarType.EXECUTION,
        directive_id=execution_directive.id,
        metadata={"hidden": True},
    )

    synthesis_star = SynthesisStar(
        id="_generic_synthesis_star",
        name="Generic Synthesizer",
        type=StarType.SYNTHESIS,
        directive_id=synthesis_directive.id,
        metadata={"hidden": True},
    )

    # Create nodes - use NodeType enum values
    start_node = StartNode(
        id="_generic_start",
        type=NodeType.START,
        position=Position(x=0, y=100),
    )

    end_node = EndNode(
        id="_generic_end",
        type=NodeType.END,
        position=Position(x=800, y=100),
    )

    planning_node = StarNode(  # type: ignore[call-arg]
        id="_generic_planning_node",
        type=NodeType.STAR,
        position=Position(x=200, y=100),
        star_id=planning_star.id,
    )

    execution_node = StarNode(  # type: ignore[call-arg]
        id="_generic_execution_node",
        type=NodeType.STAR,
        position=Position(x=400, y=100),
        star_id=execution_star.id,
    )

    synthesis_node = StarNode(  # type: ignore[call-arg]
        id="_generic_synthesis_node",
        type=NodeType.STAR,
        position=Position(x=600, y=100),
        star_id=synthesis_star.id,
    )

    # Create edges - condition is optional with default None
    edges = [
        Edge(id="_ge1", source=start_node.id, target=planning_node.id),  # type: ignore[call-arg]
        Edge(id="_ge2", source=planning_node.id, target=execution_node.id),  # type: ignore[call-arg]
        Edge(id="_ge3", source=execution_node.id, target=synthesis_node.id),  # type: ignore[call-arg]
        Edge(id="_ge4", source=synthesis_node.id, target=end_node.id),  # type: ignore[call-arg]
    ]

    # Create constellation
    constellation = Constellation(
        id="_generic_constellation",
        name="Generic Query Handler",
        description="Handles queries that don't match any specific constellation",
        start=start_node,
        end=end_node,
        nodes=[planning_node, execution_node, synthesis_node],
        edges=edges,
        metadata={"hidden": True, "ai_internal": True},
    )

    # Register with foundry if available
    # WAITING ON WORKER 1: Foundry registration methods
    if hasattr(foundry, "register_directive"):
        foundry.register_directive(planning_directive)
        foundry.register_directive(execution_directive)
        foundry.register_directive(synthesis_directive)

    if hasattr(foundry, "register_star"):
        foundry.register_star(planning_star)
        foundry.register_star(execution_star)
        foundry.register_star(synthesis_star)

    if hasattr(foundry, "register_constellation"):
        foundry.register_constellation(constellation)

    return constellation


def get_or_create_generic_constellation(foundry: Any) -> Any:
    """Get the generic constellation, creating it if needed.

    This is the main entry point for accessing the generic constellation.

    Args:
        foundry: The Foundry instance.

    Returns:
        The generic Constellation.
    """
    global _generic_constellation

    # Check if already cached
    if _generic_constellation is not None:
        return _generic_constellation

    # Check if already registered in foundry
    if hasattr(foundry, "get_constellation"):
        existing = foundry.get_constellation("_generic_constellation")
        if existing is not None:
            _generic_constellation = existing
            return existing

    # Create new
    _generic_constellation = create_generic_constellation(foundry)
    return _generic_constellation


def clear_generic_constellation_cache() -> None:
    """Clear the cached generic constellation. Useful for testing."""
    global _generic_constellation
    _generic_constellation = None
