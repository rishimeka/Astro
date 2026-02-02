"""Tests for base Star classes."""

from astro_backend_service.models import (
    Directive,
    StarType,
    WorkerStar,
)


class TestStarType:
    """Test StarType enum."""

    def test_all_values_exist(self):
        """Test all StarType values are present."""
        assert StarType.PLANNING == "planning"
        assert StarType.EXECUTION == "execution"
        assert StarType.DOCEX == "docex"
        assert StarType.EVAL == "eval"
        assert StarType.WORKER == "worker"
        assert StarType.SYNTHESIS == "synthesis"

    def test_string_comparison(self):
        """Test StarType works as string enum."""
        assert StarType.WORKER == "worker"
        assert StarType.WORKER.value == "worker"


class TestAtomicStar:
    """Test AtomicStar base class."""

    def test_resolve_probes_no_overlap(self):
        """Test probe resolution with no overlap."""
        # Create a concrete implementation (WorkerStar)
        star = WorkerStar(
            id="test",
            name="Test Worker",
            directive_id="d1",
            probe_ids=["star_probe"],
        )
        directive = Directive(
            id="d1",
            name="D1",
            description="Directive",
            content="Content",
            probe_ids=["directive_probe"],
        )
        probes = star.resolve_probes(directive)
        assert set(probes) == {"star_probe", "directive_probe"}

    def test_resolve_probes_with_overlap(self):
        """Test probe resolution with overlap (deduplication)."""
        star = WorkerStar(
            id="test",
            name="Test Worker",
            directive_id="d1",
            probe_ids=["shared_probe", "star_only"],
        )
        directive = Directive(
            id="d1",
            name="D1",
            description="Directive",
            content="Content",
            probe_ids=["shared_probe", "directive_only"],
        )
        probes = star.resolve_probes(directive)
        assert set(probes) == {"shared_probe", "star_only", "directive_only"}
        assert len(probes) == 3  # Deduplicated

    def test_resolve_probes_empty(self):
        """Test probe resolution with empty probe lists."""
        star = WorkerStar(
            id="test",
            name="Test Worker",
            directive_id="d1",
        )
        directive = Directive(
            id="d1",
            name="D1",
            description="Directive",
            content="Content",
        )
        probes = star.resolve_probes(directive)
        assert probes == []


class TestBaseStarValidation:
    """Test BaseStar validation."""

    def test_validate_star_returns_empty_list(self):
        """Test base validate_star returns empty list."""
        star = WorkerStar(
            id="test",
            name="Test",
            directive_id="d1",
        )
        errors = star.validate_star()
        assert errors == []
