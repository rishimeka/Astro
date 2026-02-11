"""Tests for the Probe model."""

import pytest

from astro_backend_service.probes.probe import Probe


class TestProbeModel:
    """Tests for the Probe Pydantic model."""

    def test_probe_creation_with_all_fields(self) -> None:
        """Test creating a Probe with all fields populated."""
        probe = Probe(
            name="test_probe",
            description="A test probe description",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            output_schema={"type": "string"},
            module_path="test.module",
            function_name="test_probe",
        )

        assert probe.name == "test_probe"
        assert probe.description == "A test probe description"
        assert probe.input_schema is not None
        assert probe.input_schema["properties"]["query"]["type"] == "string"
        assert probe.output_schema == {"type": "string"}
        assert probe.module_path == "test.module"
        assert probe.function_name == "test_probe"

    def test_probe_creation_minimal(self) -> None:
        """Test creating a Probe with only required fields."""
        probe = Probe(
            name="minimal_probe",
            description="Minimal description",
            module_path="test.module",
            function_name="minimal_probe",
        )

        assert probe.name == "minimal_probe"
        assert probe.input_schema is None
        assert probe.output_schema is None

    def test_probe_invoke_with_callable(self) -> None:
        """Test invoking a probe with a callable set."""

        def test_func(x: int) -> int:
            return x * 2

        probe = Probe(
            name="test_invoke",
            description="Test invoke",
            module_path="test.module",
            function_name="test_invoke",
        )
        probe._callable = test_func

        result = probe.invoke(x=5)
        assert result == 10

    def test_probe_invoke_without_callable_raises(self) -> None:
        """Test that invoking a probe without a callable raises RuntimeError."""
        probe = Probe(
            name="no_callable",
            description="No callable",
            module_path="test.module",
            function_name="no_callable",
        )

        with pytest.raises(RuntimeError, match="has no callable set"):
            probe.invoke()

    def test_probe_invoke_with_kwargs(self) -> None:
        """Test invoking a probe with multiple keyword arguments."""

        def multi_arg_func(a: str, b: int, c: bool = False) -> str:
            return f"{a}-{b}-{c}"

        probe = Probe(
            name="multi_arg",
            description="Multi arg test",
            module_path="test.module",
            function_name="multi_arg",
        )
        probe._callable = multi_arg_func

        result = probe.invoke(a="hello", b=42, c=True)
        assert result == "hello-42-True"
