"""Shared tool/probe support for AtomicStar types."""

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

    from astro.core.models.outputs import ToolCall
    from astro.core.probes.probe import Probe


def get_available_probes(probe_ids: list[str]) -> list["Probe"]:
    """Get probes from registry filtered by allowed probe IDs.

    Args:
        probe_ids: List of probe names allowed for this star.

    Returns:
        List of Probe instances that match the allowed names.
    """
    from astro.core.probes.registry import ProbeRegistry

    if probe_ids:
        return ProbeRegistry.get_many(probe_ids)
    return []


def create_langchain_tools(
    probes: list["Probe"],
) -> tuple[list[Any], dict[str, "Probe"]]:
    """Convert probes to LangChain tools.

    Args:
        probes: List of Probe instances to convert.

    Returns:
        Tuple of (list of LangChain StructuredTool, dict mapping name to Probe)
    """
    from langchain_core.tools import StructuredTool

    langchain_tools = []
    probe_map: dict[str, Probe] = {}

    for probe in probes:
        tool = StructuredTool.from_function(
            func=probe._callable,
            name=probe.name,
            description=probe.description,
            args_schema=None,  # Will infer from function signature
        )
        langchain_tools.append(tool)
        probe_map[probe.name] = probe

    return langchain_tools, probe_map


def execute_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    probe_map: dict[str, "Probe"],
    context: Any | None = None,
) -> tuple[str | None, str | None]:
    """Execute a single tool call, with optional result caching.

    Args:
        tool_name: Name of the tool to execute.
        tool_args: Arguments to pass to the tool.
        probe_map: Dictionary mapping tool names to Probe instances.
        context: Optional ExecutionContext for tool result caching.

    Returns:
        Tuple of (result_string, error_string). One will be None.
    """
    # Check cache first
    if context is not None and hasattr(context, "get_cached_tool_result"):
        cached = context.get_cached_tool_result(tool_name, tool_args)
        if cached is not None:
            return cached, None

    try:
        if tool_name in probe_map:
            result = str(probe_map[tool_name].invoke(**tool_args))
            # Cache the result
            if context is not None and hasattr(context, "cache_tool_result"):
                context.cache_tool_result(tool_name, tool_args, result)
            return result, None
        else:
            return None, f"Tool '{tool_name}' not found"
    except Exception as e:
        return None, str(e)


async def execute_with_tools(
    llm: "BaseChatModel",
    messages: list["BaseMessage"],
    probe_ids: list[str],
    max_iterations: int = 5,
    context: Any | None = None,
    max_tokens: int | None = None,
) -> tuple[str, list["ToolCall"], int]:
    """Execute LLM with optional tool calling support.

    This is a shared helper that handles the tool calling loop for all AtomicStar types.

    Args:
        llm: The LangChain LLM instance.
        messages: Initial messages to send to the LLM.
        probe_ids: List of probe names allowed for tool calling.
        max_iterations: Maximum iterations for tool calling loop.
        context: Optional ExecutionContext for tool result caching.

    Returns:
        Tuple of (final_result, list_of_tool_calls, iterations_used)
    """
    from langchain_core.messages import ToolMessage

    from astro.core.models.outputs import ToolCall

    tool_calls: list[ToolCall] = []
    iterations = 0

    # Get available probes based on allowed IDs
    available_probes = get_available_probes(probe_ids)

    if available_probes:
        # Convert probes to LangChain tools
        langchain_tools, probe_map = create_langchain_tools(available_probes)

        # Bind tools to LLM, then optionally bind max_tokens
        llm_with_tools = llm.bind_tools(langchain_tools)
        if max_tokens:
            llm_with_tools = llm_with_tools.bind(max_tokens=max_tokens)

        # Tool calling iteration loop
        while iterations < max_iterations:
            iterations += 1

            response = llm_with_tools.invoke(messages)

            # Check if response has tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                # Append assistant message with tool calls
                messages.append(response)

                # Process each tool call
                tool_messages = []
                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})

                    # Execute the tool
                    tool_result, tool_error = execute_tool_call(
                        tool_name, tool_args, probe_map, context
                    )

                    # Record the tool call
                    tool_calls.append(
                        ToolCall(
                            tool_name=tool_name,
                            arguments=tool_args,
                            result=tool_result,
                            error=tool_error,
                        )
                    )

                    # Create ToolMessage for LLM context
                    tool_messages.append(
                        ToolMessage(
                            content=tool_result or tool_error or "",
                            tool_call_id=tc.get("id", ""),
                        )
                    )

                # Append all tool messages
                messages.extend(tool_messages)

                # Continue to next iteration
                continue

            # No tool calls - extract final response
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            result = content if isinstance(content, str) else str(content)

            # Debug: Log response metadata to understand truncation
            if hasattr(response, "response_metadata"):
                finish_reason = response.response_metadata.get(
                    "finish_reason", "unknown"
                )
                logger.info(
                    f"LLM finish_reason: {finish_reason}, output_length: {len(result)} chars"
                )
                if finish_reason == "length":
                    logger.warning(
                        f"LLM hit max_tokens limit! Output truncated at {len(result)} chars"
                    )

            return result, tool_calls, iterations

        # Reached max iterations
        return "Maximum iterations reached without completion", tool_calls, iterations

    else:
        # No tools available - simple single-shot execution
        iterations = 1
        if max_tokens:
            response = llm.invoke(messages, max_tokens=max_tokens)
        else:
            response = llm.invoke(messages)

        content = response.content if hasattr(response, "content") else str(response)
        result = content if isinstance(content, str) else str(content)

        # Debug: Log response metadata to understand truncation
        if hasattr(response, "response_metadata"):
            finish_reason = response.response_metadata.get("finish_reason", "unknown")
            logger.info(
                f"LLM finish_reason (no tools): {finish_reason}, output_length: {len(result)} chars"
            )
            if finish_reason == "length":
                logger.warning(
                    f"LLM hit max_tokens limit! Output truncated at {len(result)} chars"
                )

        return result, tool_calls, iterations
