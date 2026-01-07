"""Constellation models for the Astro Execution Engine.

This module defines the Constellation workflow graph structure,
including nodes and edges that define execution paths.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ConstellationNode(BaseModel):
    """A node in a Constellation graph."""

    node_id: str = Field(description="Unique identifier for this node")
    star_id: str = Field(description="ID of the Star to use at this node")

    # Worker configuration
    worker_name: Optional[str] = Field(
        default=None, description="Human-readable name for the worker at this node"
    )
    task_description: Optional[str] = Field(
        default=None, description="Specific task description for this node"
    )

    # Conditional execution
    condition: Optional[str] = Field(
        default=None,
        description="Python expression evaluated at runtime to determine if node should execute",
    )
    skip_on_failure: bool = Field(
        default=False, description="Whether to skip this node if a dependency fails"
    )


class ConstellationEdge(BaseModel):
    """An edge in a Constellation graph."""

    from_node: str = Field(description="ID of the source node")
    to_node: str = Field(description="ID of the target node")

    # Edge type
    edge_type: str = Field(
        default="sequential",
        description="Type of edge: 'sequential', 'parallel', or 'conditional'",
    )
    condition: Optional[str] = Field(
        default=None, description="Condition for conditional edges"
    )


class Constellation(BaseModel):
    """A workflow graph of Stars.

    Constellations define the execution structure for multi-phase
    AI workflows, specifying which Stars to use and in what order.
    """

    id: str = Field(description="Unique identifier for this constellation")
    name: str = Field(description="Human-readable name")
    description: str = Field(
        default="", description="Description of what this constellation does"
    )

    # Graph structure
    nodes: List[ConstellationNode] = Field(
        default_factory=list, description="Nodes in the constellation graph"
    )
    edges: List[ConstellationEdge] = Field(
        default_factory=list, description="Edges connecting nodes"
    )

    # Entry and exit
    entry_node: str = Field(description="ID of the entry node")
    exit_nodes: List[str] = Field(
        default_factory=list, description="IDs of valid exit nodes"
    )

    # Metadata
    version: str = Field(default="1.0.0", description="Version of this constellation")
    created_by: str = Field(default="", description="Creator of this constellation")
    created_on: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this constellation was created",
    )

    def get_node(self, node_id: str) -> Optional[ConstellationNode]:
        """Get a node by its ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_outgoing_edges(self, node_id: str) -> List[ConstellationEdge]:
        """Get all edges originating from a node."""
        return [edge for edge in self.edges if edge.from_node == node_id]

    def get_incoming_edges(self, node_id: str) -> List[ConstellationEdge]:
        """Get all edges pointing to a node."""
        return [edge for edge in self.edges if edge.to_node == node_id]

    def topological_sort(self) -> List[List[str]]:
        """Sort nodes into execution phases based on dependencies.

        Returns a list of phases, where each phase is a list of node IDs
        that can be executed in parallel.
        """
        # Build adjacency and in-degree maps
        in_degree = {node.node_id: 0 for node in self.nodes}
        adjacency = {node.node_id: [] for node in self.nodes}

        for edge in self.edges:
            if edge.from_node in adjacency and edge.to_node in in_degree:
                adjacency[edge.from_node].append(edge.to_node)
                in_degree[edge.to_node] += 1

        # Kahn's algorithm with phase grouping
        phases = []
        current_phase = [nid for nid, deg in in_degree.items() if deg == 0]

        while current_phase:
            phases.append(current_phase)
            next_phase = []

            for node_id in current_phase:
                for neighbor in adjacency[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_phase.append(neighbor)

            current_phase = next_phase

        return phases
