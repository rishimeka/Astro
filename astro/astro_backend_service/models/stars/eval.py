"""EvalStar - evaluates results and routes execution."""

import json
from typing import TYPE_CHECKING, List

from pydantic import Field

from astro_backend_service.models.star_types import StarType
from astro_backend_service.models.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro_backend_service.executor.context import ExecutionContext
    from astro_backend_service.models.outputs import EvalDecision


class EvalStar(AtomicStar):
    """
    Evaluates results against original intent.
    Decides: continue to next node OR loop back to PlanningStar.
    """

    type: StarType = Field(default=StarType.EVAL, frozen=True)

    def validate_star(self) -> List[str]:
        """Validate EvalStar configuration."""
        errors = super().validate_star()
        # Must have PlanningStar in Constellation for loop-back
        # Validated at Constellation level
        return errors

    async def execute(self, context: "ExecutionContext") -> "EvalDecision":
        """Evaluate execution results and decide routing.

        Args:
            context: Execution context with upstream outputs.

        Returns:
            EvalDecision with continue/loop decision.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro_backend_service.llm_utils import get_llm
        from astro_backend_service.models.outputs import EvalDecision, Plan

        # Get directive
        directive = context.get_directive(self.directive_id)

        # Get the plan to check success criteria
        plan = context.get_upstream_output(Plan)
        success_criteria = (
            plan.success_criteria if plan else "Task completed successfully"
        )

        # Collect execution results
        results_parts: List[str] = []
        for node_id, output in context.node_outputs.items():
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

        system_prompt = f"""{directive.content}

You are an evaluation agent. Your job is to assess whether the execution results meet the success criteria.

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
            response = llm.invoke(messages)
            raw_content = (
                response.content if hasattr(response, "content") else str(response)
            )
            content = raw_content if isinstance(raw_content, str) else str(raw_content)

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
