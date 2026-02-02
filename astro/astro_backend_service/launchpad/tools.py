"""Launchpad-specific tools for the triggering agent."""

from typing import Any, Dict, List, Optional

from astro_backend_service.probes import probe


@probe
def invoke_constellation(constellation_id: str, variables: str) -> str:
    """Execute a specific constellation with the given variables.

    Note: This probe is available for LLM tool use. The primary execution path
    is through TriggeringAgent._invoke_constellation() which uses the Foundry
    instance from the agent context.

    Args:
        constellation_id: The ID of the constellation to execute.
        variables: JSON-encoded string of variables to pass.

    Returns:
        The constellation execution output.
    """
    import json

    # Parse variables from JSON string (LLM will pass as string)
    try:
        parsed_vars: Dict[str, Any] = json.loads(variables) if variables else {}
    except json.JSONDecodeError:
        parsed_vars = {}

    # This probe is for LLM direct use - returns instruction for actual execution
    # The main execution path uses TriggeringAgent._invoke_constellation() with Foundry
    return (
        f"Invoke constellation '{constellation_id}' with variables: {parsed_vars}. "
        f"Use TriggeringAgent for actual execution with Foundry context."
    )


@probe
def invoke_generic_constellation(
    original_query: str,
    clarifications: str,
    similar_constellation_context: str,
    why_not_triggered: str,
    suggested_probes: str,
) -> str:
    """Execute the generic planning/execution flow.

    This is called when no specific constellation matches the user's query.

    Note: This probe is available for LLM tool use. The primary execution path
    is through TriggeringAgent._invoke_generic_constellation() which uses the
    Foundry instance from the agent context.

    Args:
        original_query: The user's original request.
        clarifications: JSON array of Q&A gathered from conversation.
        similar_constellation_context: Output from analyze_constellation if relevant.
        why_not_triggered: Explanation of why existing constellation wasn't used.
        suggested_probes: JSON array of tool names the planning agent should consider.

    Returns:
        The generic constellation output.
    """
    import json

    try:
        parsed_clarifications: List[str] = (
            json.loads(clarifications) if clarifications else []
        )
    except json.JSONDecodeError:
        parsed_clarifications = []

    try:
        parsed_probes: List[str] = (
            json.loads(suggested_probes) if suggested_probes else []
        )
    except json.JSONDecodeError:
        parsed_probes = []

    context = {
        "original_query": original_query,
        "clarifications": parsed_clarifications,
        "similar_context": similar_constellation_context,
        "why_not_triggered": why_not_triggered,
        "suggested_probes": parsed_probes,
    }

    # This probe is for LLM direct use - returns instruction for actual execution
    # The main execution path uses TriggeringAgent._invoke_generic_constellation() with Foundry
    return (
        f"Invoke generic constellation with context: {context}. "
        f"Use TriggeringAgent for actual execution with Foundry context."
    )


def analyze_constellation(constellation_id: str, foundry: Any) -> str:
    """Get detailed breakdown of a constellation.

    No LLM call — just structured data retrieval and markdown formatting.

    Args:
        constellation_id: The constellation ID to analyze.
        foundry: The Foundry instance for lookups.

    Returns:
        Markdown with description, required variables, flow, and graph structure.
    """
    constellation = foundry.get_constellation(constellation_id)
    if constellation is None:
        return f"Constellation '{constellation_id}' not found."

    md = f"## {constellation.name}\n\n"
    md += f"**Description:** {constellation.description}\n\n"

    # Required variables
    md += "### Required Variables\n"
    try:
        variables = constellation.compute_required_variables(foundry)
        if variables:
            for var in variables:
                required_str = "(required)" if var.required else "(optional)"
                ui_hint = var.ui_hint or "text"
                md += f"- `{var.name}` ({ui_hint}) {required_str}: {var.description}\n"
        else:
            md += "None\n"
    except Exception:
        md += "Unable to compute variables\n"

    # Flow
    md += "\n### Execution Flow\n"
    try:
        for node_id in constellation.topological_order():
            # Find the node
            node = None
            if node_id == constellation.start.id:
                md += "- **Start**\n"
                continue
            if node_id == constellation.end.id:
                md += "- **End**\n"
                continue

            for n in constellation.nodes:
                if n.id == node_id:
                    node = n
                    break

            if node:
                star = foundry.get_star(node.star_id)
                if star:
                    directive = foundry.get_directive(star.directive_id)
                    display = node.display_name or star.name
                    md += f"- **{display}** ({star.type.value})\n"
                    if directive:
                        md += f"  {directive.description}\n"
                else:
                    md += f"- **{node.id}** (star not found)\n"
    except Exception as e:
        md += f"Unable to compute flow: {e}\n"

    # Graph structure
    md += "\n### Graph Structure\n```\n"
    md += _format_edges_as_ascii(constellation)
    md += "\n```\n"

    return md


def _format_edges_as_ascii(constellation: Any) -> str:
    """Format constellation edges as ASCII graph."""
    lines = []
    for edge in constellation.edges:
        condition = f" [{edge.condition}]" if edge.condition else ""
        lines.append(f"{edge.source} --> {edge.target}{condition}")
    return "\n".join(lines) if lines else "(no edges)"


def get_constellation_summary(
    constellation_id: str, foundry: Any
) -> Optional[Dict[str, Any]]:
    """Get a summary of a constellation for matching.

    Args:
        constellation_id: The constellation ID.
        foundry: The Foundry instance.

    Returns:
        Dict with id, name, description, required_variables, or None if not found.
    """
    constellation = foundry.get_constellation(constellation_id)
    if constellation is None:
        return None

    try:
        variables = constellation.compute_required_variables(foundry)
        var_info = [
            {
                "name": v.name,
                "required": v.required,
                "description": v.description,
                "default": v.default,
            }
            for v in variables
        ]
    except Exception:
        var_info = []

    return {
        "id": constellation.id,
        "name": constellation.name,
        "description": constellation.description,
        "required_variables": var_info,
    }
