"""Test fixtures for executor tests."""

from typing import Any

import pytest
from astro_backend_service.models import (
    Constellation,
    Directive,
    Edge,
    EndNode,
    Position,
    StarNode,
    StartNode,
    StarType,
    TemplateVariable,
    WorkerStar,
)
from astro_backend_service.models.nodes import NodeType


class MockFoundry:
    """Mock Foundry for testing without actual registry."""

    def __init__(self) -> None:
        self._constellations: dict[str, Constellation] = {}
        self._stars: dict[str, Any] = {}
        self._directives: dict[str, Directive] = {}
        self._runs: dict[str, dict[str, Any]] = {}

    def add_constellation(self, constellation: Constellation) -> None:
        self._constellations[constellation.id] = constellation

    def add_star(self, star: Any) -> None:
        self._stars[star.id] = star

    def add_directive(self, directive: Directive) -> None:
        self._directives[directive.id] = directive

    def get_constellation(self, constellation_id: str) -> Constellation | None:
        return self._constellations.get(constellation_id)

    def get_star(self, star_id: str) -> Any | None:
        return self._stars.get(star_id)

    def get_directive(self, directive_id: str) -> Directive | None:
        return self._directives.get(directive_id)

    def list_stars(self) -> list[Any]:
        return list(self._stars.values())

    def list_constellations(self) -> list[Constellation]:
        return list(self._constellations.values())

    # Run persistence methods (async to match Foundry interface)
    async def create_run(self, run_data: dict[str, Any]) -> None:
        self._runs[run_data["id"]] = run_data

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self._runs.get(run_id)

    async def update_run(self, run_id: str, updates: dict[str, Any]) -> bool:
        if run_id in self._runs:
            self._runs[run_id].update(updates)
            return True
        return False

    async def list_runs(
        self, constellation_id: str | None = None
    ) -> list[dict[str, Any]]:
        if constellation_id:
            return [
                r
                for r in self._runs.values()
                if r.get("constellation_id") == constellation_id
            ]
        return list(self._runs.values())

    # Directive/star creation methods (async to match Foundry interface)
    async def create_directive(
        self, directive: Directive
    ) -> tuple[Directive, list[Any]]:
        self._directives[directive.id] = directive
        return directive, []

    async def create_star(self, star: Any) -> tuple[Any, list[Any]]:
        self._stars[star.id] = star
        return star, []


@pytest.fixture
def mock_foundry() -> MockFoundry:
    """Create a mock foundry instance."""
    return MockFoundry()


@pytest.fixture
def simple_directive() -> Directive:
    """Create a simple directive for testing."""
    return Directive(
        id="test_directive",
        name="Test Directive",
        description="A test directive",
        content="Do something with {{company_name}}",
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Company name",
                required=True,
            )
        ],
    )


@pytest.fixture
def simple_star(simple_directive: Directive) -> WorkerStar:
    """Create a simple worker star for testing."""
    return WorkerStar(
        id="test_star",
        name="Test Star",
        type=StarType.WORKER,
        directive_id=simple_directive.id,
    )


@pytest.fixture
def simple_constellation() -> Constellation:
    """Create a simple linear constellation for testing."""
    start = StartNode(
        id="start",
        type=NodeType.START,
        position=Position(x=0, y=0),
    )
    end = EndNode(
        id="end",
        type=NodeType.END,
        position=Position(x=400, y=0),
    )
    worker_node = StarNode(
        id="worker_1",
        type=NodeType.STAR,
        position=Position(x=200, y=0),
        star_id="test_star",
        display_name=None,
    )

    return Constellation(
        id="test_constellation",
        name="Test Constellation",
        description="A test constellation",
        start=start,
        end=end,
        nodes=[worker_node],
        edges=[
            Edge(id="e1", source="start", target="worker_1", condition=None),
            Edge(id="e2", source="worker_1", target="end", condition=None),
        ],
    )


@pytest.fixture
def parallel_constellation() -> Constellation:
    """Create a constellation with parallel nodes."""
    start = StartNode(
        id="start",
        type=NodeType.START,
        position=Position(x=0, y=100),
    )
    end = EndNode(
        id="end",
        type=NodeType.END,
        position=Position(x=600, y=100),
    )
    worker_1 = StarNode(
        id="worker_1",
        type=NodeType.STAR,
        position=Position(x=200, y=0),
        star_id="star_1",
        display_name=None,
    )
    worker_2 = StarNode(
        id="worker_2",
        type=NodeType.STAR,
        position=Position(x=200, y=200),
        star_id="star_2",
        display_name=None,
    )
    synthesis = StarNode(
        id="synthesis",
        type=NodeType.STAR,
        position=Position(x=400, y=100),
        star_id="synthesis_star",
        display_name=None,
    )

    return Constellation(
        id="parallel_constellation",
        name="Parallel Constellation",
        description="A constellation with parallel execution",
        start=start,
        end=end,
        nodes=[worker_1, worker_2, synthesis],
        edges=[
            Edge(id="e1", source="start", target="worker_1", condition=None),
            Edge(id="e2", source="start", target="worker_2", condition=None),
            Edge(id="e3", source="worker_1", target="synthesis", condition=None),
            Edge(id="e4", source="worker_2", target="synthesis", condition=None),
            Edge(id="e5", source="synthesis", target="end", condition=None),
        ],
    )


@pytest.fixture
def eval_loop_constellation() -> Constellation:
    """Create a constellation with eval loop."""
    start = StartNode(
        id="start",
        type=NodeType.START,
        position=Position(x=0, y=0),
    )
    end = EndNode(
        id="end",
        type=NodeType.END,
        position=Position(x=600, y=0),
    )
    planning = StarNode(
        id="planning",
        type=NodeType.STAR,
        position=Position(x=150, y=0),
        star_id="planning_star",
        display_name=None,
    )
    worker = StarNode(
        id="worker",
        type=NodeType.STAR,
        position=Position(x=300, y=0),
        star_id="worker_star",
        display_name=None,
    )
    eval_node = StarNode(
        id="eval",
        type=NodeType.STAR,
        position=Position(x=450, y=0),
        star_id="eval_star",
        display_name=None,
    )

    return Constellation(
        id="eval_loop_constellation",
        name="Eval Loop Constellation",
        description="A constellation with eval loop",
        start=start,
        end=end,
        nodes=[planning, worker, eval_node],
        edges=[
            Edge(id="e1", source="start", target="planning", condition=None),
            Edge(id="e2", source="planning", target="worker", condition=None),
            Edge(id="e3", source="worker", target="eval", condition=None),
            Edge(id="e4", source="eval", target="end", condition="continue"),
            Edge(id="e5", source="eval", target="planning", condition="loop"),
        ],
        max_loop_iterations=3,
    )


@pytest.fixture
def hitl_constellation() -> Constellation:
    """Create a constellation with human-in-the-loop confirmation."""
    start = StartNode(
        id="start",
        type=NodeType.START,
        position=Position(x=0, y=0),
    )
    end = EndNode(
        id="end",
        type=NodeType.END,
        position=Position(x=400, y=0),
    )
    worker = StarNode(
        id="worker",
        type=NodeType.STAR,
        position=Position(x=200, y=0),
        star_id="worker_star",
        display_name=None,
        requires_confirmation=True,
        confirmation_prompt="Review the analysis. Continue?",
    )

    return Constellation(
        id="hitl_constellation",
        name="HITL Constellation",
        description="A constellation with human confirmation",
        start=start,
        end=end,
        nodes=[worker],
        edges=[
            Edge(id="e1", source="start", target="worker", condition=None),
            Edge(id="e2", source="worker", target="end", condition=None),
        ],
    )


@pytest.fixture
def hitl_multi_node_constellation() -> Constellation:
    """Create a constellation with HITL node followed by another node.

    Structure: Start -> Node A (HITL) -> Node B -> End

    This tests that execution halts at Node A and Node B does NOT execute.
    """
    start = StartNode(
        id="start",
        type=NodeType.START,
        position=Position(x=0, y=0),
    )
    end = EndNode(
        id="end",
        type=NodeType.END,
        position=Position(x=600, y=0),
    )
    node_a = StarNode(
        id="node_a",
        type=NodeType.STAR,
        position=Position(x=200, y=0),
        star_id="worker_star",
        display_name="Node A (HITL)",
        requires_confirmation=True,
        confirmation_prompt="Approve Node A output?",
    )
    node_b = StarNode(
        id="node_b",
        type=NodeType.STAR,
        position=Position(x=400, y=0),
        star_id="worker_star",
        display_name="Node B",
        requires_confirmation=False,
    )

    return Constellation(
        id="hitl_multi_node",
        name="HITL Multi-Node",
        description="Test that HITL halts execution before downstream nodes",
        start=start,
        end=end,
        nodes=[node_a, node_b],
        edges=[
            Edge(id="e1", source="start", target="node_a", condition=None),
            Edge(id="e2", source="node_a", target="node_b", condition=None),
            Edge(id="e3", source="node_b", target="end", condition=None),
        ],
    )
