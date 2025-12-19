"""Tests for probes.decorator module."""

import pytest
from probes.decorator import probe
from probes.registry import probe_registry


class TestProbeDecorator:
    """Test suite for the probe decorator."""

    def setup_method(self):
        """Reset the probe registry before each test."""
        probe_registry._probes = {}

    def test_probe_decorator_with_description(self):
        """Test that probe decorator registers function with provided description."""

        @probe(id="test_probe", description="Test probe description")
        def test_function(x: int) -> int:
            return x * 2

        # Verify the probe is registered
        registered = probe_registry.get_probe("test_probe")
        assert registered is not None
        assert registered["id"] == "test_probe"
        assert registered["description"] == "Test probe description"
        assert registered["function"] == test_function

        # Verify the function still works
        assert test_function(5) == 10

    def test_probe_decorator_with_docstring(self):
        """Test that probe decorator uses function docstring when description is empty."""

        @probe(id="test_probe_docstring", description="")
        def test_function(x: int) -> int:
            """This is a docstring description."""
            return x * 2

        registered = probe_registry.get_probe("test_probe_docstring")
        assert registered is not None
        assert registered["description"] == "This is a docstring description."

    def test_probe_decorator_no_description_no_docstring_raises_error(self):
        """Test that probe decorator raises ValueError when neither description nor docstring exists."""
        with pytest.raises(ValueError, match="must have a description"):

            @probe(id="test_probe_no_desc", description="")
            def test_function(x: int) -> int:
                return x * 2

    def test_probe_decorator_with_multiple_parameters(self):
        """Test probe decorator with function that has multiple parameters."""

        @probe(id="multi_param_probe", description="Multi parameter probe")
        def test_function(x: int, y: str, z: float = 1.0) -> str:
            return f"{x}-{y}-{z}"

        registered = probe_registry.get_probe("multi_param_probe")
        assert registered is not None
        assert "param_schema" in registered

        # Verify function still works
        result = test_function(1, "test", 2.5)
        assert result == "1-test-2.5"

    def test_probe_decorator_with_no_parameters(self):
        """Test probe decorator with function that has no parameters."""

        @probe(id="no_param_probe", description="No parameter probe")
        def test_function() -> str:
            return "success"

        registered = probe_registry.get_probe("no_param_probe")
        assert registered is not None
        assert test_function() == "success"

    def test_probe_decorator_preserves_function_metadata(self):
        """Test that probe decorator preserves function name and metadata."""

        @probe(id="metadata_probe", description="Metadata test")
        def test_function(x: int) -> int:
            """Original docstring."""
            return x

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Original docstring."

    def test_probe_decorator_builds_metadata(self):
        """Test that probe decorator builds comprehensive metadata."""

        @probe(id="metadata_test", description="Metadata building test")
        def test_function(x: int, y: str = "default") -> dict:
            return {"x": x, "y": y}

        registered = probe_registry.get_probe("metadata_test")
        assert registered is not None
        assert "signature" in registered
        assert "param_schema" in registered
        assert "return_schema" in registered

    def test_probe_decorator_with_complex_types(self):
        """Test probe decorator with complex type hints."""
        from typing import List, Dict

        @probe(id="complex_type_probe", description="Complex types")
        def test_function(items: List[int], mapping: Dict[str, int]) -> List[str]:
            return [str(i) for i in items]

        registered = probe_registry.get_probe("complex_type_probe")
        assert registered is not None

        result = test_function([1, 2, 3], {"a": 1})
        assert result == ["1", "2", "3"]

    def test_multiple_probes_registration(self):
        """Test that multiple probes can be registered independently."""

        @probe(id="probe_1", description="First probe")
        def func1(x: int) -> int:
            return x

        @probe(id="probe_2", description="Second probe")
        def func2(y: str) -> str:
            return y

        assert probe_registry.get_probe("probe_1") is not None
        assert probe_registry.get_probe("probe_2") is not None
        assert func1(1) == 1
        assert func2("test") == "test"

    def test_probe_decorator_with_async_function(self):
        """Test probe decorator with async function."""

        @probe(id="async_probe", description="Async probe")
        async def async_function(x: int) -> int:
            return x * 2

        registered = probe_registry.get_probe("async_probe")
        assert registered is not None
        assert registered["function"] == async_function
