"""PlanningStar - generates structured execution plans."""

import json
from typing import TYPE_CHECKING, List

from pydantic import Field

from astro_backend_service.models.star_types import StarType
from astro_backend_service.models.stars.base import AtomicStar

if TYPE_CHECKING:
    from astro_backend_service.executor.context import ExecutionContext
    from astro_backend_service.models.outputs import Plan


class PlanningStar(AtomicStar):
    """
    Generates structured execution plan.
    Can use probes/tools to gather context for better planning.
    Validates output matches plan schema.
    """

    type: StarType = Field(default=StarType.PLANNING, frozen=True)

    # Planning-specific configuration
    max_tool_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum iterations for tool calling during planning",
    )

    def validate_star(self) -> List[str]:
        """Validate PlanningStar configuration."""
        errors = super().validate_star()
        # Must have ExecutionStar downstream - validated at Constellation level
        return errors

    async def execute(self, context: "ExecutionContext") -> "Plan":
        """Generate an execution plan, optionally using tools to gather context.

        Args:
            context: Execution context with the original query.

        Returns:
            Plan with tasks to execute.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro_backend_service.llm_utils import get_llm
        from astro_backend_service.models.outputs import Plan, Task
        from astro_backend_service.models.stars.tool_support import execute_with_tools

        # Get directive for system prompt
        directive = context.get_directive(self.directive_id)

        # Resolve probes for this star (directive probes + star probes)
        resolved_probes = self.resolve_probes(directive)

        # Build tool instructions if probes are available
        tool_instructions = ""
        if resolved_probes:
            tool_instructions = """
You have access to tools that can help gather context for better planning.
Use these tools to understand the current state, gather requirements, or fetch relevant information before creating your plan.
Once you have gathered sufficient context, output your final plan as JSON."""

        system_prompt = f"""{directive.content}

You are a planning agent. Given the user's request and context, create a structured execution plan.
{tool_instructions}

Output your plan as JSON with this structure:
{{
    "tasks": [
        {{
            "id": "task_1",
            "description": "Clear description of what needs to be done",
            "dependencies": []
        }},
        {{
            "id": "task_2",
            "description": "Another task that depends on task_1",
            "dependencies": ["task_1"]
        }}
    ],
    "context": "Additional context for executing the tasks",
    "success_criteria": "How to evaluate if the plan succeeded"
}}

Keep the plan focused and actionable. Each task should be completable by a single worker."""

        # Build user message
        user_parts = [f"User's request: {context.original_query}"]

        if context.constellation_purpose:
            user_parts.append(f"Overall goal: {context.constellation_purpose}")

        if context.variables:
            user_parts.append("Provided information:")
            for key, value in context.variables.items():
                user_parts.append(f"- {key}: {value}")

        # Include any upstream context (e.g., from DocEx)
        if context.node_outputs:
            user_parts.append("\nContext from previous steps:")
            for output in context.node_outputs.values():
                if hasattr(output, "documents"):
                    user_parts.append(f"- Documents available: {len(output.documents)}")
                elif hasattr(output, "result"):
                    user_parts.append(f"- Previous result: {str(output.result)[:300]}")

        user_message = "\n".join(user_parts)

        # Get LLM
        llm = get_llm(temperature=0.3)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        try:
            # Execute with tool support
            content, tool_calls, iterations = await execute_with_tools(
                llm=llm,
                messages=messages,
                probe_ids=resolved_probes,
                max_iterations=self.max_tool_iterations,
            )

            # Parse JSON response
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            plan_data = json.loads(content.strip())

            # Build Plan object
            tasks: List[Task] = []
            for task_data in plan_data.get("tasks", []):
                tasks.append(
                    Task(
                        id=task_data.get("id", f"task_{len(tasks)+1}"),
                        description=task_data.get("description", ""),
                        directive_id=task_data.get("directive_id"),
                        dependencies=task_data.get("dependencies", []),
                        metadata=task_data.get("metadata", {}),
                    )
                )

            return Plan(
                tasks=tasks,
                context=plan_data.get("context", ""),
                success_criteria=plan_data.get(
                    "success_criteria", "All tasks completed successfully"
                ),
            )

        except json.JSONDecodeError:
            # Fallback: create a single task from the response
            return Plan(
                tasks=[
                    Task(
                        id="task_1",
                        description=context.original_query,
                    )
                ],
                context="Plan generation failed, executing as single task",
                success_criteria="Task completed",
            )
        except Exception as e:
            return Plan(
                tasks=[
                    Task(
                        id="task_1",
                        description=f"Handle request: {context.original_query}",
                    )
                ],
                context=f"Error during planning: {str(e)}",
                success_criteria="Task completed despite planning error",
            )
