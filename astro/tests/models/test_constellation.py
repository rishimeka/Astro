"""Tests for Constellation model."""

import pytest

from astro_backend_service.models import (
    Constellation,
    Edge,
    Position,
    StartNode,
    EndNode,
    StarNode,
)


class TestConstellation:
    """Test Constellation model."""

    @pytest.fixture
    def simple_constellation(self):
        """Create a simple constellation for testing."""
        start = StartNode(id="start", position=Position(x=0, y=200))
        end = EndNode(id="end", position=Position(x=1000, y=200))
        nodes = [
            StarNode(id="n1", star_id="s1", position=Position(x=200, y=200)),
            StarNode(id="n2", star_id="s2", position=Position(x=400, y=200)),
            StarNode(id="n3", star_id="s3", position=Position(x=600, y=200)),
        ]
        edges = [
            Edge(id="e1", source="start", target="n1"),
            Edge(id="e2", source="n1", target="n2"),
            Edge(id="e3", source="n2", target="n3"),
            Edge(id="e4", source="n3", target="end"),
        ]
        return Constellation(
            id="test_constellation",
            name="Test Constellation",
            description="A test workflow",
            start=start,
            end=end,
            nodes=nodes,
            edges=edges,
        )

    def test_minimal_instantiation(self):
        """Test creating Constellation with required fields."""
        constellation = Constellation(
            id="c1",
            name="Simple Workflow",
            description="A simple workflow",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
        )
        assert constellation.id == "c1"
        assert constellation.nodes == []
        assert constellation.edges == []
        assert constellation.max_loop_iterations == 3
        assert constellation.max_retry_attempts == 3
        assert constellation.retry_delay_base == 2.0

    def test_full_instantiation(self, simple_constellation):
        """Test creating full Constellation."""
        c = simple_constellation
        assert len(c.nodes) == 3
        assert len(c.edges) == 4

    def test_get_entry_nodes(self, simple_constellation):
        """Test get_entry_nodes method."""
        entry = simple_constellation.get_entry_nodes()
        assert len(entry) == 1
        assert entry[0].id == "n1"

    def test_get_upstream_nodes(self, simple_constellation):
        """Test get_upstream_nodes method."""
        upstream = simple_constellation.get_upstream_nodes("n2")
        assert len(upstream) == 1
        assert upstream[0].id == "n1"

    def test_get_downstream_nodes(self, simple_constellation):
        """Test get_downstream_nodes method."""
        downstream = simple_constellation.get_downstream_nodes("n2")
        assert len(downstream) == 1
        assert downstream[0].id == "n3"

    def test_topological_order(self, simple_constellation):
        """Test topological_order method."""
        order = simple_constellation.topological_order()
        # start should come first, end should come last
        assert order[0] == "start"
        assert order[-1] == "end"
        # n1 should come before n2, n2 before n3
        assert order.index("n1") < order.index("n2")
        assert order.index("n2") < order.index("n3")

    def test_topological_order_with_loop_edge(self):
        """Test topological order ignores loop edges."""
        constellation = Constellation(
            id="c1",
            name="Loop Workflow",
            description="Workflow with eval loop",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=500, y=0)),
            nodes=[
                StarNode(id="plan", star_id="s1", position=Position(x=100, y=0)),
                StarNode(id="exec", star_id="s2", position=Position(x=200, y=0)),
                StarNode(id="eval", star_id="s3", position=Position(x=300, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="plan"),
                Edge(id="e2", source="plan", target="exec"),
                Edge(id="e3", source="exec", target="eval"),
                Edge(id="e4", source="eval", target="end", condition="continue"),
                Edge(
                    id="e5", source="eval", target="plan", condition="loop"
                ),  # Loop back
            ],
        )
        order = constellation.topological_order()
        # Should still produce valid order, ignoring loop edge
        assert order[0] == "start"
        assert order[-1] == "end"
        assert order.index("plan") < order.index("exec")
        assert order.index("exec") < order.index("eval")

    def test_json_serialization(self, simple_constellation):
        """Test JSON round-trip."""
        json_str = simple_constellation.model_dump_json()
        restored = Constellation.model_validate_json(json_str)
        assert restored.id == simple_constellation.id
        assert len(restored.nodes) == len(simple_constellation.nodes)
        assert len(restored.edges) == len(simple_constellation.edges)

    def test_execution_constraints(self):
        """Test execution constraint validation."""
        # Valid constraints
        c = Constellation(
            id="c1",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            max_loop_iterations=5,
            max_retry_attempts=2,
            retry_delay_base=1.0,
        )
        assert c.max_loop_iterations == 5

        # Invalid constraints should raise
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Constellation(
                id="c1",
                name="Test",
                description="Test",
                start=StartNode(id="start", position=Position(x=0, y=0)),
                end=EndNode(id="end", position=Position(x=100, y=0)),
                max_loop_iterations=0,  # Must be >= 1
            )

        with pytest.raises(ValidationError):
            Constellation(
                id="c1",
                name="Test",
                description="Test",
                start=StartNode(id="start", position=Position(x=0, y=0)),
                end=EndNode(id="end", position=Position(x=100, y=0)),
                max_retry_attempts=10,  # Must be <= 5
            )


class TestConstellationParallelBranches:
    """Test Constellation with parallel branches."""

    def test_parallel_branches(self):
        """Test constellation with parallel worker branches."""
        constellation = Constellation(
            id="parallel_workflow",
            name="Parallel Analysis",
            description="Runs multiple analyses in parallel",
            start=StartNode(id="start", position=Position(x=0, y=200)),
            end=EndNode(id="end", position=Position(x=800, y=200)),
            nodes=[
                StarNode(
                    id="aapl", star_id="analyzer", position=Position(x=200, y=100)
                ),
                StarNode(
                    id="msft", star_id="analyzer", position=Position(x=200, y=200)
                ),
                StarNode(
                    id="goog", star_id="analyzer", position=Position(x=200, y=300)
                ),
                StarNode(
                    id="synth", star_id="synthesizer", position=Position(x=500, y=200)
                ),
            ],
            edges=[
                Edge(id="e1", source="start", target="aapl"),
                Edge(id="e2", source="start", target="msft"),
                Edge(id="e3", source="start", target="goog"),
                Edge(id="e4", source="aapl", target="synth"),
                Edge(id="e5", source="msft", target="synth"),
                Edge(id="e6", source="goog", target="synth"),
                Edge(id="e7", source="synth", target="end"),
            ],
        )

        # Entry nodes should be all three analyzers
        entry = constellation.get_entry_nodes()
        entry_ids = {n.id for n in entry}
        assert entry_ids == {"aapl", "msft", "goog"}

        # Synth should have three upstream nodes
        upstream = constellation.get_upstream_nodes("synth")
        upstream_ids = {n.id for n in upstream}
        assert upstream_ids == {"aapl", "msft", "goog"}

        # Topological order should have start first, end last
        order = constellation.topological_order()
        assert order[0] == "start"
        assert order[-1] == "end"
        # Synth should come after all analyzers
        assert order.index("synth") > order.index("aapl")
        assert order.index("synth") > order.index("msft")
        assert order.index("synth") > order.index("goog")
