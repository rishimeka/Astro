"""The @probe decorator for registering tools."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

from langchain_core.tools import BaseTool

from astro.core.probes.probe import Probe
from astro.core.probes.registry import ProbeRegistry


def _python_type_to_json_type(python_type: type[Any]) -> str:
    """Convert Python type to JSON Schema type.

    Args:
        python_type: A Python type annotation.

    Returns:
        The corresponding JSON Schema type string.
    """
    type_map: dict[type[Any], str] = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    # Handle generic types by checking origin
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
    return type_map.get(python_type, "string")


def probe(func: Callable[..., Any]) -> BaseTool:
    """Decorator that registers a function as a probe.

    This decorator:
    - Extracts metadata from function signature and docstring
    - Wraps with LangChain's tool decorator
    - Registers in global ProbeRegistry

    The docstring becomes the tool description shown to the LLM.
    Type hints are converted to JSON schema for tool parameters.

    Args:
        func: The function to decorate.

    Returns:
        The wrapped function as a LangChain BaseTool.

    Raises:
        ValueError: If function has no docstring.
        DuplicateProbeError: If probe name already registered.

    Example:
        @probe
        def search_web(query: str, max_results: int = 10) -> str:
            '''Search the web for information and return relevant results.

            Args:
                query: The search query
                max_results: Maximum number of results to return

            Returns:
                Formatted search results as a string
            '''
            # Implementation...
            return "search results"
    """
    # Validate docstring exists
    if not func.__doc__:
        raise ValueError(
            f"Probe '{func.__name__}' must have a docstring. "
            "The docstring is used as the tool description for the LLM."
        )

    # Extract metadata
    name = func.__name__
    description = func.__doc__.strip()
    module_path = func.__module__

    # Extract input schema from type hints
    try:
        hints = get_type_hints(func)
    except Exception:
        # Fall back if get_type_hints fails (e.g., forward references)
        hints = {}

    return_type = hints.pop("return", None)

    input_schema: dict[str, Any] | None = None
    if hints:
        input_schema = {"type": "object", "properties": {}, "required": []}
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name in hints:
                input_schema["properties"][param_name] = {
                    "type": _python_type_to_json_type(hints[param_name])
                }
                if param.default is inspect.Parameter.empty:
                    input_schema["required"].append(param_name)

    output_schema: dict[str, Any] | None = None
    if return_type:
        output_schema = {"type": _python_type_to_json_type(return_type)}

    # Create Probe instance
    probe_instance = Probe(
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        module_path=module_path,
        function_name=name,
    )
    probe_instance._callable = func

    # Register
    ProbeRegistry.register(probe_instance)

    # Wrap with LangChain's tool decorator
    from langchain_core.tools import tool as langgraph_tool

    @langgraph_tool
    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    # Preserve probe metadata on wrapped function
    wrapped._probe = probe_instance  # type: ignore[attr-defined]

    return wrapped
