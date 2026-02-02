"""ConstellationRunner - executes constellation graphs."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

from astro_backend_service.executor.context import ExecutionContext, StarOutput
from astro_backend_service.executor.events import (
    NodeCompletedEvent,
    NodeFailedEvent,
    NodeStartedEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunPausedEvent,
    RunStartedEvent,
    truncate_output,
)
from astro_backend_service.executor.exceptions import (
    ExecutionError,
    ParallelExecutionError,
)
from astro_backend_service.executor.run import NodeOutput, Run
from astro_backend_service.executor.stream import ExecutionStream, NoOpStream

if TYPE_CHECKING:
    from astro_backend_service.foundry import Foundry
    from astro_backend_service.models import (
        BaseStar,
        Constellation,
        EvalDecision,
        StarNode,
    )


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return f"run_{uuid.uuid4().hex[:12]}"


class ConstellationRunner:
    """Executes a Constellation.

    Handles:
    - Traversing the DAG in topological order
    - Executing Stars with proper context
    - Managing parallel execution with retry logic
    - Enforcing loop limits for EvalStar cycles
    - Human-in-the-loop confirmation pause/resume
    """

    def __init__(self, foundry: "Foundry") -> None:
        """Initialize the runner with a Foundry instance.

        Args:
            foundry: The Foundry registry for looking up Stars, Directives, etc.
        """
        from astro_backend_service.foundry import Foundry

        self.foundry: Foundry = foundry
        self._loop_count_lock = asyncio.Lock()

    async def run(
        self,
        constellation_id: str,
        variables: Dict[str, Any],
        original_query: str = "",
        stream: Optional[ExecutionStream] = None,
    ) -> Run:
        """Execute a constellation.

        Args:
            constellation_id: ID of constellation to run.
            variables: Filled template variables.
            original_query: Original user query.
            stream: Optional stream for real-time event emission.

        Returns:
            Run object with status and outputs.

        Raises:
            ValueError: If constellation not found.
        """
        # Use NoOpStream if no stream provided
        effective_stream = stream or NoOpStream()

        constellation = self.foundry.get_constellation(constellation_id)
        if not constellation:
            raise ValueError(f"Constellation '{constellation_id}' not found")

        # Create run record
        run = Run(
            id=generate_run_id(),
            constellation_id=constellation_id,
            constellation_name=constellation.name,
            status="running",
            variables=variables,
            started_at=datetime.now(timezone.utc),
            node_outputs={},
        )

        # Persist run
        await self._save_run(run)

        # Build node name list for UI
        node_names = self._get_node_names(constellation)

        # Emit run started event
        await effective_stream.emit(
            RunStartedEvent(
                run_id=run.id,
                constellation_id=constellation_id,
                constellation_name=constellation.name,
                total_nodes=len(constellation.nodes),
                node_names=node_names,
            )
        )

        # Create execution context with stream
        context = ExecutionContext(
            run_id=run.id,
            constellation_id=constellation_id,
            original_query=original_query,
            constellation_purpose=constellation.description,
            variables=variables,
            foundry=self.foundry,
            stream=effective_stream,
        )

        try:
            # Execute in topological order
            await self._execute_graph(constellation, context, run)

            # Mark complete
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.final_output = self._extract_final_output(run)

            # Calculate duration
            duration_ms = None
            if run.started_at and run.completed_at:
                duration_ms = int(
                    (run.completed_at - run.started_at).total_seconds() * 1000
                )

            # Emit run completed event
            await effective_stream.emit(
                RunCompletedEvent(
                    run_id=run.id,
                    final_output=truncate_output(run.final_output, max_length=500),
                    duration_ms=duration_ms,
                )
            )

        except Exception as e:
            run.status = "failed"
            run.error = str(e)
            run.completed_at = datetime.now(timezone.utc)

            # Emit run failed event
            await effective_stream.emit(
                RunFailedEvent(
                    run_id=run.id,
                    error=str(e),
                    failed_node_id=context.current_node_id,
                )
            )

        await self._save_run(run)
        return run

    def _get_node_names(self, constellation: "Constellation") -> List[str]:
        """Get ordered list of node display names for UI."""
        from astro_backend_service.models import EndNode, StartNode

        names = []
        for node_id in constellation.topological_order():
            node = self._get_node(constellation, node_id)
            if isinstance(node, (StartNode, EndNode)):
                continue

            # Get display name
            display_name = getattr(node, "display_name", None)
            if not display_name:
                star = self.foundry.get_star(node.star_id)
                display_name = star.name if star else node.star_id

            names.append(display_name)

        return names

    async def _execute_graph(
        self,
        constellation: "Constellation",
        context: ExecutionContext,
        run: Run,
    ) -> None:
        """Execute constellation graph in topological order."""
        from astro_backend_service.models import EndNode, StartNode

        execution_order = constellation.topological_order()
        node_index = 0

        for node_id in execution_order:
            node = self._get_node(constellation, node_id)

            if isinstance(node, StartNode):
                # Populate start node context
                node.original_query = context.original_query
                node.constellation_purpose = context.constellation_purpose
                continue

            if isinstance(node, EndNode):
                continue

            # Execute StarNode with index for progress tracking
            node_index += 1
            await self._execute_node(node, constellation, context, run, node_index)

    def _get_node(
        self, constellation: "Constellation", node_id: str
    ) -> Union["StarNode", Any]:
        """Get a node from the constellation by ID."""

        if node_id == constellation.start.id:
            return constellation.start
        if node_id == constellation.end.id:
            return constellation.end
        for node in constellation.nodes:
            if node.id == node_id:
                return node
        raise ValueError(f"Node '{node_id}' not found in constellation")

    async def _execute_node(
        self,
        node: "StarNode",
        constellation: "Constellation",
        context: ExecutionContext,
        run: Run,
        node_index: int = 0,
    ) -> None:
        """Execute a single StarNode."""
        star = self.foundry.get_star(node.star_id)
        if star is None:
            raise ValueError(f"Star '{node.star_id}' not found")

        # Check for upstream parallel nodes
        upstream_nodes = constellation.get_upstream_nodes(node.id)
        if len(upstream_nodes) > 1:
            # Wait for all upstream to complete
            await self._wait_for_upstream(upstream_nodes, run)

        # Get display name for events
        display_name = node.display_name or star.name

        # Set current node in context for stream events
        context.current_node_id = node.id
        context.current_node_name = display_name

        # Build node output record
        node_output = NodeOutput(
            node_id=node.id,
            star_id=node.star_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        run.node_outputs[node.id] = node_output

        # Emit node started event
        if context.stream:
            await context.stream.emit(
                NodeStartedEvent(
                    run_id=run.id,
                    node_id=node.id,
                    node_name=display_name,
                    star_id=node.star_id,
                    star_type=(
                        star.type.value
                        if hasattr(star.type, "value")
                        else str(star.type)
                    ),
                    node_index=node_index,
                    total_nodes=len(constellation.nodes),
                )
            )

        try:
            # Execute star
            result = await self._execute_star(star, node, context)

            # Store output - handle different output types
            if hasattr(result, "formatted_result"):
                # SynthesisOutput
                node_output.output = result.formatted_result
            elif hasattr(result, "result"):
                # WorkerOutput
                node_output.output = result.result
            elif hasattr(result, "worker_outputs"):
                # ExecutionResult - combine worker outputs
                outputs = []
                for wo in result.worker_outputs:
                    if hasattr(wo, "result"):
                        outputs.append(wo.result)
                node_output.output = "\n\n".join(outputs) if outputs else str(result)
            elif hasattr(result, "documents"):
                # DocExResult - combine document extractions
                extractions = []
                for doc in result.documents:
                    if hasattr(doc, "extracted_content"):
                        extractions.append(doc.extracted_content)
                node_output.output = (
                    "\n\n".join(extractions) if extractions else str(result)
                )
            elif hasattr(result, "reasoning"):
                # EvalDecision
                node_output.output = f"Decision: {result.decision}. {result.reasoning}"
            elif hasattr(result, "tasks"):
                # Plan
                task_descs = [t.description for t in result.tasks]
                node_output.output = (
                    f"Plan with {len(result.tasks)} tasks: " + "; ".join(task_descs[:3])
                )
            else:
                node_output.output = str(result)

            node_output.status = "completed"
            node_output.completed_at = datetime.now(timezone.utc)
            context.node_outputs[node.id] = result

            # Calculate duration
            duration_ms = 0
            if node_output.started_at and node_output.completed_at:
                duration_ms = int(
                    (node_output.completed_at - node_output.started_at).total_seconds()
                    * 1000
                )

            # Emit node completed event
            if context.stream:
                await context.stream.emit(
                    NodeCompletedEvent(
                        run_id=run.id,
                        node_id=node.id,
                        node_name=display_name,
                        output_preview=truncate_output(node_output.output),
                        duration_ms=duration_ms,
                    )
                )

            # Handle EvalStar routing
            from astro_backend_service.models import EvalDecision, EvalStar

            if isinstance(star, EvalStar) and isinstance(result, EvalDecision):
                await self._handle_eval_decision(result, constellation, context, run)

            # Handle human-in-the-loop
            if node.requires_confirmation:
                await self._pause_for_confirmation(node, run, context)

        except Exception as e:
            node_output.status = "failed"
            node_output.error = str(e)
            node_output.completed_at = datetime.now(timezone.utc)

            # Calculate duration
            duration_ms = 0
            if node_output.started_at and node_output.completed_at:
                duration_ms = int(
                    (node_output.completed_at - node_output.started_at).total_seconds()
                    * 1000
                )

            # Emit node failed event
            if context.stream:
                await context.stream.emit(
                    NodeFailedEvent(
                        run_id=run.id,
                        node_id=node.id,
                        node_name=display_name,
                        error=str(e),
                        duration_ms=duration_ms,
                    )
                )
            raise
        finally:
            # Clear current node from context
            context.current_node_id = None
            context.current_node_name = None

        await self._save_run(run)

    async def _execute_star(
        self,
        star: "BaseStar",
        node: "StarNode",
        context: ExecutionContext,
    ) -> StarOutput:
        """Execute a star with proper context."""

        # Resolve variable bindings
        bindings = self._resolve_bindings(node, context)

        # Update context with bindings
        context.variables.update(bindings)

        # Execute the star
        if hasattr(star, "execute"):
            execute_fn = getattr(star, "execute")
            return await execute_fn(context)

        # Fallback for stars without execute method
        return {"status": "executed", "star_id": star.id}

    def _resolve_bindings(
        self,
        node: "StarNode",
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Resolve variable bindings from context."""
        star = self.foundry.get_star(node.star_id)
        if star is None:
            return {}

        directive = self.foundry.get_directive(star.directive_id)
        if directive is None:
            return {}

        bindings: Dict[str, Any] = {}
        for var in directive.template_variables:
            if var.name in context.variables:
                bindings[var.name] = context.variables[var.name]
            elif var.default is not None:
                bindings[var.name] = var.default
            elif var.required:
                raise ValueError(f"Required variable '{var.name}' not provided")
        return bindings

    async def _wait_for_upstream(
        self, upstream_nodes: List["StarNode"], run: Run
    ) -> None:
        """Wait for all upstream nodes to complete."""
        for node in upstream_nodes:
            if node.id in run.node_outputs:
                node_output = run.node_outputs[node.id]
                if node_output.status == "failed":
                    raise ExecutionError(
                        f"Upstream node '{node.id}' failed: {node_output.error}"
                    )

    async def _handle_eval_decision(
        self,
        decision: "EvalDecision",
        constellation: "Constellation",
        context: ExecutionContext,
        run: Run,
    ) -> None:
        """Handle EvalStar routing decision."""
        from astro_backend_service.models import StarType

        if decision.decision == "loop":
            # Check loop limit - use lock to prevent race condition
            async with self._loop_count_lock:
                context.loop_count += 1
                loop_exceeded = context.loop_count >= constellation.max_loop_iterations
            if loop_exceeded:
                # Force continue
                object.__setattr__(decision, "decision", "continue")
                decision.reasoning += (
                    f" (forced continue: max {constellation.max_loop_iterations} "
                    "loops reached)"
                )
            else:
                # Loop back to planning star
                planning_node = self._find_node_by_star_type(
                    constellation, StarType.PLANNING
                )
                if planning_node:
                    # Clear downstream outputs
                    self._clear_downstream_outputs(
                        planning_node.id, constellation, context
                    )
                    # Re-execute from planning star
                    await self._execute_from_node(
                        planning_node.id, constellation, context, run
                    )

    def _find_node_by_star_type(
        self, constellation: "Constellation", star_type: Any
    ) -> Optional["StarNode"]:
        """Find a node by its star type."""
        for node in constellation.nodes:
            star = self.foundry.get_star(node.star_id)
            if star and star.type == star_type:
                return node
        return None

    def _clear_downstream_outputs(
        self,
        node_id: str,
        constellation: "Constellation",
        context: ExecutionContext,
        visited: Optional[Set[str]] = None,
    ) -> None:
        """Clear outputs of all nodes downstream from given node."""
        if visited is None:
            visited = set()

        if node_id in visited:
            return  # Prevent infinite recursion on cycles

        visited.add(node_id)

        downstream = constellation.get_downstream_nodes(node_id)
        for node in downstream:
            if node.id in context.node_outputs:
                del context.node_outputs[node.id]
            # Recursively clear further downstream
            self._clear_downstream_outputs(node.id, constellation, context, visited)

    async def _execute_from_node(
        self,
        node_id: str,
        constellation: "Constellation",
        context: ExecutionContext,
        run: Run,
    ) -> None:
        """Execute graph starting from a specific node."""
        from astro_backend_service.models import EndNode, StartNode

        execution_order = constellation.topological_order()

        # Find starting index
        try:
            start_idx = execution_order.index(node_id)
        except ValueError:
            return

        # Calculate node index (1-based, excluding start/end)
        node_index = 0
        for i in range(start_idx):
            node = self._get_node(constellation, execution_order[i])
            if not isinstance(node, (StartNode, EndNode)):
                node_index += 1

        # Execute from that point
        for i in range(start_idx, len(execution_order)):
            current_id = execution_order[i]
            node = self._get_node(constellation, current_id)

            # Skip start/end nodes
            if isinstance(node, (StartNode, EndNode)):
                continue

            node_index += 1
            await self._execute_node(node, constellation, context, run, node_index)

    async def _pause_for_confirmation(
        self,
        node: "StarNode",
        run: Run,
        context: ExecutionContext,
    ) -> None:
        """Pause execution for user confirmation."""
        run.status = "awaiting_confirmation"
        run.awaiting_node_id = node.id
        run.awaiting_prompt = node.confirmation_prompt or "Review the output. Proceed?"

        # Get display name
        star = self.foundry.get_star(node.star_id)
        display_name = node.display_name or (star.name if star else node.id)

        # Emit paused event
        if context.stream:
            await context.stream.emit(
                RunPausedEvent(
                    run_id=run.id,
                    node_id=node.id,
                    node_name=display_name,
                    prompt=run.awaiting_prompt,
                )
            )

        await self._save_run(run)
        # Execution pauses here - resumed via resume_run()

    async def resume_run(
        self,
        run_id: str,
        additional_context: Optional[str] = None,
        stream: Optional[ExecutionStream] = None,
    ) -> Run:
        """Resume a paused run.

        Args:
            run_id: ID of the run to resume.
            additional_context: Optional additional context to inject.
            stream: Optional stream for real-time event emission.

        Returns:
            Updated Run object.

        Raises:
            ValueError: If run is not awaiting confirmation.
        """
        effective_stream = stream or NoOpStream()
        run = await self._get_run(run_id)

        if run.status != "awaiting_confirmation":
            raise ValueError(f"Run is not awaiting confirmation (status: {run.status})")

        # Clear confirmation state
        awaiting_node_id = run.awaiting_node_id
        run.status = "running"
        run.awaiting_node_id = None
        run.awaiting_prompt = None

        # Inject additional context if provided
        if additional_context:
            run.additional_context = additional_context

        await self._save_run(run)

        # Recreate context and continue execution
        constellation = self.foundry.get_constellation(run.constellation_id)
        if constellation is None:
            raise ValueError(f"Constellation '{run.constellation_id}' not found")

        context = ExecutionContext(
            run_id=run.id,
            constellation_id=run.constellation_id,
            original_query="",  # Would need to restore from run
            constellation_purpose=constellation.description,
            variables=run.variables,
            foundry=self.foundry,
            stream=effective_stream,
        )

        # Restore node outputs
        for node_id, node_output in run.node_outputs.items():
            if node_output.output:
                context.node_outputs[node_id] = node_output.output

        # Continue from the node after the paused one
        if awaiting_node_id:
            downstream = constellation.get_downstream_nodes(awaiting_node_id)
            # Calculate node index for resumed execution
            execution_order = constellation.topological_order()
            try:
                base_idx = execution_order.index(awaiting_node_id)
                node_index = base_idx  # Approximate - count star nodes before this
            except ValueError:
                node_index = len(run.node_outputs)

            for node in downstream:
                node_index += 1
                await self._execute_node(node, constellation, context, run, node_index)

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.final_output = self._extract_final_output(run)

        # Calculate duration
        duration_ms = None
        if run.started_at and run.completed_at:
            duration_ms = int(
                (run.completed_at - run.started_at).total_seconds() * 1000
            )

        # Emit completed event
        await effective_stream.emit(
            RunCompletedEvent(
                run_id=run.id,
                final_output=truncate_output(run.final_output, max_length=500),
                duration_ms=duration_ms,
            )
        )

        await self._save_run(run)

        return run

    async def cancel_run(self, run_id: str) -> Run:
        """Cancel a running or paused run.

        Args:
            run_id: ID of the run to cancel.

        Returns:
            Updated Run object with cancelled status.
        """
        run = await self._get_run(run_id)

        if run.status in ("completed", "failed", "cancelled"):
            return run

        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc)
        run.awaiting_node_id = None
        run.awaiting_prompt = None

        await self._save_run(run)
        return run

    def _extract_final_output(self, run: Run) -> Optional[str]:
        """Extract final output from the last completed node."""
        # Find the last node in execution order that has output
        if not run.node_outputs:
            return None

        last_output = None
        for node_output in run.node_outputs.values():
            if node_output.status == "completed" and node_output.output:
                last_output = node_output.output

        return last_output

    async def _save_run(self, run: Run) -> None:
        """Persist run to database via Foundry."""
        run_data = run.model_dump()
        # Convert datetime to ISO strings for MongoDB
        if run_data.get("started_at"):
            run_data["started_at"] = run_data["started_at"].isoformat()
        if run_data.get("completed_at"):
            run_data["completed_at"] = run_data["completed_at"].isoformat()
        # Serialize node_outputs
        for node_id, node_output in run_data.get("node_outputs", {}).items():
            if node_output.get("started_at"):
                node_output["started_at"] = node_output["started_at"].isoformat()
            if node_output.get("completed_at"):
                node_output["completed_at"] = node_output["completed_at"].isoformat()

        # Check if run exists and update or create
        existing = await self.foundry.get_run(run.id)
        if existing:
            await self.foundry.update_run(run.id, run_data)
        else:
            await self.foundry.create_run(run_data)

    async def _get_run(self, run_id: str) -> Run:
        """Load run from database via Foundry."""
        from datetime import datetime

        from astro_backend_service.executor.exceptions import RunNotFoundError

        doc = await self.foundry.get_run(run_id)
        if doc:
            # Parse ISO datetime strings back to datetime objects
            if doc.get("started_at") and isinstance(doc["started_at"], str):
                doc["started_at"] = datetime.fromisoformat(doc["started_at"])
            if doc.get("completed_at") and isinstance(doc["completed_at"], str):
                doc["completed_at"] = datetime.fromisoformat(doc["completed_at"])
            # Parse node_outputs
            for node_output in doc.get("node_outputs", {}).values():
                if node_output.get("started_at") and isinstance(
                    node_output["started_at"], str
                ):
                    node_output["started_at"] = datetime.fromisoformat(
                        node_output["started_at"]
                    )
                if node_output.get("completed_at") and isinstance(
                    node_output["completed_at"], str
                ):
                    node_output["completed_at"] = datetime.fromisoformat(
                        node_output["completed_at"]
                    )
            return Run(**doc)

        raise RunNotFoundError(f"Run '{run_id}' not found")

    # Parallel execution methods
    async def _execute_parallel_nodes(
        self,
        nodes: List["StarNode"],
        constellation: "Constellation",
        context: ExecutionContext,
        run: Run,
    ) -> List[StarOutput]:
        """Execute nodes in parallel with retry logic."""
        tasks = []
        for node in nodes:
            task = self._execute_with_retry(
                node,
                constellation,
                context,
                run,
                max_attempts=constellation.max_retry_attempts,
                delay_base=constellation.retry_delay_base,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle failures
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            raise ParallelExecutionError(f"{len(errors)} nodes failed", errors)

        return [r for r in results if not isinstance(r, Exception)]

    async def _execute_with_retry(
        self,
        node: "StarNode",
        constellation: "Constellation",
        context: ExecutionContext,
        run: Run,
        max_attempts: int,
        delay_base: float,
        node_index: int = 0,
    ) -> StarOutput:
        """Execute node with exponential backoff retry."""
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts + 1):
            try:
                await self._execute_node(node, constellation, context, run, node_index)
                # Get the result from context
                return context.node_outputs.get(node.id, {})
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    delay = delay_base * (2**attempt)
                    await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise ExecutionError(
            f"Node '{node.id}' failed after {max_attempts + 1} attempts"
        )
