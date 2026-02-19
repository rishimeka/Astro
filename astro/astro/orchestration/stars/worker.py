"""WorkerStar - generic flexible execution unit."""

import logging
from typing import TYPE_CHECKING

from pydantic import Field

logger = logging.getLogger(__name__)

from astro.orchestration.models.star_types import StarType
from astro.orchestration.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro.core.models.outputs import WorkerOutput
    from astro.orchestration.context import ConstellationContext


class WorkerStar(AtomicStar):
    """Generic flexible execution unit.

    The atomic building block — runs until task complete or max iterations.
    """

    type: StarType = Field(default=StarType.WORKER, frozen=True)

    # Worker-specific configuration
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum iterations before stopping",
    )

    async def execute(self, context: "ConstellationContext") -> "WorkerOutput":
        """Execute the worker star with LLM.

        Args:
            context: Constellation execution context with variables and upstream outputs.

        Returns:
            WorkerOutput with the result.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro.core.llm.utils import get_langchain_llm
        from astro.core.models.outputs import ToolCall, WorkerOutput

        # Get the directive for this star
        directive = context.get_directive(self.directive_id)

        # Build the system prompt from directive content
        system_prompt = directive.content

        # Substitute template variables in the prompt
        for var_name, var_value in context.variables.items():
            system_prompt = system_prompt.replace(
                f"@variable:{var_name}", str(var_value)
            )

        # Build user message from original query and context
        user_message_parts = []

        if context.original_query:
            user_message_parts.append(f"User's request: {context.original_query}")

        if context.constellation_purpose:
            user_message_parts.append(f"Overall goal: {context.constellation_purpose}")

        # Include direct upstream outputs for context (not all prior outputs)
        direct_upstream = context.get_direct_upstream_outputs()
        if direct_upstream:
            user_message_parts.append("\nContext from previous steps:")
            for i, (node_id, output) in enumerate(direct_upstream.items()):
                if hasattr(output, "result"):
                    user_message_parts.append(f"- Step {i+1}: {output.result[:500]}")
                elif hasattr(output, "formatted_result"):
                    user_message_parts.append(
                        f"- Step {i+1}: {output.formatted_result[:500]}"
                    )
                elif isinstance(output, dict) and "output" in output:
                    user_message_parts.append(
                        f"- Step {i+1}: {str(output['output'])[:500]}"
                    )

        # Add any specific variables as context
        if context.variables:
            user_message_parts.append("\nProvided information:")
            for key, value in context.variables.items():
                user_message_parts.append(f"- {key}: {value}")

        user_message = (
            "\n".join(user_message_parts)
            if user_message_parts
            else "Please complete the task."
        )

        # Use temperature from config if specified, otherwise default to 0.7
        temperature = self.config.get("temperature", 0.7)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        tool_calls: list[ToolCall] = []
        iterations = 0

        # Get available probes/tools - combining Directive + Star probes
        from astro.core.probes.registry import ProbeRegistry

        # Resolve final probe set: Directive.probe_ids ∪ Star.probe_ids (deduplicated)
        resolved_probe_ids = self.resolve_probes(directive)

        # Filter probes to only those in the resolved set (probe scoping)
        if resolved_probe_ids:
            available_probes = ProbeRegistry.get_many(resolved_probe_ids)
        else:
            # If no probe_ids specified, no tools available (synthesis-only star)
            available_probes = []

        # If we have tools, bind them to the LLM for tool calling
        if available_probes:
            # Get LangChain chat model for tool calling support
            llm = get_langchain_llm(temperature=temperature)

            # Convert probes to LangChain tools
            langchain_tools = []
            probe_map = {}  # name -> probe for lookup

            for probe in available_probes:
                # Use the LangChain tool wrapper created by the @probe decorator
                from langchain_core.tools import StructuredTool

                tool = StructuredTool.from_function(
                    func=probe._callable,
                    name=probe.name,
                    description=probe.description,
                    args_schema=None,  # Will infer from function
                )
                langchain_tools.append(tool)
                probe_map[probe.name] = probe

            # Bind tools to LLM, then optionally bind max_tokens
            llm_with_tools = llm.bind_tools(langchain_tools)
            max_tokens = self.config.get("max_tokens")
            if max_tokens:
                llm_with_tools = llm_with_tools.bind(max_tokens=max_tokens)

            try:
                # Iteration loop with tool calling
                while iterations < self.max_iterations:
                    iterations += 1

                    response = llm_with_tools.invoke(messages)

                    # Check if the response has tool calls
                    if hasattr(response, "tool_calls") and response.tool_calls:
                        from langchain_core.messages import ToolMessage

                        # First, append the assistant message with tool calls ONCE
                        messages.append(response)

                        # Then process each tool call and collect ToolMessages
                        tool_messages = []
                        for tc in response.tool_calls:
                            tool_name = tc.get("name", "")
                            tool_args = tc.get("args", {})

                            # Execute the probe
                            tool_result = None
                            tool_error = None
                            try:
                                # Check tool result cache
                                cached = context.get_cached_tool_result(
                                    tool_name, tool_args
                                )
                                if cached is not None:
                                    tool_result = cached
                                elif tool_name in probe_map:
                                    tool_result = str(
                                        probe_map[tool_name].invoke(**tool_args)
                                    )
                                    context.cache_tool_result(
                                        tool_name, tool_args, tool_result
                                    )
                                else:
                                    tool_error = f"Tool '{tool_name}' not found"
                            except Exception as e:
                                tool_error = str(e)

                            tool_calls.append(
                                ToolCall(
                                    tool_name=tool_name,
                                    arguments=tool_args,
                                    result=tool_result,
                                    error=tool_error,
                                )
                            )

                            # Create ToolMessage for this tool call
                            tool_messages.append(
                                ToolMessage(
                                    content=tool_result or tool_error or "",
                                    tool_call_id=tc.get("id", ""),
                                )
                            )

                        # Append all tool messages after the assistant message
                        messages.extend(tool_messages)

                        # Continue to next iteration to process tool results
                        continue

                    # No tool calls - we have a final response
                    content = (
                        response.content
                        if hasattr(response, "content")
                        else str(response)
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

                    return WorkerOutput(
                        result=result,
                        tool_calls=tool_calls,
                        iterations=iterations,
                        status="completed",
                    )

                # Reached max iterations
                return WorkerOutput(
                    result="Maximum iterations reached without completion",
                    tool_calls=tool_calls,
                    iterations=iterations,
                    status="max_iterations",
                )

            except Exception as e:
                return WorkerOutput(
                    result=f"Error during execution: {str(e)}",
                    tool_calls=tool_calls,
                    iterations=max(iterations, 1),
                    status="failed",
                )
        else:
            # No tools available - simple single-shot execution
            # Get LangChain chat model for consistent message handling
            llm = get_langchain_llm(temperature=temperature)

            try:
                # Apply max_tokens if specified
                max_tokens = self.config.get("max_tokens")
                if max_tokens:
                    response = llm.invoke(messages, max_tokens=max_tokens)
                else:
                    response = llm.invoke(messages)
                iterations = 1

                content = (
                    response.content if hasattr(response, "content") else str(response)
                )
                result = content if isinstance(content, str) else str(content)

                return WorkerOutput(
                    result=result,
                    tool_calls=tool_calls,
                    iterations=iterations,
                    status="completed",
                )

            except Exception as e:
                return WorkerOutput(
                    result=f"Error during execution: {str(e)}",
                    tool_calls=tool_calls,
                    iterations=max(iterations, 1),
                    status="failed",
                )
