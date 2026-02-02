"""Tests for Edge model."""

from astro_backend_service.models import Edge


class TestEdge:
    """Test Edge model."""

    def test_minimal_instantiation(self):
        """Test creating Edge with required fields."""
        edge = Edge(id="e1", source="start", target="node1")
        assert edge.id == "e1"
        assert edge.source == "start"
        assert edge.target == "node1"
        assert edge.condition is None

    def test_with_condition(self):
        """Test creating Edge with condition (for EvalStar routing)."""
        continue_edge = Edge(
            id="e_continue",
            source="eval_node",
            target="synthesis_node",
            condition="continue",
        )
        assert continue_edge.condition == "continue"

        loop_edge = Edge(
            id="e_loop",
            source="eval_node",
            target="planning_node",
            condition="loop",
        )
        assert loop_edge.condition == "loop"

    def test_json_serialization(self):
        """Test JSON round-trip."""
        edge = Edge(
            id="e1",
            source="start",
            target="node1",
            condition="continue",
        )
        json_str = edge.model_dump_json()
        restored = Edge.model_validate_json(json_str)
        assert restored == edge

    def test_json_serialization_without_condition(self):
        """Test JSON round-trip without condition."""
        edge = Edge(id="e1", source="a", target="b")
        json_str = edge.model_dump_json()
        restored = Edge.model_validate_json(json_str)
        assert restored.condition is None
