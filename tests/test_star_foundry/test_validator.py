"""Tests for star_foundry.validator module."""

import logging
from datetime import datetime
from star_foundry.star import Star
from star_foundry.validator import StarValidator
from star_foundry.registry import StarRegistry
from probes.registry import ProbeRegistry
from inspect import signature


class TestStarValidator:
    """Test suite for the StarValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.probe_registry = ProbeRegistry()
        self.star_registry = StarRegistry(self.probe_registry)
        self.validator = StarValidator(self.star_registry, self.probe_registry)

    def test_validator_initialization(self):
        """Test StarValidator initialization."""
        assert self.validator.star_registry == self.star_registry
        assert self.validator.probe_registry == self.probe_registry

    def test_validate_references_all_valid(self, caplog):
        """Test validating references when all exist."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star1)
        self.star_registry.register(star2)

        with caplog.at_level(logging.WARNING):
            valid_refs = self.validator.validate_references(star2)

        assert valid_refs == ["star1"]
        assert star2.missing_references == []

    def test_validate_references_some_missing(self, caplog):
        """Test validating references with some missing."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star1", "missing_star"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star1)
        self.star_registry.register(star2)

        with caplog.at_level(logging.WARNING):
            valid_refs = self.validator.validate_references(star2)

        assert valid_refs == ["star1"]
        assert star2.missing_references == ["missing_star"]
        assert "missing references" in caplog.text

    def test_validate_references_all_missing(self, caplog):
        """Test validating references when all are missing."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            references=["missing1", "missing2"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)

        with caplog.at_level(logging.WARNING):
            valid_refs = self.validator.validate_references(star)

        assert valid_refs == []
        assert len(star.missing_references) == 2
        assert "missing1" in star.missing_references
        assert "missing2" in star.missing_references

    def test_validate_references_empty(self, caplog):
        """Test validating references when star has no references."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            references=[],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)

        with caplog.at_level(logging.WARNING):
            valid_refs = self.validator.validate_references(star)

        assert valid_refs == []
        assert star.missing_references == []

    def test_validate_probes_all_valid(self, caplog):
        """Test validating probes when all exist."""

        def test_probe():
            pass

        sig = signature(test_probe)
        self.probe_registry.register(
            id="probe1",
            fun=test_probe,
            description="Test probe",
            signature=sig,
            param_schema={},
        )

        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=["probe1"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)

        with caplog.at_level(logging.WARNING):
            valid_probes = self.validator.validate_probes(star)

        assert valid_probes == ["probe1"]
        assert star.missing_probes == []

    def test_validate_probes_some_missing(self, caplog):
        """Test validating probes with some missing."""

        def test_probe():
            pass

        sig = signature(test_probe)
        self.probe_registry.register(
            id="probe1",
            fun=test_probe,
            description="Test probe",
            signature=sig,
            param_schema={},
        )

        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=["probe1", "missing_probe"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)

        with caplog.at_level(logging.WARNING):
            valid_probes = self.validator.validate_probes(star)

        assert valid_probes == ["probe1"]
        assert star.missing_probes == ["missing_probe"]
        assert "missing probes" in caplog.text

    def test_validate_probes_all_missing(self, caplog):
        """Test validating probes when all are missing."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=["missing1", "missing2"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)

        with caplog.at_level(logging.WARNING):
            valid_probes = self.validator.validate_probes(star)

        assert valid_probes == []
        assert len(star.missing_probes) == 2

    def test_detect_cycles_no_cycles(self):
        """Test detecting cycles when there are none."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star1)
        self.star_registry.register(star2)

        cycles = self.validator.detect_cycles()
        assert cycles == []

    def test_detect_cycles_simple_cycle(self):
        """Test detecting a simple two-node cycle."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            references=["star2"],
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star1)
        self.star_registry.register(star2)

        cycles = self.validator.detect_cycles()
        assert len(cycles) > 0
        # Check that a cycle was detected
        assert any("star1" in cycle or "star2" in cycle for cycle in cycles)

    def test_detect_cycles_self_reference(self):
        """Test detecting a self-referencing cycle."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)

        cycles = self.validator.detect_cycles()
        assert len(cycles) > 0

    def test_detect_cycles_three_node_cycle(self):
        """Test detecting a three-node cycle."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            references=["star2"],
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star3"],
            created_on=now,
            updated_on=now,
        )
        star3 = Star(
            id="star3",
            name="Star 3",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star1)
        self.star_registry.register(star2)
        self.star_registry.register(star3)

        cycles = self.validator.detect_cycles()
        assert len(cycles) > 0

    def test_detect_cycles_complex_graph_no_cycles(self):
        """Test detecting cycles in a complex graph without cycles."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )
        star3 = Star(
            id="star3",
            name="Star 3",
            description="Test",
            content="Content",
            references=["star1"],
            created_on=now,
            updated_on=now,
        )
        star4 = Star(
            id="star4",
            name="Star 4",
            description="Test",
            content="Content",
            references=["star2", "star3"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star1)
        self.star_registry.register(star2)
        self.star_registry.register(star3)
        self.star_registry.register(star4)

        cycles = self.validator.detect_cycles()
        assert cycles == []

    def test_detect_cycles_empty_registry(self):
        """Test detecting cycles in an empty registry."""
        cycles = self.validator.detect_cycles()
        assert cycles == []

    def test_validate_references_updates_star_state(self):
        """Test that validate_references updates the star's missing_references."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            references=["missing"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)
        self.validator.validate_references(star)

        assert star.missing_references == ["missing"]

    def test_validate_probes_updates_star_state(self):
        """Test that validate_probes updates the star's missing_probes."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=["missing"],
            created_on=now,
            updated_on=now,
        )

        self.star_registry.register(star)
        self.validator.validate_probes(star)

        assert star.missing_probes == ["missing"]
