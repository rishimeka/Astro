"""Tests for the ProbeRegistry."""

from typing import Generator

import pytest

from astro_backend_service.probes.exceptions import DuplicateProbeError
from astro_backend_service.probes.probe import Probe
from astro_backend_service.probes.registry import ProbeRegistry


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Clear the registry before and after each test."""
    ProbeRegistry.clear()
    yield
    ProbeRegistry.clear()


class TestProbeRegistry:
    """Tests for the ProbeRegistry class."""

    def test_register_adds_probe(self) -> None:
        """Test that register() adds a probe to the registry."""
        probe = Probe(
            name="test_probe",
            description="A test probe",
            module_path="test.module",
            function_name="test_probe",
        )

        ProbeRegistry.register(probe)

        assert ProbeRegistry.count() == 1
        assert ProbeRegistry.get("test_probe") is probe

    def test_get_returns_registered_probe(self) -> None:
        """Test that get() returns the registered probe."""
        probe = Probe(
            name="my_probe",
            description="My probe",
            module_path="test.module",
            function_name="my_probe",
        )
        ProbeRegistry.register(probe)

        result = ProbeRegistry.get("my_probe")

        assert result is probe
        assert result.name == "my_probe"

    def test_get_returns_none_for_unknown(self) -> None:
        """Test that get() returns None for unknown probe names."""
        result = ProbeRegistry.get("nonexistent")

        assert result is None

    def test_all_returns_all_probes(self) -> None:
        """Test that all() returns all registered probes."""
        probe1 = Probe(
            name="probe1",
            description="First probe",
            module_path="test.module",
            function_name="probe1",
        )
        probe2 = Probe(
            name="probe2",
            description="Second probe",
            module_path="test.module",
            function_name="probe2",
        )

        ProbeRegistry.register(probe1)
        ProbeRegistry.register(probe2)

        all_probes = ProbeRegistry.all()

        assert len(all_probes) == 2
        assert probe1 in all_probes
        assert probe2 in all_probes

    def test_count_returns_correct_count(self) -> None:
        """Test that count() returns the correct number of probes."""
        assert ProbeRegistry.count() == 0

        for i in range(5):
            probe = Probe(
                name=f"probe_{i}",
                description=f"Probe {i}",
                module_path="test.module",
                function_name=f"probe_{i}",
            )
            ProbeRegistry.register(probe)

        assert ProbeRegistry.count() == 5

    def test_clear_empties_registry(self) -> None:
        """Test that clear() empties the registry."""
        probe = Probe(
            name="probe",
            description="A probe",
            module_path="test.module",
            function_name="probe",
        )
        ProbeRegistry.register(probe)
        assert ProbeRegistry.count() == 1

        ProbeRegistry.clear()

        assert ProbeRegistry.count() == 0
        assert ProbeRegistry.get("probe") is None

    def test_duplicate_raises_error(self) -> None:
        """Test that registering a duplicate name raises DuplicateProbeError."""
        probe1 = Probe(
            name="duplicate",
            description="First probe",
            module_path="module1",
            function_name="duplicate",
        )
        probe2 = Probe(
            name="duplicate",
            description="Second probe",
            module_path="module2",
            function_name="duplicate",
        )

        ProbeRegistry.register(probe1)

        with pytest.raises(DuplicateProbeError) as exc_info:
            ProbeRegistry.register(probe2)

        error_msg = str(exc_info.value)
        assert "duplicate" in error_msg
        assert "module1" in error_msg
        assert "module2" in error_msg

    def test_duplicate_error_message_shows_locations(self) -> None:
        """Test that the DuplicateProbeError message shows both locations."""
        probe1 = Probe(
            name="test_name",
            description="First",
            module_path="path.to.first",
            function_name="func1",
        )
        probe2 = Probe(
            name="test_name",
            description="Second",
            module_path="path.to.second",
            function_name="func2",
        )

        ProbeRegistry.register(probe1)

        with pytest.raises(DuplicateProbeError) as exc_info:
            ProbeRegistry.register(probe2)

        error_msg = str(exc_info.value)
        assert "Existing: path.to.first:func1" in error_msg
        assert "Duplicate: path.to.second:func2" in error_msg
        assert "Each probe must have a unique name" in error_msg
