"""Tests for validation logic."""

import pytest

from astro_backend_service.foundry import ValidationError
from astro_backend_service.foundry.validation import (
    validate_directive,
    validate_star,
    validate_constellation,
)
from astro_backend_service.foundry.indexes import FoundryIndexes, Probe
from astro_backend_service.models import (
    Directive,
    Constellation,
    Position,
    StartNode,
    EndNode,
    StarNode,
    Edge,
    WorkerStar,
    PlanningStar,
    ExecutionStar,
    EvalStar,
    SynthesisStar,
)


@pytest.fixture
def indexes():
    """Create empty indexes for testing."""
    return FoundryIndexes()


@pytest.fixture
def indexes_with_probes(indexes):
    """Create indexes with registered probes."""
    indexes.probes["web_search"] = Probe(
        name="web_search", description="Search the web"
    )
    indexes.probes["calculator"] = Probe(name="calculator", description="Do math")
    return indexes


class TestValidateDirective:
    """Test validate_directive function."""

    def test_valid_directive(self, indexes_with_probes):
        """Test valid directive passes validation."""
        directive = Directive(
            id="test",
            name="Test",
            description="A test directive",
            content="Content with @probe:web_search",
            probe_ids=["web_search"],
        )
        warnings = validate_directive(directive, indexes_with_probes)
        assert warnings == []

    def test_empty_description_raises(self, indexes):
        """Test empty description raises ValidationError."""
        directive = Directive(
            id="test",
            name="Test",
            description="",
            content="Some content",
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_directive(directive, indexes)
        assert "no description" in str(exc_info.value)

    def test_empty_content_raises(self, indexes):
        """Test empty content raises ValidationError."""
        directive = Directive(
            id="test",
            name="Test",
            description="Valid description",
            content="",
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_directive(directive, indexes)
        assert "no content" in str(exc_info.value)

    def test_missing_probe_warning(self, indexes):
        """Test missing probe reference returns warning."""
        directive = Directive(
            id="test",
            name="Test",
            description="Valid description",
            content="Uses @probe:unknown_probe",
            probe_ids=["unknown_probe"],
        )
        warnings = validate_directive(directive, indexes)
        assert len(warnings) == 1
        assert "unknown_probe" in warnings[0].message
        assert "isn't registered" in warnings[0].message

    def test_missing_directive_warning(self, indexes):
        """Test missing directive reference returns warning."""
        directive = Directive(
            id="test",
            name="Test",
            description="Valid description",
            content="Delegates to @directive:missing",
            reference_ids=["missing"],
        )
        warnings = validate_directive(directive, indexes)
        assert len(warnings) == 1
        assert "missing" in warnings[0].message
        assert "doesn't exist" in warnings[0].message

    def test_cycle_raises(self, indexes):
        """Test cycle in reference_ids raises ValidationError."""
        # Create directive A that will reference B
        directive_b = Directive(
            id="b",
            name="B",
            description="Directive B",
            content="Content",
            reference_ids=["a"],  # B references A
        )
        indexes.directives["b"] = directive_b

        # Now try to create A that references B (creates cycle)
        directive_a = Directive(
            id="a",
            name="A",
            description="Directive A",
            content="Content",
            reference_ids=["b"],  # A references B
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_directive(directive_a, indexes)
        assert "cycle" in str(exc_info.value).lower()


class TestValidateStar:
    """Test validate_star function."""

    def test_valid_star(self, indexes_with_probes):
        """Test valid star passes validation."""
        directive = Directive(
            id="d1",
            name="Directive",
            description="Test",
            content="Content",
        )
        indexes_with_probes.directives["d1"] = directive

        star = WorkerStar(
            id="s1",
            name="Worker",
            directive_id="d1",
            probe_ids=["web_search"],
        )
        warnings = validate_star(star, indexes_with_probes)
        assert warnings == []

    def test_missing_directive_raises(self, indexes):
        """Test missing directive raises ValidationError."""
        star = WorkerStar(
            id="s1",
            name="Worker",
            directive_id="missing",
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_star(star, indexes)
        assert "doesn't exist" in str(exc_info.value)

    def test_missing_probe_warning(self, indexes):
        """Test missing probe returns warning."""
        directive = Directive(
            id="d1",
            name="Directive",
            description="Test",
            content="Content",
        )
        indexes.directives["d1"] = directive

        star = WorkerStar(
            id="s1",
            name="Worker",
            directive_id="d1",
            probe_ids=["unknown_probe"],
        )
        warnings = validate_star(star, indexes)
        assert len(warnings) == 1
        assert "unknown_probe" in warnings[0].message


class TestValidateConstellation:
    """Test validate_constellation function."""

    @pytest.fixture
    def setup_stars(self, indexes):
        """Set up stars for constellation tests."""
        # Create directives
        for i in range(5):
            indexes.directives[f"d{i}"] = Directive(
                id=f"d{i}",
                name=f"Directive {i}",
                description="Test",
                content="Content",
            )

        # Create stars
        indexes.stars["planning"] = PlanningStar(
            id="planning", name="Planner", directive_id="d0"
        )
        indexes.stars["execution"] = ExecutionStar(
            id="execution", name="Executor", directive_id="d1"
        )
        indexes.stars["eval"] = EvalStar(id="eval", name="Evaluator", directive_id="d2")
        indexes.stars["synthesis"] = SynthesisStar(
            id="synthesis", name="Synthesizer", directive_id="d3"
        )
        indexes.stars["worker"] = WorkerStar(
            id="worker", name="Worker", directive_id="d4"
        )
        return indexes

    def test_valid_constellation(self, setup_stars):
        """Test valid constellation passes validation."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test constellation",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=500, y=0)),
            nodes=[
                StarNode(id="n1", star_id="planning", position=Position(x=100, y=0)),
                StarNode(id="n2", star_id="execution", position=Position(x=200, y=0)),
                StarNode(id="n3", star_id="synthesis", position=Position(x=300, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="n2"),
                Edge(id="e3", source="n2", target="n3"),
                Edge(id="e4", source="n3", target="end"),
            ],
        )
        # Should not raise - synthesis has upstream
        validate_constellation(constellation, setup_stars)
        # May have warning about ExecutionStar without SynthesisStar downstream
        # but that's okay for this test

    def test_missing_star_raises(self, indexes):
        """Test missing star raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="missing", position=Position(x=50, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, indexes)
        assert "doesn't exist" in str(exc_info.value)

    def test_orphan_node_raises(self, setup_stars):
        """Test orphan node raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="worker", position=Position(x=50, y=0)),
                StarNode(id="orphan", star_id="worker", position=Position(x=50, y=100)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
                # orphan has no edges
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "no connections" in str(exc_info.value)

    def test_incoming_to_start_raises(self, setup_stars):
        """Test incoming edge to start raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="worker", position=Position(x=50, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="start"),  # Back to start!
                Edge(id="e3", source="n1", target="end"),
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "Start node cannot have incoming edges" in str(exc_info.value)

    def test_outgoing_from_end_raises(self, setup_stars):
        """Test outgoing edge from end raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="worker", position=Position(x=50, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
                Edge(id="e3", source="end", target="n1"),  # From end!
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "End node cannot have outgoing edges" in str(exc_info.value)

    def test_synthesis_as_entry_raises(self, setup_stars):
        """Test SynthesisStar as entry point raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="synthesis", position=Position(x=50, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "cannot be entry point" in str(exc_info.value)

    def test_eval_star_edge_without_condition_raises(self, setup_stars):
        """Test EvalStar edge without condition raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="planning", position=Position(x=100, y=0)),
                StarNode(id="n2", star_id="execution", position=Position(x=200, y=0)),
                StarNode(id="n3", star_id="eval", position=Position(x=300, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="n2"),
                Edge(id="e3", source="n2", target="n3"),
                Edge(id="e4", source="n3", target="end"),  # No condition!
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "must have condition" in str(exc_info.value)

    def test_non_eval_edge_with_condition_raises(self, setup_stars):
        """Test non-EvalStar edge with condition raises ValidationError."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="worker", position=Position(x=50, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end", condition="continue"),
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "Only EvalStar edges can have conditions" in str(exc_info.value)

    def test_eval_loop_to_planning_allowed(self, setup_stars):
        """Test EvalStar loop to PlanningStar is allowed."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="planning", position=Position(x=100, y=0)),
                StarNode(id="n2", star_id="execution", position=Position(x=200, y=0)),
                StarNode(id="n3", star_id="eval", position=Position(x=300, y=0)),
                StarNode(id="n4", star_id="synthesis", position=Position(x=400, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="n2"),
                Edge(id="e3", source="n2", target="n3"),
                Edge(id="e4", source="n3", target="n4", condition="continue"),
                Edge(id="e5", source="n3", target="n1", condition="loop"),  # Loop back!
                Edge(id="e6", source="n4", target="end"),
            ],
        )
        # Should not raise
        validate_constellation(constellation, setup_stars)
        # May have warnings but no errors

    def test_planning_without_execution_raises(self, setup_stars):
        """Test PlanningStar without ExecutionStar downstream raises."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="planning", position=Position(x=50, y=0)),
                StarNode(id="n2", star_id="synthesis", position=Position(x=100, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="n2"),
                Edge(id="e3", source="n2", target="end"),
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "must connect to an ExecutionStar" in str(exc_info.value)

    def test_execution_without_planning_raises(self, setup_stars):
        """Test ExecutionStar without PlanningStar upstream raises."""
        constellation = Constellation(
            id="test",
            name="Test",
            description="Test",
            start=StartNode(id="start", position=Position(x=0, y=0)),
            end=EndNode(id="end", position=Position(x=100, y=0)),
            nodes=[
                StarNode(id="n1", star_id="execution", position=Position(x=50, y=0)),
            ],
            edges=[
                Edge(id="e1", source="start", target="n1"),
                Edge(id="e2", source="n1", target="end"),
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_constellation(constellation, setup_stars)
        assert "requires a PlanningStar upstream" in str(exc_info.value)
