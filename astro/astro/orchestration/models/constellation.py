"""Constellation model - a workflow graph of Stars."""

from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, Field

from astro.orchestration.models.edge import Edge
from astro.orchestration.models.nodes import EndNode, StarNode, StartNode

if TYPE_CHECKING:
    from astro.core.models.template_variable import TemplateVariable


class Constellation(BaseModel):
    """A workflow graph of Stars."""

    # Identity
    id: str
    name: str
    description: str = Field(
        ...,
        description="Purpose of this constellation. "
        "Passed to workers as constellation_purpose for context.",
    )

    # Graph structure
    start: StartNode
    end: EndNode
    nodes: List[StarNode] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)

    # Execution constraints
    max_loop_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum times EvalStar can loop back to PlanningStar "
        "before forced 'continue'. Prevents infinite loops.",
    )
    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Max retry attempts for failed nodes in parallel execution. "
        "0 = no retries.",
    )
    retry_delay_base: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Base delay in seconds for exponential backoff between retries.",
    )

    # Extensibility
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_entry_nodes(self) -> List[StarNode]:
        """Nodes connected directly from Start."""
        start_edges = [e for e in self.edges if e.source == self.start.id]
        entry_ids = {e.target for e in start_edges}
        return [n for n in self.nodes if n.id in entry_ids]

    def get_upstream_nodes(self, node_id: str) -> List[StarNode]:
        """Get all nodes that feed into this node."""
        incoming_edges = [e for e in self.edges if e.target == node_id]
        upstream_ids = {e.source for e in incoming_edges}
        return [n for n in self.nodes if n.id in upstream_ids]

    def get_downstream_nodes(self, node_id: str) -> List[StarNode]:
        """Get all nodes this node feeds into."""
        outgoing_edges = [e for e in self.edges if e.source == node_id]
        downstream_ids = {e.target for e in outgoing_edges}
        return [n for n in self.nodes if n.id in downstream_ids]

    def topological_order(self) -> List[str]:
        """Return node IDs in execution order."""
        # Build adjacency list (excluding start/end for cleaner sorting)
        all_node_ids = [self.start.id] + [n.id for n in self.nodes] + [self.end.id]
        in_degree: Dict[str, int] = {node_id: 0 for node_id in all_node_ids}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in all_node_ids}

        for edge in self.edges:
            # Skip loop edges (from EvalStar with conditions containing 'loop')
            # This handles both condition="loop" and condition="decision == 'loop'"
            if edge.condition and "loop" in edge.condition.lower():
                continue
            if edge.source in adjacency:
                adjacency[edge.source].append(edge.target)
            if edge.target in in_degree:
                in_degree[edge.target] += 1

        # Kahn's algorithm
        queue = [node_id for node_id, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def compute_required_variables(self, foundry: Any) -> List["TemplateVariable"]:
        """Walk all nodes, resolve Stars → Directives, aggregate template_variables.

        Called at runtime before execution to show user what needs filling.

        Args:
            foundry: The Foundry/Registry instance for star/directive lookups.

        Returns:
            List of TemplateVariables with used_by tracking which nodes need them.
        """
        from astro.core.models.template_variable import TemplateVariable

        all_variables: Dict[str, TemplateVariable] = {}

        for node in self.nodes:
            star = foundry.get_star(node.star_id)
            if star is None:
                continue
            directive = foundry.get_directive(star.directive_id)
            if directive is None:
                continue

            for var in directive.template_variables:
                if var.name not in all_variables:
                    all_variables[var.name] = var.model_copy()
                    all_variables[var.name].used_by = [node.id]
                else:
                    all_variables[var.name].used_by.append(node.id)

        return list(all_variables.values())
