"""ConstellationRunner - executes constellation graphs."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional, Union

from astro.orchestration.context import ConstellationContext, StarOutput

logger = logging.getLogger(__name__)
from astro.core.runtime.events import (
    NodeCompletedEvent,
    NodeFailedEvent,
    NodeStartedEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunPausedEvent,
    RunResumedEvent,
    RunStartedEvent,
    truncate_output,
)
from astro.core.runtime.exceptions import (
    ExecutionError,
    ExecutionPausedException,
    ParallelExecutionError,
)
from astro.core.runtime.stream import ExecutionStream, NoOpStream
from astro.orchestration.runner.run import NodeOutput, Run

if TYPE_CHECKING:
    from astro.core.registry.registry import Registry as Foundry
    from astro.orchestration.models import (  # type: ignore[attr-defined]
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
        """Initialize the runner with a Registry instance.

        Args:
            foundry: The Registry for looking up Stars, Directives, etc.
                   (kept as 'foundry' param for backwards compatibility)
        """
        from astro.core.registry import Registry

        self.foundry: Registry = foundry
        self._loop_count_lock = asyncio.Lock()
        self._node_save_counter = 0

    async def run(
        self,
        constellation_id: str,
        variables: dict[str, Any],
        original_query: str = "",
        stream: ExecutionStream | None = None,
        run_id: str | None = None,
    ) -> Run:
        """Execute a constellation.

        Args:
            constellation_id: ID of constellation to run.
            variables: Filled template variables.
            original_query: Original user query.
            stream: Optional stream for real-time event emission.
            run_id: Optional pre-generated run ID (if None, generates a new one).

        Returns:
            Run object with status and outputs.

        Raises:
            ValueError: If constellation not found.
        """
        # Use NoOpStream if no stream provided
        effective_stream = stream or NoOpStream()

        logger.info(f"Starting constellation run: constellation_id={constellation_id}")
        logger.debug(f"Run variables: {list(variables.keys())}")

        constellation = self.foundry.get_constellation(constellation_id)  # type: ignore[attr-defined]
        if not constellation:
            logger.error(f"Constellation not found: {constellation_id}")
            raise ValueError(f"Constellation '{constellation_id}' not found")

        # Store original_query in variables for persistence (needed for resume)
        variables_with_query = {**variables, "_original_query": original_query}

        # Create run record
        run = Run(
            id=run_id or generate_run_id(),
            constellation_id=constellation_id,
            constellation_name=constellation.name,
            status="running",
            variables=variables_with_query,
            started_at=datetime.now(UTC),
            node_outputs={},
        )

        logger.info(f"Created run: id={run.id}, constellation={constellation.name}")

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
        context = ConstellationContext(
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
            logger.debug(f"Executing graph for run: {run.id}")
            await self._execute_graph(constellation, context, run)

            # Mark complete
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.final_output = self._extract_final_output(run)

            # Calculate duration
            duration_ms = None
            if run.started_at and run.completed_at:
                duration_ms = int(
                    (run.completed_at - run.started_at).total_seconds() * 1000
                )

            logger.info(f"Run completed: id={run.id}, duration_ms={duration_ms}")

            # Emit run completed event
            await effective_stream.emit(
                RunCompletedEvent(
                    run_id=run.id,
                    final_output=truncate_output(run.final_output, max_length=500),
                    duration_ms=duration_ms,
                )
            )

        except ExecutionPausedException as e:
            # HITL pause - not an error, just halt execution gracefully
            logger.info(f"Run paused for confirmation: id={run.id}, node={e.node_id}")
            # Run is already saved with awaiting_confirmation status in _pause_for_confirmation()
            # Just return without marking as failed

        except Exception as e:
            run.status = "failed"
            run.error = str(e)
            run.completed_at = datetime.now(UTC)

            logger.error(
                f"Run failed: id={run.id}, node={context.current_node_id}, error={e}",
                exc_info=True,
            )

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

    def _get_node_names(self, constellation: "Constellation") -> list[str]:
        """Get ordered list of node display names for UI."""
        from astro.orchestration.models import EndNode, StartNode

        names = []
        for node_id in constellation.topological_order():
            node = self._get_node(constellation, node_id)
            if isinstance(node, (StartNode, EndNode)):
                continue

            # Get display name
            display_name = getattr(node, "display_name", None)
            if not display_name:
                star = self.foundry.get_star(node.star_id)  # type: ignore[attr-defined]  # type: ignore[attr-defined]  # type: ignore[attr-defined]
                display_name = star.name if star else node.star_id

            names.append(display_name)

        return names

    async def _execute_graph(
        self,
        constellation: "Constellation",
        context: ConstellationContext,
        run: Run,
    ) -> None:
        """Execute constellation graph in topological order."""
        from astro.orchestration.models import EndNode, StartNode

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
        context: ConstellationContext,
        run: Run,
        node_index: int = 0,
    ) -> None:
        """Execute a single StarNode."""
        logger.debug(
            f"Executing node: id={node.id}, star_id={node.star_id}, index={node_index}"
        )
        star = self.foundry.get_star(node.star_id)  # type: ignore[attr-defined]
        if star is None:
            logger.error(f"Star not found: {node.star_id}")
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
            started_at=datetime.now(UTC),
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
            logger.debug(f"Executing star: id={star.id}, type={star.type}")
            result = await self._execute_star(star, node, context)
            logger.debug(f"Star execution complete: id={star.id}")

            # Store output - handle different output types
            if hasattr(result, "formatted_result"):
                # SynthesisOutput
                node_output.output = result.formatted_result
            elif hasattr(result, "result"):
                # WorkerOutput
                node_output.output = result.result
                # Transfer tool calls if present
                if hasattr(result, "tool_calls") and result.tool_calls:
                    from astro.orchestration.runner.run import ToolCallRecord

                    node_output.tool_calls = [
                        ToolCallRecord(
                            tool_name=tc.tool_name,
                            arguments=tc.arguments,
                            result=(
                                tc.result[:500] + "... [truncated]"
                                if tc.result and len(tc.result) > 500
                                else tc.result
                            ),
                            error=tc.error,
                        )
                        for tc in result.tool_calls
                    ]
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

            # NOTE: We do NOT truncate the main output here. Fix 2.4 only truncates
            # tool_calls metadata (line 335) to reduce storage overhead, but the
            # main output should be preserved for synthesis and final results.
            # Truncating here broke benchmarks and synthesis quality.

            node_output.status = "completed"
            node_output.completed_at = datetime.now(UTC)
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
            from astro.orchestration.models import (  # type: ignore[attr-defined]
                EvalDecision,
                EvalStar,
            )

            if isinstance(star, EvalStar) and isinstance(result, EvalDecision):
                await self._handle_eval_decision(
                    result, constellation, context, run, node.id
                )

            # Handle human-in-the-loop
            if node.requires_confirmation:
                await self._pause_for_confirmation(node, run, context)

        except ExecutionPausedException:
            # HITL pause - not a failure, re-raise to halt execution
            raise

        except Exception as e:
            logger.error(
                f"Node execution failed: node_id={node.id}, star_id={node.star_id}, error={e}",
                exc_info=True,
            )
            node_output.status = "failed"
            node_output.error = str(e)
            node_output.completed_at = datetime.now(UTC)

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

        # Save at checkpoints: every 3rd node, on failures, or HITL pause
        self._node_save_counter += 1
        if self._node_save_counter % 3 == 0 or node_output.status == "failed":
            await self._save_run(run)

    async def _execute_star(
        self,
        star: "BaseStar",
        node: "StarNode",
        context: ConstellationContext,
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
        context: ConstellationContext,
    ) -> dict[str, Any]:
        """Resolve variable bindings from context.

        Resolution order:
        1. Explicit variables in context.variables
        2. Upstream node outputs (by variable name matching node_id pattern)
        3. Upstream node outputs (by execution order for common variable names)
        4. Default values
        """
        star = self.foundry.get_star(node.star_id)  # type: ignore[attr-defined]
        if star is None:
            return {}

        directive = self.foundry.get_directive(star.directive_id)
        if directive is None:
            return {}

        bindings: dict[str, Any] = {}
        for var in directive.template_variables:
            # 1. Check explicit variables first
            if var.name in context.variables:
                bindings[var.name] = context.variables[var.name]
                continue

            # 2. Check node_outputs - try to find matching output
            found_in_outputs = False

            # 2a. Check for direct node_id match (e.g., variable "node_excel_parser")
            if var.name in context.node_outputs:
                output = context.node_outputs[var.name]
                bindings[var.name] = self._extract_output_value(output)
                found_in_outputs = True
                continue

            # 2b. Check for semantic match based on variable name patterns
            # Map common variable names to likely upstream outputs
            var_to_node_patterns = {
                "structure_analysis": ["excel_parser", "parser"],
                "detected_patterns": ["dependency_mapper", "pattern_detector"],
                "dependency_map": ["dependency_mapper"],
                "interview_results": ["expert_interview", "interviewer"],
                "interview_transcript": ["expert_interview", "interviewer"],
                # Progress extractor outputs structured metrics for the eval
                "interview_state": [
                    "progress_extractor",
                    "expert_interview",
                    "interviewer",
                ],
                "blueprint_progress": [
                    "progress_extractor",
                    "expert_interview",
                    "blueprint_compiler",
                ],
                "verification_results": ["reconstructor", "verifier"],
                "validated_input": ["input_validator", "validator"],
                "model_blueprint": ["blueprint_compiler"],
            }

            if var.name in var_to_node_patterns:
                for pattern in var_to_node_patterns[var.name]:
                    for node_id, output in context.node_outputs.items():
                        if pattern in node_id.lower():
                            bindings[var.name] = self._extract_output_value(output)
                            found_in_outputs = True
                            break
                    if found_in_outputs:
                        break

            if found_in_outputs:
                continue

            # 2c. Fallback: use the most recent upstream output for generic variable names
            if not found_in_outputs and context.node_outputs:
                # Get the last completed node's output
                last_output = (
                    list(context.node_outputs.values())[-1]
                    if context.node_outputs
                    else None
                )
                if last_output is not None:
                    bindings[var.name] = self._extract_output_value(last_output)
                    found_in_outputs = True
                    continue

            # 3. Use default if available
            if var.default is not None:
                bindings[var.name] = var.default
            elif var.required:
                raise ValueError(f"Required variable '{var.name}' not provided")

        return bindings

    def _extract_output_value(self, output: Any) -> Any:
        """Extract the actual value from a node output object."""
        if output is None:
            return None
        # Handle different output types
        if hasattr(output, "result"):
            return output.result
        if hasattr(output, "formatted_result"):
            return output.formatted_result
        if hasattr(output, "output"):
            return output.output
        # Return as-is if it's already a simple value
        return output

    async def _wait_for_upstream(
        self, upstream_nodes: list["StarNode"], run: Run
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
        context: ConstellationContext,
        run: Run,
        current_node_id: str,
    ) -> None:
        """Handle EvalStar routing decision."""
        from astro.orchestration.models import StarType

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
                # Find the loop target from edges with 'loop' condition
                loop_target_id = self._find_loop_target(constellation, current_node_id)

                if loop_target_id:
                    logger.info(f"EvalStar loop: returning to {loop_target_id}")
                    # Clear downstream outputs
                    self._clear_downstream_outputs(
                        loop_target_id, constellation, context
                    )
                    # Re-execute from loop target
                    await self._execute_from_node(
                        loop_target_id, constellation, context, run
                    )
                else:
                    # Fallback: try to find a PLANNING star
                    planning_node = self._find_node_by_star_type(
                        constellation, StarType.PLANNING
                    )
                    if planning_node:
                        logger.info(
                            f"EvalStar loop: falling back to planning node {planning_node.id}"
                        )
                        self._clear_downstream_outputs(
                            planning_node.id, constellation, context
                        )
                        await self._execute_from_node(
                            planning_node.id, constellation, context, run
                        )
                    else:
                        logger.warning(
                            "EvalStar loop decision but no loop target found, continuing..."
                        )

    def _find_loop_target(
        self, constellation: "Constellation", eval_node_id: str
    ) -> str | None:
        """Find the loop target node ID from edges with 'loop' in condition."""
        for edge in constellation.edges:
            if edge.source == eval_node_id and edge.condition:
                if "loop" in edge.condition.lower():
                    return edge.target
        return None

    def _find_node_by_star_type(
        self, constellation: "Constellation", star_type: Any
    ) -> Optional["StarNode"]:
        """Find a node by its star type."""
        for node in constellation.nodes:
            star = self.foundry.get_star(node.star_id)  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            if star and star.type == star_type:
                return node
        return None

    def _clear_downstream_outputs(
        self,
        node_id: str,
        constellation: "Constellation",
        context: ConstellationContext,
        visited: set[str] | None = None,
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
        context: ConstellationContext,
        run: Run,
    ) -> None:
        """Execute graph starting from a specific node."""
        from astro.orchestration.models import EndNode, StartNode

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
        context: ConstellationContext,
    ) -> None:
        """Pause execution for user confirmation."""
        run.status = "awaiting_confirmation"
        run.awaiting_node_id = node.id
        run.awaiting_prompt = node.confirmation_prompt or "Review the output. Proceed?"

        # Get display name
        star = self.foundry.get_star(node.star_id)  # type: ignore[attr-defined]
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

        # Raise exception to halt execution loop - resumed via resume_run()
        raise ExecutionPausedException(run.id, node.id)

    async def resume_run(
        self,
        run_id: str,
        additional_context: str | None = None,
        stream: ExecutionStream | None = None,
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
        logger.info(f"Resuming run: {run_id}")
        effective_stream = stream or NoOpStream()
        run = await self._get_run(run_id)

        if run.status != "awaiting_confirmation":
            logger.warning(f"Cannot resume run {run_id}: status={run.status}")
            raise ValueError(f"Run is not awaiting confirmation (status: {run.status})")

        # Clear confirmation state
        awaiting_node_id = run.awaiting_node_id
        run.status = "running"
        run.awaiting_node_id = None
        run.awaiting_prompt = None

        # Inject additional context if provided
        if additional_context:
            run.additional_context = additional_context
            # Also append to the awaiting node's output so downstream nodes see full context
            if awaiting_node_id and awaiting_node_id in run.node_outputs:
                node_output = run.node_outputs[awaiting_node_id]
                if node_output.output:
                    node_output.output = (
                        f"{node_output.output}\n\n"
                        f"--- Expert Response ---\n{additional_context}"
                    )
                else:
                    node_output.output = (
                        f"--- Expert Response ---\n{additional_context}"
                    )

        await self._save_run(run)

        # Recreate context and continue execution
        constellation = self.foundry.get_constellation(run.constellation_id)  # type: ignore[attr-defined]
        if constellation is None:
            raise ValueError(f"Constellation '{run.constellation_id}' not found")

        # Restore original_query from persisted variables
        original_query = run.variables.get("_original_query", "")

        context = ConstellationContext(
            run_id=run.id,
            constellation_id=run.constellation_id,
            original_query=original_query,
            constellation_purpose=constellation.description,
            variables=run.variables,
            foundry=self.foundry,
            stream=effective_stream,
        )

        # Restore node outputs
        for node_id, node_output in run.node_outputs.items():
            if node_output.output:
                context.node_outputs[node_id] = node_output.output

        # Emit resumed event
        await effective_stream.emit(
            RunResumedEvent(
                run_id=run.id,
                resumed_from_node=awaiting_node_id or "",
                additional_context=additional_context,
            )
        )

        # Continue from the node after the paused one
        # Execute all remaining nodes in topological order (not just immediate downstream)
        try:
            if awaiting_node_id:
                execution_order = constellation.topological_order()
                try:
                    base_idx = execution_order.index(awaiting_node_id)
                except ValueError:
                    base_idx = 0

                # Get all nodes after the paused node in topological order
                remaining_node_ids = execution_order[base_idx + 1 :]
                node_index = base_idx

                from astro.orchestration.models import EndNode, StartNode

                for node_id in remaining_node_ids:
                    node = self._get_node(constellation, node_id)
                    if isinstance(node, (StartNode, EndNode)):
                        continue
                    node_index += 1
                    await self._execute_node(
                        node, constellation, context, run, node_index
                    )

            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.final_output = self._extract_final_output(run)

        except ExecutionPausedException as e:
            # Another HITL pause encountered - gracefully halt
            logger.info(
                f"Run paused again for confirmation: id={run.id}, node={e.node_id}"
            )
            return run

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
        logger.info(f"Cancelling run: {run_id}")
        run = await self._get_run(run_id)

        if run.status in ("completed", "failed", "cancelled"):
            logger.debug(f"Run {run_id} already in terminal state: {run.status}")
            return run

        run.status = "cancelled"
        run.completed_at = datetime.now(UTC)
        run.awaiting_node_id = None
        run.awaiting_prompt = None

        logger.info(f"Run cancelled: {run_id}")
        await self._save_run(run)
        return run

    def _extract_final_output(self, run: Run) -> str | None:
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
        """Persist run to database via Foundry using upsert."""
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

        await self.foundry.upsert_run(run_data)  # type: ignore[attr-defined]

    async def _get_run(self, run_id: str) -> Run:
        """Load run from database via Registry."""
        from datetime import datetime

        from astro.core.runtime.exceptions import RunNotFoundError

        doc = await self.foundry.get_run(run_id)  # type: ignore[attr-defined]
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
        nodes: list["StarNode"],
        constellation: "Constellation",
        context: ConstellationContext,
        run: Run,
    ) -> list[StarOutput]:
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
        context: ConstellationContext,
        run: Run,
        max_attempts: int,
        delay_base: float,
        node_index: int = 0,
    ) -> StarOutput:
        """Execute node with exponential backoff retry."""
        last_error: Exception | None = None

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
