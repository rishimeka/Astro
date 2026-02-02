"""WorkerStar - generic flexible execution unit."""

from typing import TYPE_CHECKING, List

from pydantic import Field

from astro_backend_service.models.star_types import StarType
from astro_backend_service.models.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro_backend_service.executor.context import ExecutionContext
    from astro_backend_service.models.outputs import WorkerOutput


class WorkerStar(AtomicStar):
    """
    Generic flexible execution unit.
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

    async def execute(self, context: "ExecutionContext") -> "WorkerOutput":
        """Execute the worker star with LLM.

        Args:
            context: Execution context with variables and upstream outputs.

        Returns:
            WorkerOutput with the result.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro_backend_service.llm_utils import get_llm
        from astro_backend_service.models.outputs import ToolCall, WorkerOutput

        # Get the directive for this star
        directive = context.get_directive(self.directive_id)

        # Build the system prompt from directive content
        system_prompt = directive.content

        # Substitute template variables in the prompt
        for var_name, var_value in context.variables.items():
            system_prompt = system_prompt.replace(
                f"{{{{${var_name}}}}}", str(var_value)
            )
            system_prompt = system_prompt.replace(
                f"@variable:{var_name}", str(var_value)
            )

        # Build user message from original query and context
        user_message_parts = []

        if context.original_query:
            user_message_parts.append(f"User's request: {context.original_query}")

        if context.constellation_purpose:
            user_message_parts.append(f"Overall goal: {context.constellation_purpose}")

        # Include upstream outputs for context
        upstream_outputs = list(context.node_outputs.values())
        if upstream_outputs:
            user_message_parts.append("\nContext from previous steps:")
            for i, output in enumerate(upstream_outputs):
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

        # Get LLM and make the call
        llm = get_llm(temperature=0.7)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        tool_calls: List[ToolCall] = []
        iterations = 0

        try:
            # Simple single-shot execution for now
            # TODO: Add tool/probe support with iteration loop
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
                iterations=iterations,
                status="failed",
            )
