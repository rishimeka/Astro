"""SynthesisStar - aggregates outputs from multiple upstream Stars."""

from typing import TYPE_CHECKING, List

from pydantic import Field

from astro_backend_service.models.star_types import StarType
from astro_backend_service.models.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro_backend_service.executor.context import ExecutionContext
    from astro_backend_service.models.outputs import SynthesisOutput


class SynthesisStar(AtomicStar):
    """
    Aggregates outputs from multiple upstream Stars.
    Can optionally use probes for output formatting/delivery
    (e.g., PDF generation, Slack posting, external storage).
    """

    type: StarType = Field(default=StarType.SYNTHESIS, frozen=True)

    def validate_star(self) -> List[str]:
        """Validate SynthesisStar configuration."""
        errors = super().validate_star()
        # Must have upstream - validated at Constellation level
        return errors

    async def execute(self, context: "ExecutionContext") -> "SynthesisOutput":
        """Aggregate and format outputs from upstream stars.

        Args:
            context: Execution context with upstream outputs.

        Returns:
            SynthesisOutput with formatted result.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro_backend_service.llm_utils import get_llm
        from astro_backend_service.models.outputs import SynthesisOutput

        # Get directive for formatting instructions
        directive = context.get_directive(self.directive_id)

        # Collect all upstream outputs
        sources: List[str] = []
        upstream_content_parts: List[str] = []

        for node_id, output in context.node_outputs.items():
            sources.append(node_id)

            if hasattr(output, "result"):
                upstream_content_parts.append(
                    f"## Output from {node_id}\n{output.result}"
                )
            elif hasattr(output, "formatted_result"):
                upstream_content_parts.append(
                    f"## Output from {node_id}\n{output.formatted_result}"
                )
            elif hasattr(output, "worker_outputs"):
                # ExecutionResult
                for i, wo in enumerate(output.worker_outputs):
                    if hasattr(wo, "result"):
                        upstream_content_parts.append(
                            f"## Worker {i+1} output\n{wo.result}"
                        )
            elif isinstance(output, dict):
                if "output" in output:
                    upstream_content_parts.append(
                        f"## Output from {node_id}\n{output['output']}"
                    )
                elif "result" in output:
                    upstream_content_parts.append(
                        f"## Output from {node_id}\n{output['result']}"
                    )

        upstream_content = "\n\n".join(upstream_content_parts)

        # Build synthesis prompt
        system_prompt = f"""{directive.content}

You are a synthesis agent. Your job is to take the outputs from multiple execution steps and combine them into a coherent, well-formatted final result.

Guidelines:
- Combine information logically, eliminating redundancy
- Format the output clearly (use markdown if appropriate)
- Maintain accuracy - don't add information not present in the inputs
- If there are conflicting outputs, acknowledge and reconcile them
- Present the most important findings first"""

        user_message = f"""Original request: {context.original_query}

Goal: {context.constellation_purpose}

Here are the outputs from the execution steps that need to be synthesized:

{upstream_content}

Please synthesize these outputs into a clear, comprehensive final result."""

        # Get LLM and synthesize
        llm = get_llm(temperature=0.3)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        try:
            response = llm.invoke(messages)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            result = content if isinstance(content, str) else str(content)

            # Determine format type from result
            format_type = (
                "markdown"
                if "#" in result or "**" in result or "-" in result
                else "text"
            )

            return SynthesisOutput(
                formatted_result=result,
                format_type=format_type,
                sources=sources,
                metadata={"original_query": context.original_query},
            )

        except Exception as e:
            # Fallback: just concatenate outputs
            return SynthesisOutput(
                formatted_result=f"Synthesis error: {str(e)}\n\nRaw outputs:\n{upstream_content}",
                format_type="text",
                sources=sources,
                metadata={"error": str(e)},
            )
