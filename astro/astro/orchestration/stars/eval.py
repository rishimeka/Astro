"""EvalStar - evaluates results and routes execution."""

import json
from typing import TYPE_CHECKING

from pydantic import Field

from astro.orchestration.models.star_types import StarType
from astro.orchestration.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro.core.models.outputs import EvalDecision  # type: ignore[attr-defined]
    from astro.orchestration.context import ConstellationContext


class EvalStar(AtomicStar):
    """
    Evaluates results against original intent.
    Can use probes/tools to verify results (e.g., run tests, check outputs).
    Decides: continue to next node OR loop back to PlanningStar.
    """

    type: StarType = Field(default=StarType.EVAL, frozen=True)

    # Eval-specific configuration
    max_tool_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum iterations for tool calling during evaluation",
    )

    def validate_star(self) -> list[str]:
        """Validate EvalStar configuration."""
        errors = super().validate_star()
        # Must have PlanningStar in Constellation for loop-back
        # Validated at Constellation level
        return errors

    async def execute(self, context: "ConstellationContext") -> "EvalDecision":
        """Evaluate execution results and decide routing, optionally using tools.

        Args:
            context: Execution context with upstream outputs.

        Returns:
            EvalDecision with continue/loop decision.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro.core.llm.utils import get_llm
        from astro.core.models.outputs import (  # type: ignore[attr-defined]
            EvalDecision,
            Plan,
        )
        from astro.orchestration.stars.tool_support import execute_with_tools

        # Get directive
        directive = context.get_directive(self.directive_id)

        # Resolve probes for this star (directive probes + star probes)
        resolved_probes = self.resolve_probes(directive)

        # Get the plan to check success criteria
        plan = context.get_upstream_output(Plan)
        success_criteria = (
            plan.success_criteria if plan else "Task completed successfully"
        )

        # Collect execution results from direct upstream only
        direct_upstream = context.get_direct_upstream_outputs()
        results_parts: list[str] = []
        for node_id, output in direct_upstream.items():
            if hasattr(output, "result"):
                results_parts.append(f"- {node_id}: {output.result[:500]}")
            elif hasattr(output, "worker_outputs"):
                for i, wo in enumerate(output.worker_outputs):
                    status = wo.status if hasattr(wo, "status") else "unknown"
                    result = wo.result[:300] if hasattr(wo, "result") else "no result"
                    results_parts.append(f"- Worker {i+1} ({status}): {result}")
            elif hasattr(output, "formatted_result"):
                results_parts.append(f"- {node_id}: {output.formatted_result[:500]}")

        results_summary = (
            "\n".join(results_parts) if results_parts else "No results available"
        )

        # Build tool instructions if probes are available
        tool_instructions = ""
        if resolved_probes:
            tool_instructions = """
You have access to tools that can help verify the execution results.
Use these tools to run tests, check outputs, validate data, or perform other verification tasks before making your decision.
Once you have gathered sufficient verification data, output your final decision as JSON."""

        system_prompt = f"""{directive.content}

You are an evaluation agent. Your job is to assess whether the execution results meet the success criteria.
{tool_instructions}

Respond with JSON in this exact format:
{{
    "decision": "continue",  // or "loop" if results are inadequate
    "reasoning": "Explanation for your decision"
}}

- Choose "continue" if the results adequately address the original request
- Choose "loop" if the results are incomplete, incorrect, or need improvement
- Be pragmatic - minor imperfections are acceptable if the core request is satisfied
- Consider the loop count: we've already looped {context.loop_count} times"""

        user_message = f"""Original request: {context.original_query}

Success criteria: {success_criteria}

Execution results:
{results_summary}

Evaluate these results. Should we continue to finalization or loop back for improvements?"""

        llm = get_llm(temperature=0.2)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        try:
            # Execute with tool support
            content, tool_calls, iterations = await execute_with_tools(
                llm=llm,  # type: ignore[arg-type]
                messages=messages,
                probe_ids=resolved_probes,
                max_iterations=self.max_tool_iterations,
            )

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            eval_data = json.loads(content.strip())

            decision = eval_data.get("decision", "continue").lower()
            if decision not in ("continue", "loop"):
                decision = "continue"

            return EvalDecision(
                decision=decision,
                reasoning=eval_data.get("reasoning", ""),
                loop_target=None,  # Runner determines the target
            )

        except Exception as e:
            # Default to continue on error
            return EvalDecision(
                decision="continue",
                reasoning=f"Evaluation error ({str(e)}), defaulting to continue",
            )
