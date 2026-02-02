"""Probe model for registered tool metadata."""

from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field, PrivateAttr


class Probe(BaseModel):
    """Registered probe (tool) metadata.

    A Probe wraps a function with metadata extracted from its signature
    and docstring. It is automatically registered in the ProbeRegistry
    when using the @probe decorator.
    """

    name: str = Field(..., description="Function name, used as unique identifier")
    description: str = Field(..., description="Docstring, passed to LLM")
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON schema for function arguments"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON schema for return type"
    )

    # For error messages
    module_path: str = Field(..., description="Module where probe is defined")
    function_name: str = Field(..., description="Original function name")

    # The wrapped callable (not serialized)
    _callable: Optional[Callable[..., Any]] = PrivateAttr(default=None)

    model_config = {"arbitrary_types_allowed": True}

    def invoke(self, **kwargs: Any) -> Any:
        """Execute the probe with given arguments.

        Args:
            **kwargs: Arguments to pass to the underlying function.

        Returns:
            The return value of the underlying function.

        Raises:
            RuntimeError: If the callable is not set.
        """
        if self._callable is None:
            raise RuntimeError(f"Probe '{self.name}' has no callable set")
        return self._callable(**kwargs)
