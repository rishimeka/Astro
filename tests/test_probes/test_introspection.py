"""Tests for probes.introspection module."""

from typing import List, Dict, Optional, Union
from enum import Enum
from pydantic import BaseModel
from probes.introspection import (
    extract_signature,
    extract_type_hints,
    python_type_to_json_schema,
    signature_to_json_schema,
    extract_return_schema,
    build_probe_metadata,
    schema_for_planner,
    build_langgraph_tool_schema,
)


class TestEnum(Enum):
    """Test enum for schema conversion."""

    OPTION_A = "a"
    OPTION_B = "b"


class TestModel(BaseModel):
    """Test Pydantic model for schema conversion."""

    name: str
    age: int


class TestIntrospectionFunctions:
    """Test suite for introspection utility functions."""

    def test_extract_signature(self):
        """Test extracting function signature."""

        def sample_func(x: int, y: str = "default") -> str:
            return f"{x}-{y}"

        sig = extract_signature(sample_func)
        assert sig is not None
        assert len(sig.parameters) == 2
        assert "x" in sig.parameters
        assert "y" in sig.parameters

    def test_extract_type_hints(self):
        """Test extracting type hints from function."""

        def sample_func(x: int, y: str) -> bool:
            return True

        hints = extract_type_hints(sample_func)
        assert hints["x"] is int
        assert hints["y"] is str
        assert hints["return"] is bool

    def test_python_type_to_json_schema_int(self):
        """Test converting int type to JSON schema."""
        schema = python_type_to_json_schema(int)
        assert schema == {"type": "integer"}

    def test_python_type_to_json_schema_float(self):
        """Test converting float type to JSON schema."""
        schema = python_type_to_json_schema(float)
        assert schema == {"type": "number"}

    def test_python_type_to_json_schema_str(self):
        """Test converting str type to JSON schema."""
        schema = python_type_to_json_schema(str)
        assert schema == {"type": "string"}

    def test_python_type_to_json_schema_bool(self):
        """Test converting bool type to JSON schema."""
        schema = python_type_to_json_schema(bool)
        assert schema == {"type": "boolean"}

    def test_python_type_to_json_schema_dict(self):
        """Test converting dict type to JSON schema."""
        schema = python_type_to_json_schema(dict)
        assert schema == {"type": "object"}

    def test_python_type_to_json_schema_list(self):
        """Test converting list type to JSON schema."""
        schema = python_type_to_json_schema(list)
        assert schema == {"type": "array"}

    def test_python_type_to_json_schema_typed_list(self):
        """Test converting typed List to JSON schema."""
        schema = python_type_to_json_schema(List[int])
        assert schema == {"type": "array", "items": {"type": "integer"}}

    def test_python_type_to_json_schema_typed_dict(self):
        """Test converting typed Dict to JSON schema."""
        schema = python_type_to_json_schema(Dict[str, int])
        assert schema == {"type": "object", "additionalProperties": {"type": "integer"}}

    def test_python_type_to_json_schema_optional(self):
        """Test converting Optional type to JSON schema."""
        schema = python_type_to_json_schema(Optional[int])
        assert schema == {"type": "integer"}

    def test_python_type_to_json_schema_union(self):
        """Test converting Union type to JSON schema."""
        schema = python_type_to_json_schema(Union[int, str])
        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 2

    def test_python_type_to_json_schema_enum(self):
        """Test converting Enum type to JSON schema."""
        schema = python_type_to_json_schema(TestEnum)
        assert schema["type"] == "string"
        assert schema["enum"] == ["a", "b"]

    def test_python_type_to_json_schema_pydantic_model(self):
        """Test converting Pydantic model to JSON schema."""
        schema = python_type_to_json_schema(TestModel)
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]

    def test_signature_to_json_schema_simple(self):
        """Test converting simple function signature to JSON schema."""

        def sample_func(x: int, y: str):
            pass

        sig = extract_signature(sample_func)
        schema = signature_to_json_schema(sig)

        assert schema["type"] == "object"
        assert "properties" in schema
        assert schema["properties"]["x"] == {"type": "integer"}
        assert schema["properties"]["y"] == {"type": "string"}
        assert "required" in schema
        assert set(schema["required"]) == {"x", "y"}

    def test_signature_to_json_schema_with_defaults(self):
        """Test converting signature with default values to JSON schema."""

        def sample_func(x: int, y: str = "default", z: float = 1.0):
            pass

        sig = extract_signature(sample_func)
        schema = signature_to_json_schema(sig)

        assert "required" in schema
        assert schema["required"] == ["x"]
        assert "y" not in schema["required"]
        assert "z" not in schema["required"]

    def test_signature_to_json_schema_no_annotations(self):
        """Test converting signature without type annotations."""

        def sample_func(x, y):
            pass

        sig = extract_signature(sample_func)
        schema = signature_to_json_schema(sig)

        assert schema["properties"]["x"] == {"type": "string"}
        assert schema["properties"]["y"] == {"type": "string"}

    def test_signature_to_json_schema_no_parameters(self):
        """Test converting signature with no parameters."""

        def sample_func():
            pass

        sig = extract_signature(sample_func)
        schema = signature_to_json_schema(sig)

        assert schema["type"] == "object"
        assert schema["properties"] == {}

    def test_extract_return_schema_with_annotation(self):
        """Test extracting return schema from annotated function."""

        def sample_func(x: int) -> List[str]:
            return [str(x)]

        schema = extract_return_schema(sample_func)
        assert schema["type"] == "array"
        assert schema["items"] == {"type": "string"}

    def test_extract_return_schema_no_annotation(self):
        """Test extracting return schema from function without return annotation."""

        def sample_func(x: int):
            return x

        schema = extract_return_schema(sample_func)
        assert schema is None

    def test_build_probe_metadata(self):
        """Test building comprehensive probe metadata."""

        def sample_func(x: int, y: str = "default") -> Dict[str, int]:
            return {"x": x}

        metadata = build_probe_metadata(sample_func, "test_probe", "Test description")

        assert metadata["id"] == "test_probe"
        assert metadata["description"] == "Test description"
        assert "signature" in metadata
        assert "param_schema" in metadata
        assert "return_schema" in metadata
        assert metadata["param_schema"]["type"] == "object"
        assert "x" in metadata["param_schema"]["properties"]
        assert "y" in metadata["param_schema"]["properties"]

    def test_build_langgraph_tool_schema(self):
        """Test building LangGraph tool schema."""
        param_schema = {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        }
        return_schema = {"type": "string"}

        schema = build_langgraph_tool_schema(
            "test_tool", "Test tool description", param_schema, return_schema
        )

        assert schema["id"] == "test_tool"
        assert schema["description"] == "Test tool description"
        assert schema["parameters"] == param_schema
        assert schema["return"] == return_schema

    def test_build_langgraph_tool_schema_no_return(self):
        """Test building LangGraph tool schema without return schema."""
        param_schema = {"type": "object", "properties": {}}

        schema = build_langgraph_tool_schema(
            "test_tool", "Test description", param_schema
        )

        assert "return" not in schema

    def test_schema_for_planner(self):
        """Test converting probe metadata to planner schema format."""

        def sample_func(x: int) -> str:
            return str(x)

        metadata = build_probe_metadata(sample_func, "planner_probe", "Planner test")
        planner_schema = schema_for_planner(metadata)

        assert planner_schema["id"] == "planner_probe"
        assert planner_schema["description"] == "Planner test"
        assert "params" in planner_schema
        assert "returns" in planner_schema
        assert planner_schema["params"] == metadata["param_schema"]
        assert planner_schema["returns"] == metadata["return_schema"]

    def test_complex_nested_types(self):
        """Test handling complex nested type structures."""
        schema = python_type_to_json_schema(List[Dict[str, List[int]]])

        assert schema["type"] == "array"
        assert schema["items"]["type"] == "object"
        assert schema["items"]["additionalProperties"]["type"] == "array"
        assert schema["items"]["additionalProperties"]["items"] == {"type": "integer"}

    def test_union_with_multiple_types(self):
        """Test Union with more than two types."""
        schema = python_type_to_json_schema(Union[int, str, float])

        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 3

    def test_optional_complex_type(self):
        """Test Optional with complex type."""
        schema = python_type_to_json_schema(Optional[List[str]])

        assert schema["type"] == "array"
        assert schema["items"] == {"type": "string"}
