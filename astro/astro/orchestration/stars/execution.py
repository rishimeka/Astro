"""ExecutionStar - consumes plans and spawns workers."""

import asyncio
from typing import TYPE_CHECKING, List

from pydantic import Field

from astro.orchestration.models.star_types import StarType
from astro.orchestration.stars.base import OrchestratorStar

if TYPE_CHECKING:
    from astro.orchestration.context import ConstellationContext
    from astro.core.models.outputs import ExecutionResult


class ExecutionStar(OrchestratorStar):
    """
    Consumes Plan from PlanningStar, spawns N workers.
    Parallel or sequential execution based on config.
    """

    type: StarType = Field(default=StarType.EXECUTION, frozen=True)

    # Execution configuration
    parallel: bool = Field(
        default=True, description="Execute workers in parallel if True"
    )

    def validate_star(self) -> List[str]:
        """Validate ExecutionStar configuration."""
        errors = super().validate_star()
        # Must have PlanningStar upstream - validated at Constellation level
        return errors

    async def execute(self, context: "ConstellationContext") -> "ExecutionResult":
        """Execute tasks from an upstream Plan.

        Args:
            context: Execution context with Plan from PlanningStar.

        Returns:
            ExecutionResult with worker outputs.
        """
        from astro.core.models.outputs import (
            ExecutionResult,
            Plan,
            WorkerOutput,
        )

        # Get the plan from upstream
        plan = context.get_upstream_output(Plan)

        if not plan or not plan.tasks:
            return ExecutionResult(
                worker_outputs=[],
                status="completed",
                errors=["No plan or tasks found"],
            )

        worker_outputs: List[WorkerOutput] = []
        errors: List[str] = []

        async def execute_task(task) -> WorkerOutput:
            """Execute a single task with a worker."""
            try:
                # Find or create a worker for this task
                star = context.find_star_for_task(task)

                if star is None:
                    # Create dynamic worker
                    star = await context.create_dynamic_star(task)

                # Create a lightweight sub-context sharing node_outputs and
                # tool_result_cache by reference (read-only from workers)
                from astro.orchestration.context import ConstellationContext

                task_context = ConstellationContext(
                    run_id=context.run_id,
                    constellation_id=context.constellation_id,
                    original_query=context.original_query,
                    constellation_purpose=context.constellation_purpose,
                    variables={
                        **context.variables,
                        "task_description": task.description,
                        "task_context": plan.context,
                    },
                    node_outputs=context.node_outputs,
                    tool_result_cache=context.tool_result_cache,
                    loop_count=context.loop_count,
                    foundry=context.foundry,
                    stream=context.stream,
                    current_node_id=context.current_node_id,
                    current_node_name=context.current_node_name,
                )

                # Execute the worker
                if hasattr(star, "execute"):
                    result = await star.execute(task_context)
                    if isinstance(result, WorkerOutput):
                        return result
                    # Wrap non-WorkerOutput in WorkerOutput
                    return WorkerOutput(
                        result=str(
                            result.formatted_result
                            if hasattr(result, "formatted_result")
                            else result
                        ),
                        status="completed",
                    )
                else:
                    return WorkerOutput(
                        result=f"Task '{task.id}' completed (no execute method)",
                        status="completed",
                    )

            except Exception as e:
                return WorkerOutput(
                    result=f"Error executing task '{task.id}': {str(e)}",
                    status="failed",
                )

        # Group tasks by dependencies for execution order
        # For simplicity, execute all without dependencies first, then the rest
        independent_tasks = [t for t in plan.tasks if not t.dependencies]
        dependent_tasks = [t for t in plan.tasks if t.dependencies]

        if self.parallel:
            # Execute independent tasks in parallel
            if independent_tasks:
                results = await asyncio.gather(
                    *[execute_task(t) for t in independent_tasks],
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, BaseException):
                        errors.append(str(r))
                        worker_outputs.append(
                            WorkerOutput(
                                result=f"Error: {str(r)}",
                                status="failed",
                            )
                        )
                    elif isinstance(r, WorkerOutput):
                        worker_outputs.append(r)

            # Execute dependent tasks (simplified - could be more sophisticated)
            if dependent_tasks:
                results = await asyncio.gather(
                    *[execute_task(t) for t in dependent_tasks], return_exceptions=True
                )
                for r in results:
                    if isinstance(r, BaseException):
                        errors.append(str(r))
                        worker_outputs.append(
                            WorkerOutput(
                                result=f"Error: {str(r)}",
                                status="failed",
                            )
                        )
                    elif isinstance(r, WorkerOutput):
                        worker_outputs.append(r)
        else:
            # Sequential execution
            for task in plan.tasks:
                result = await execute_task(task)
                worker_outputs.append(result)
                if result.status == "failed":
                    errors.append(f"Task {task.id} failed")

        # Determine overall status
        failed_count = sum(1 for wo in worker_outputs if wo.status == "failed")
        if failed_count == len(worker_outputs):
            status = "failed"
        elif failed_count > 0:
            status = "partial"
        else:
            status = "completed"

        return ExecutionResult(
            worker_outputs=worker_outputs,
            status=status,
            errors=errors,
        )
