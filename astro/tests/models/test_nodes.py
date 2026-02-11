"""Tests for Node models."""

from astro_backend_service.models import (
    EndNode,
    NodeType,
    Position,
    StarNode,
    StartNode,
)


class TestNodeType:
    """Test NodeType enum."""

    def test_all_values_exist(self):
        """Test all NodeType values are present."""
        assert NodeType.START == "start"
        assert NodeType.END == "end"
        assert NodeType.STAR == "star"


class TestPosition:
    """Test Position model."""

    def test_instantiation(self):
        """Test creating Position."""
        pos = Position(x=100.5, y=200.0)
        assert pos.x == 100.5
        assert pos.y == 200.0

    def test_json_serialization(self):
        """Test JSON round-trip."""
        pos = Position(x=50, y=100)
        json_str = pos.model_dump_json()
        restored = Position.model_validate_json(json_str)
        assert restored == pos


class TestStartNode:
    """Test StartNode model."""

    def test_minimal_instantiation(self):
        """Test creating StartNode with required fields."""
        node = StartNode(id="start", position=Position(x=0, y=0))
        assert node.id == "start"
        assert node.type == NodeType.START
        assert node.position.x == 0
        assert node.original_query is None
        assert node.constellation_purpose is None

    def test_with_runtime_fields(self):
        """Test StartNode with runtime fields filled."""
        node = StartNode(
            id="start",
            position=Position(x=0, y=200),
            original_query="Analyze AAPL",
            constellation_purpose="Financial analysis workflow",
        )
        assert node.original_query == "Analyze AAPL"
        assert node.constellation_purpose == "Financial analysis workflow"

    def test_json_serialization(self):
        """Test JSON round-trip."""
        node = StartNode(id="start", position=Position(x=0, y=0))
        json_str = node.model_dump_json()
        restored = StartNode.model_validate_json(json_str)
        assert restored.id == node.id
        assert restored.type == NodeType.START


class TestEndNode:
    """Test EndNode model."""

    def test_instantiation(self):
        """Test creating EndNode."""
        node = EndNode(id="end", position=Position(x=1000, y=200))
        assert node.id == "end"
        assert node.type == NodeType.END
        assert node.position.x == 1000

    def test_json_serialization(self):
        """Test JSON round-trip."""
        node = EndNode(id="end", position=Position(x=100, y=0))
        json_str = node.model_dump_json()
        restored = EndNode.model_validate_json(json_str)
        assert restored.id == node.id
        assert restored.type == NodeType.END


class TestStarNode:
    """Test StarNode model."""

    def test_minimal_instantiation(self):
        """Test creating StarNode with required fields."""
        node = StarNode(
            id="node1",
            star_id="worker_star_1",
            position=Position(x=200, y=100),
        )
        assert node.id == "node1"
        assert node.type == NodeType.STAR
        assert node.star_id == "worker_star_1"
        assert node.display_name is None
        assert node.variable_bindings == {}
        assert node.requires_confirmation is False
        assert node.confirmation_prompt is None

    def test_full_instantiation(self):
        """Test creating StarNode with all fields."""
        node = StarNode(
            id="analysis_node",
            star_id="company_analyzer",
            position=Position(x=300, y=150),
            display_name="AAPL Analysis",
            variable_bindings={"company_name": "Apple Inc.", "ticker": "AAPL"},
            requires_confirmation=True,
            confirmation_prompt="Review the analysis. Proceed with synthesis?",
        )
        assert node.display_name == "AAPL Analysis"
        assert node.variable_bindings["ticker"] == "AAPL"
        assert node.requires_confirmation is True
        assert "Proceed with synthesis" in node.confirmation_prompt

    def test_json_serialization(self):
        """Test JSON round-trip."""
        node = StarNode(
            id="n1",
            star_id="s1",
            position=Position(x=50, y=50),
            variable_bindings={"key": "value"},
        )
        json_str = node.model_dump_json()
        restored = StarNode.model_validate_json(json_str)
        assert restored.id == node.id
        assert restored.star_id == node.star_id
        assert restored.variable_bindings == node.variable_bindings
