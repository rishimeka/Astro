"""Tests for probes.validator module."""

from datetime import datetime
from probes.validator import validate_star_probes
from probes.registry import ProbeRegistry
from star_foundry.star import Star
from inspect import signature


class TestProbeValidator:
    """Test suite for the probe validator module."""

    def setup_method(self):
        """Set up test fixtures."""
        self.probe_registry = ProbeRegistry()

    def test_validate_star_probes_all_valid(self):
        """Test validating a star with all valid probes."""

        # Register some probes
        def probe1():
            pass

        def probe2():
            pass

        sig = signature(probe1)
        self.probe_registry.register(
            id="probe1",
            fun=probe1,
            description="Probe 1",
            signature=sig,
            param_schema={},
        )

        sig2 = signature(probe2)
        self.probe_registry.register(
            id="probe2",
            fun=probe2,
            description="Probe 2",
            signature=sig2,
            param_schema={},
        )

        # Create a star with valid probes
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=["probe1", "probe2"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        missing = validate_star_probes(star, self.probe_registry)
        assert missing == []

    def test_validate_star_probes_some_missing(self):
        """Test validating a star with some missing probes."""

        def probe1():
            pass

        sig = signature(probe1)
        self.probe_registry.register(
            id="probe1",
            fun=probe1,
            description="Probe 1",
            signature=sig,
            param_schema={},
        )

        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=["probe1", "probe2", "probe3"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        missing = validate_star_probes(star, self.probe_registry)
        assert len(missing) == 2
        assert "probe2" in missing
        assert "probe3" in missing

    def test_validate_star_probes_all_missing(self):
        """Test validating a star with all missing probes."""
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=["nonexistent1", "nonexistent2"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        missing = validate_star_probes(star, self.probe_registry)
        assert len(missing) == 2
        assert "nonexistent1" in missing
        assert "nonexistent2" in missing

    def test_validate_star_probes_empty_list(self):
        """Test validating a star with no probes."""
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=[],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        missing = validate_star_probes(star, self.probe_registry)
        assert missing == []

    def test_validate_star_probes_with_empty_registry(self):
        """Test validating a star when probe registry is empty."""
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=["probe1"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        missing = validate_star_probes(star, self.probe_registry)
        assert missing == ["probe1"]

    def test_validate_star_probes_returns_list(self):
        """Test that validate_star_probes always returns a list."""
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            probes=["probe1"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        result = validate_star_probes(star, self.probe_registry)
        assert isinstance(result, list)

    def test_validate_multiple_stars(self):
        """Test validating multiple stars with different probe combinations."""

        def probe1():
            pass

        sig = signature(probe1)
        self.probe_registry.register(
            id="probe1",
            fun=probe1,
            description="Probe 1",
            signature=sig,
            param_schema={},
        )

        star1 = Star(
            id="star1",
            name="Star 1",
            description="Test",
            content="Content",
            probes=["probe1"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        star2 = Star(
            id="star2",
            name="Star 2",
            description="Test",
            content="Content",
            probes=["probe2"],
            created_on=datetime.now(),
            updated_on=datetime.now(),
        )

        missing1 = validate_star_probes(star1, self.probe_registry)
        missing2 = validate_star_probes(star2, self.probe_registry)

        assert missing1 == []
        assert missing2 == ["probe2"]
