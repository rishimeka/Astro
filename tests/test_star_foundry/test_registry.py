"""Tests for star_foundry.registry module."""

import logging
from datetime import datetime
from star_foundry.star import Star
from star_foundry.registry import StarRegistry
from star_foundry.validator import StarValidator
from probes.registry import ProbeRegistry
from inspect import signature


class TestStarRegistry:
    """Test suite for the StarRegistry class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.probe_registry = ProbeRegistry()
        self.registry = StarRegistry(self.probe_registry)

    def test_registry_initialization(self):
        """Test StarRegistry initialization."""
        assert self.registry._stars == {}
        assert self.registry.probe_registry == self.probe_registry
        assert self.registry.validator is None

    def test_registry_initialization_with_validator(self):
        """Test StarRegistry initialization with validator."""
        validator = StarValidator(
            StarRegistry(self.probe_registry), self.probe_registry
        )
        registry = StarRegistry(self.probe_registry, validator)
        assert registry.validator == validator

    def test_register_star(self):
        """Test registering a star."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star)
        assert "star1" in self.registry._stars
        assert self.registry._stars["star1"] == star

    def test_register_multiple_stars(self):
        """Test registering multiple stars."""
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
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star1)
        self.registry.register(star2)

        assert len(self.registry._stars) == 2
        assert "star1" in self.registry._stars
        assert "star2" in self.registry._stars

    def test_get_star_exists(self):
        """Test retrieving an existing star."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star)
        retrieved = self.registry.get("star1")

        assert retrieved is not None
        assert retrieved.id == "star1"
        assert retrieved == star

    def test_get_star_not_exists(self):
        """Test retrieving a non-existent star returns None."""
        result = self.registry.get("nonexistent")
        assert result is None

    def test_list_stars_empty(self):
        """Test listing stars when registry is empty."""
        stars = self.registry.list_stars()
        assert stars == []

    def test_list_stars(self):
        """Test listing all registered stars."""
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
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star1)
        self.registry.register(star2)

        stars = self.registry.list_stars()
        assert len(stars) == 2
        assert star1 in stars
        assert star2 in stars

    def test_resolve_references_without_validator(self):
        """Test resolving references without a validator."""
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

        self.registry.register(star1)
        self.registry.register(star2)
        self.registry.resolve_references(star2)

        assert len(star2.resolved_references) == 1
        assert star2.resolved_references[0] == star1

    def test_resolve_references_with_validator(self):
        """Test resolving references with a validator."""
        validator = StarValidator(self.registry, self.probe_registry)
        self.registry.validator = validator

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

        self.registry.register(star1)
        self.registry.register(star2)
        self.registry.resolve_references(star2)

        assert len(star2.resolved_references) == 1
        assert star2.resolved_references[0] == star1
        assert star2.missing_references == ["missing_star"]

    def test_resolve_probes_without_validator(self):
        """Test resolving probes without a validator."""

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

        self.registry.register(star)
        self.registry.resolve_probes(star)

        assert len(star.resolved_probes) == 1
        assert star.resolved_probes[0]["id"] == "probe1"

    def test_resolve_probes_with_validator(self):
        """Test resolving probes with a validator."""
        validator = StarValidator(self.registry, self.probe_registry)
        self.registry.validator = validator

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

        self.registry.register(star)
        self.registry.resolve_probes(star)

        assert len(star.resolved_probes) == 1
        assert star.missing_probes == ["missing_probe"]

    def test_finalize_without_validator(self, caplog):
        """Test finalize method without validator."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star)

        with caplog.at_level(logging.INFO):
            self.registry.finalize()

        assert "Finalizing StarRegistry" in caplog.text

    def test_finalize_with_validator_no_cycles(self, caplog):
        """Test finalize method with validator and no cycles."""
        validator = StarValidator(self.registry, self.probe_registry)
        self.registry.validator = validator

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

        self.registry.register(star1)
        self.registry.register(star2)

        with caplog.at_level(logging.INFO):
            self.registry.finalize()

        assert "finalized" in caplog.text.lower()

    def test_finalize_with_validator_with_cycles(self, caplog):
        """Test finalize method detects cycles in references."""
        validator = StarValidator(self.registry, self.probe_registry)
        self.registry.validator = validator

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

        self.registry.register(star1)
        self.registry.register(star2)

        with caplog.at_level(logging.WARNING):
            self.registry.finalize()

        assert "Cycle detected" in caplog.text

    def test_register_overwrites_existing_star(self):
        """Test that registering a star with same ID overwrites the previous one."""
        now = datetime.now()
        star1 = Star(
            id="star1",
            name="Original",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )
        star2 = Star(
            id="star1",
            name="Updated",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star1)
        self.registry.register(star2)

        retrieved = self.registry.get("star1")
        assert retrieved.name == "Updated"

    def test_resolve_references_empty_list(self):
        """Test resolving references when star has no references."""
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

        self.registry.register(star)
        result = self.registry.resolve_references(star)

        assert result is None
        assert star.resolved_references == []

    def test_resolve_probes_empty_list(self):
        """Test resolving probes when star has no probes."""
        now = datetime.now()
        star = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=[],
            created_on=now,
            updated_on=now,
        )

        self.registry.register(star)
        result = self.registry.resolve_probes(star)

        assert result is None
        assert star.resolved_probes == []
