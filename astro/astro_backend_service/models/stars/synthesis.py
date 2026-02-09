"""SynthesisStar - aggregates outputs from multiple upstream Stars."""

from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import Field

from astro_backend_service.models.star_types import StarType
from astro_backend_service.models.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro_backend_service.executor.context import ExecutionContext
    from astro_backend_service.models.outputs import SynthesisOutput


class SynthesisStar(AtomicStar):
    """
    Aggregates outputs from multiple upstream Stars.
    Can use probes/tools for output formatting and delivery
    (e.g., PDF generation, Slack posting, external storage).
    """

    type: StarType = Field(default=StarType.SYNTHESIS, frozen=True)

    # Synthesis-specific configuration
    max_tool_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum iterations for tool calling during synthesis",
    )

    def validate_star(self) -> List[str]:
        """Validate SynthesisStar configuration."""
        errors = super().validate_star()
        # Must have upstream - validated at Constellation level
        return errors

    async def execute(self, context: "ExecutionContext") -> "SynthesisOutput":
        """Aggregate and format outputs from upstream stars, optionally using tools.

        Args:
            context: Execution context with upstream outputs.

        Returns:
            SynthesisOutput with formatted result.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro_backend_service.llm_utils import get_llm
        from astro_backend_service.models.outputs import SynthesisOutput
        from astro_backend_service.models.stars.tool_support import execute_with_tools

        # Get directive for formatting instructions
        directive = context.get_directive(self.directive_id)

        # Resolve probes for this star (directive probes + star probes)
        resolved_probes = self.resolve_probes(directive)

        # Collect upstream outputs, filtering out orchestration artifacts
        # (Plan and EvalDecision are not content to synthesize)
        # NOTE: Synthesis stars need ALL node outputs (not just direct upstream)
        # to create comprehensive reports combining all analyst inputs
        sources: List[str] = []
        upstream_content_parts: List[str] = []

        # Use all node_outputs for synthesis (special case - needs full context)
        all_outputs = context.node_outputs
        for node_id, output in all_outputs.items():
            # Skip orchestration outputs (Plan has .tasks, EvalDecision has .decision)
            if hasattr(output, "tasks") or hasattr(output, "decision"):
                continue

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

        # Build tool instructions if probes are available
        tool_instructions = ""
        if resolved_probes:
            tool_instructions = """
You have access to tools for formatting and delivering the synthesized output.
Use these tools to generate PDFs, post to Slack, save to external storage, or perform other delivery tasks.
Call the appropriate tools after synthesizing the content, then provide a summary of what was done."""

        # Build synthesis prompt
        system_prompt = f"""{directive.content}

You are a synthesis agent. Your job is to take the outputs from multiple execution steps and combine them into a coherent, well-formatted final result.
{tool_instructions}

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
            # Execute with tool support
            result, tool_calls, iterations = await execute_with_tools(
                llm=llm,
                messages=messages,
                probe_ids=resolved_probes,
                max_iterations=self.max_tool_iterations,
            )

            # Determine format type from result
            format_type = (
                "markdown"
                if "#" in result or "**" in result or "-" in result
                else "text"
            )

            # Build metadata including tool call info
            metadata: Dict[str, Any] = {"original_query": context.original_query}
            if tool_calls:
                metadata["tool_calls"] = [
                    {
                        "tool_name": tc.tool_name,
                        "result": tc.result,
                        "error": tc.error,
                    }
                    for tc in tool_calls
                ]
                metadata["tool_iterations"] = iterations

            return SynthesisOutput(
                formatted_result=result,
                format_type=format_type,
                sources=sources,
                metadata=metadata,
            )

        except Exception as e:
            # Fallback: just concatenate outputs
            return SynthesisOutput(
                formatted_result=f"Synthesis error: {str(e)}\n\nRaw outputs:\n{upstream_content}",
                format_type="text",
                sources=sources,
                metadata={"error": str(e)},
            )
