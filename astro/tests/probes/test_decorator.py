"""Tests for the @probe decorator."""

from collections.abc import Generator

import pytest
from astro_backend_service.probes.decorator import _python_type_to_json_type, probe
from astro_backend_service.probes.exceptions import DuplicateProbeError
from astro_backend_service.probes.registry import ProbeRegistry


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Clear the registry before and after each test."""
    ProbeRegistry.clear()
    yield
    ProbeRegistry.clear()


class TestPythonTypeToJsonType:
    """Tests for the type conversion utility."""

    def test_str_to_string(self) -> None:
        """Test str maps to string."""
        assert _python_type_to_json_type(str) == "string"

    def test_int_to_integer(self) -> None:
        """Test int maps to integer."""
        assert _python_type_to_json_type(int) == "integer"

    def test_float_to_number(self) -> None:
        """Test float maps to number."""
        assert _python_type_to_json_type(float) == "number"

    def test_bool_to_boolean(self) -> None:
        """Test bool maps to boolean."""
        assert _python_type_to_json_type(bool) == "boolean"

    def test_list_to_array(self) -> None:
        """Test list maps to array."""
        assert _python_type_to_json_type(list) == "array"

    def test_dict_to_object(self) -> None:
        """Test dict maps to object."""
        assert _python_type_to_json_type(dict) == "object"

    def test_unknown_type_falls_back_to_string(self) -> None:
        """Test unknown types fall back to string."""

        class CustomType:
            pass

        assert _python_type_to_json_type(CustomType) == "string"


class TestProbeDecorator:
    """Tests for the @probe decorator."""

    def test_basic_decoration_works(self) -> None:
        """Test that basic decoration works."""

        @probe
        def my_probe(x: str) -> str:
            """A simple probe."""
            return x

        # LangGraph tools have an invoke method
        assert hasattr(my_probe, "invoke")

    def test_function_name_extraction(self) -> None:
        """Test that function name is extracted correctly."""

        @probe
        def named_probe(x: str) -> str:
            """A named probe."""
            return x

        registered = ProbeRegistry.get("named_probe")
        assert registered is not None
        assert registered.name == "named_probe"

    def test_docstring_extraction(self) -> None:
        """Test that docstring is extracted correctly."""

        @probe
        def documented_probe() -> str:
            """This is the probe description."""
            return "result"

        registered = ProbeRegistry.get("documented_probe")
        assert registered is not None
        assert registered.description == "This is the probe description."

    def test_missing_docstring_raises_value_error(self) -> None:
        """Test that missing docstring raises ValueError."""
        with pytest.raises(ValueError, match="must have a docstring"):

            @probe
            def no_doc_probe() -> str:
                return "result"

    def test_input_schema_from_type_hints(self) -> None:
        """Test that input schema is built from type hints."""

        @probe
        def typed_probe(query: str, count: int) -> str:
            """A probe with typed inputs."""
            return f"{query}: {count}"

        registered = ProbeRegistry.get("typed_probe")
        assert registered is not None
        assert registered.input_schema is not None
        assert registered.input_schema["type"] == "object"
        assert registered.input_schema["properties"]["query"]["type"] == "string"
        assert registered.input_schema["properties"]["count"]["type"] == "integer"

    def test_output_schema_from_return_type(self) -> None:
        """Test that output schema is built from return type."""

        @probe
        def returns_dict(x: str) -> dict:
            """Returns a dict."""
            return {"x": x}

        registered = ProbeRegistry.get("returns_dict")
        assert registered is not None
        assert registered.output_schema == {"type": "object"}

    def test_optional_parameters_not_required(self) -> None:
        """Test that optional parameters are not marked as required."""

        @probe
        def optional_probe(required: str, optional: int = 10) -> str:
            """A probe with optional param."""
            return f"{required}: {optional}"

        registered = ProbeRegistry.get("optional_probe")
        assert registered is not None
        assert registered.input_schema is not None
        assert "required" in registered.input_schema["required"]
        assert "optional" not in registered.input_schema["required"]

    def test_registration_happens_on_decoration(self) -> None:
        """Test that registration happens when the function is decorated."""
        assert ProbeRegistry.get("registration_test") is None

        @probe
        def registration_test() -> str:
            """Test registration."""
            return "done"

        assert ProbeRegistry.get("registration_test") is not None

    def test_duplicate_raises_duplicate_probe_error(self) -> None:
        """Test that duplicate probe names raise DuplicateProbeError."""

        @probe
        def duplicate_name() -> str:
            """First probe."""
            return "first"

        with pytest.raises(DuplicateProbeError):

            @probe
            def duplicate_name() -> str:  # noqa: F811
                """Second probe."""
                return "second"


class TestProbeDecoratorIntegration:
    """Integration tests for the @probe decorator."""

    def test_decorated_function_is_callable(self) -> None:
        """Test that decorated function remains callable."""

        @probe
        def callable_probe(x: int) -> int:
            """Double the input."""
            return x * 2

        # LangGraph tools use .invoke(input_dict) syntax
        result = callable_probe.invoke({"x": 5})
        assert result == 10

    def test_decorated_function_returns_correct_value(self) -> None:
        """Test that decorated function returns correct value."""

        @probe
        def greeting_probe(name: str) -> str:
            """Greet by name."""
            return f"Hello, {name}!"

        # LangGraph tools use .invoke(input_dict) syntax
        result = greeting_probe.invoke({"name": "World"})
        assert result == "Hello, World!"

    def test_probe_invoke_works(self) -> None:
        """Test that Probe.invoke() works correctly."""

        @probe
        def invoke_test(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        registered = ProbeRegistry.get("invoke_test")
        assert registered is not None
        result = registered.invoke(a=3, b=4)
        assert result == 7

    def test_langgraph_tool_integration(self) -> None:
        """Test that LangGraph tool integration works."""
        from langchain_core.tools import BaseTool

        @probe
        def langgraph_probe(query: str) -> str:
            """Search for something."""
            return f"Result: {query}"

        # The decorated function should be a LangGraph tool
        assert isinstance(langgraph_probe, BaseTool)

    def test_probe_metadata_accessible(self) -> None:
        """Test that probe metadata is accessible via ._probe."""

        @probe
        def metadata_probe(x: str) -> str:
            """A probe with metadata."""
            return x

        assert hasattr(metadata_probe, "_probe")
        assert metadata_probe._probe.name == "metadata_probe"
        assert metadata_probe._probe.description == "A probe with metadata."
