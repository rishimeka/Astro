"""Probe model for registered tool metadata."""

from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, Field, PrivateAttr


class Probe(BaseModel):
    """Registered probe (tool) metadata.

    A Probe wraps a function with metadata extracted from its signature
    and docstring. It is automatically registered in the ProbeRegistry
    when using the @probe decorator.

    Example:
        @probe
        def search_web(query: str) -> str:
            '''Search the web for information.'''
            return perform_web_search(query)

        # Probe metadata is extracted:
        # - name: "search_web"
        # - description: "Search the web for information."
        # - input_schema: {"type": "object", "properties": {"query": {"type": "string"}}}
        # - output_schema: {"type": "string"}
    """

    name: str = Field(..., description="Function name, used as unique identifier")
    description: str = Field(..., description="Docstring, passed to LLM")
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON schema for function arguments"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON schema for return type"
    )

    # For error messages and debugging
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

    def as_langchain_tool(self) -> Any:
        """Convert probe to LangChain tool.

        Returns:
            LangChain tool that can be bound to LLM.
        """
        from langchain_core.tools import tool as langgraph_tool
        from functools import wraps

        @langgraph_tool
        @wraps(self._callable)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return self.invoke(**kwargs)

        wrapped._probe = self  # type: ignore[attr-defined]
        return wrapped
