"""
Convert Python probe functions into metadata that the Planner can use to build worker toolsets.

It needs to generate:
- type hints
- JSON schema for parameters
- JSON schema for return types (optional)
- LangGraph Function Tool schema
- A unified representation for all models
"""

from inspect import signature, _empty
from typing import get_type_hints, get_origin, get_args, Union
from enum import Enum
from pydantic import BaseModel


def extract_signature(fn):
    """Extract the signature of a function.

    Args:
        fn: The function to extract the signature from.

    Returns:
        The signature object of the function.
    """
    return signature(fn)


def extract_type_hints(fn):
    """Extract type hints from a function.

    Args:
        fn: The function to extract type hints from.

    Returns:
        A dictionary mapping parameter names to their type hints.
    """
    return get_type_hints(fn)


def python_type_to_json_schema(py_type):
    """Convert a Python type to a JSON schema.

    Args:
        py_type: The Python type to convert. Supports basic types, typed lists,
                typed dicts, Pydantic models, unions, and enums.

    Returns:
        A dictionary representing the JSON schema for the given type.
    """
    # Handle basic types
    mapping = {
        int: {"type": "integer"},
        float: {"type": "number"},
        str: {"type": "string"},
        bool: {"type": "boolean"},
        dict: {"type": "object"},
        list: {"type": "array"},
    }

    # Check for basic type match
    if py_type in mapping:
        return mapping[py_type]

    # Handle Pydantic models
    if isinstance(py_type, type) and issubclass(py_type, BaseModel):
        return py_type.model_json_schema()

    # Handle Enums
    if isinstance(py_type, type) and issubclass(py_type, Enum):
        return {"type": "string", "enum": [member.value for member in py_type]}

    # Handle generic types (list[int], dict[str, int], etc.)
    origin = get_origin(py_type)
    args = get_args(py_type)

    # Handle typed lists: list[int], list[str], etc.
    if origin is list:
        schema = {"type": "array"}
        if args:
            schema["items"] = python_type_to_json_schema(args[0])
        return schema

    # Handle typed dicts: dict[str, int], etc.
    if origin is dict:
        schema = {"type": "object"}
        if args and len(args) == 2:
            schema["additionalProperties"] = python_type_to_json_schema(args[1])
        return schema

    # Handle Union types (including Optional)
    if origin is Union:
        # Filter out NoneType for Optional handling
        non_none_types = [arg for arg in args if arg is not type(None)]

        if len(non_none_types) == 1:
            # This is Optional[T], return schema for T
            return python_type_to_json_schema(non_none_types[0])
        else:
            # Multiple types in Union
            return {
                "anyOf": [python_type_to_json_schema(arg) for arg in non_none_types]
            }

    # Default fallback
    return {"type": "string"}


def extract_return_schema(fn):
    """Extract the return type schema from a function.

    Args:
        fn: The function to extract the return type from.

    Returns:
        A JSON schema dictionary for the return type, or None if no return annotation exists.
    """
    annotation = get_type_hints(fn).get("return")
    if annotation:
        return python_type_to_json_schema(annotation)
    return None


def signature_to_json_schema(sig):
    """Convert a function's signature to JSON schema for its parameters.

    Args:
        sig: The signature object to convert.

    Returns:
        A JSON schema dictionary representing the function's parameters.
    """
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        param_type = param.annotation

        # Handle unannotated parameters
        if param_type is _empty:
            param_schema = {"type": "string"}
        else:
            param_schema = python_type_to_json_schema(param_type)

        properties[param_name] = param_schema

        if param.default is param.empty:
            required.append(param_name)

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema


def build_langgraph_tool_schema(
    probe_id, description, param_schema, return_schema=None
):
    """Build a LangGraph Function Tool schema for a probe.

    Args:
        probe_id: The unique identifier of the probe.
        description: A human-readable description of the probe.
        param_schema: JSON schema for the probe's parameters.
        return_schema: Optional JSON schema for the probe's return type.
    """
    tool_schema = {
        "id": probe_id,
        "description": description,
        "parameters": param_schema,
    }

    if return_schema is not None:
        tool_schema["return"] = return_schema

    return tool_schema


def build_probe_metadata(fn, probe_id, description):
    """
    Build comprehensive metadata for a probe function.
    Args:
        fn: The probe function.
        probe_id: The unique identifier of the probe.
        description: A human-readable description of the probe.
    Returns:
        A dictionary containing the probe's metadata.
    """
    sig = extract_signature(fn)
    params = signature_to_json_schema(sig)
    returns = extract_return_schema(fn)

    return {
        "id": probe_id,
        "description": description,
        "signature": sig,
        "param_schema": params,
        "return_schema": returns,
    }


def schema_for_planner(probe_metadata):
    """
    Convert probe metadata into a schema format suitable for the Planner.
    Args:
        probe_metadata: The metadata dictionary of the probe.
    Returns:
        A dictionary formatted for the Planner's use.
    """
    return {
        "id": probe_metadata["id"],
        "description": probe_metadata["description"],
        "params": probe_metadata["param_schema"],
        "returns": probe_metadata["return_schema"],
    }
