"""Orchestrator for coordinating the execution engine.

This module implements the main Plan -> Execute -> Evaluate -> Synthesize
loop for running AI workflows.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from execution.models.input import ExecutionInput, ExecutionConfig, ExecutionMode
from execution.models.state import (
    ExecutionState,
    ExecutionStatus,
    ExecutionPlan,
    PhaseState,
    PhaseStatus,
    WorkerState,
)
from execution.star_foundry import ExecutionStarFoundry
from execution.probe_executor import ExecutionProbeExecutor
from execution.worker_runtime import WorkerRuntime
from execution.phase_executor import PhaseExecutor
from execution.sidekick import SidekickClient

logger = logging.getLogger(__name__)


# System prompts for planning and synthesis
PLANNER_SYSTEM_PROMPT = """You are a planning agent for an AI execution system. Your job is to create execution plans that break down complex queries into phases and workers.

Each phase runs sequentially, but workers within a phase run in parallel.

When creating a plan:
1. Break the query into logical phases
2. Identify what workers are needed in each phase
3. Specify which Star (prompt template) each worker should use
4. Provide clear task descriptions for each worker

Return your plan as valid JSON."""

SYNTHESIZER_SYSTEM_PROMPT = """You are a synthesis agent. Your job is to combine outputs from multiple research phases into a coherent, well-structured final response.

When synthesizing:
1. Integrate all relevant findings
2. Maintain logical flow and organization
3. Acknowledge any limitations or uncertainties
4. Provide a clear, actionable response"""

EVALUATOR_SYSTEM_PROMPT = """You are an evaluation agent. Your job is to assess whether research outputs adequately address the original query.

Evaluate completeness on a scale of 0-1 and identify any gaps that need additional research.

Return your evaluation as valid JSON with these fields:
- completeness_score: float between 0 and 1
- is_complete: boolean (true if score >= 0.7)
- missing_aspects: list of strings describing gaps
- recommendation: "continue", "conclude", or "escalate"
- justification: string explaining your assessment"""


class Orchestrator:
    """Main execution coordinator.

    Implements the Plan -> Execute -> Evaluate -> Synthesize loop.
    """

    def __init__(
        self,
        star_foundry: ExecutionStarFoundry,
        probe_executor: ExecutionProbeExecutor,
        config: Optional[ExecutionConfig] = None,
    ):
        """Initialize the orchestrator.

        Args:
            star_foundry: The Star Foundry for prompt resolution
            probe_executor: The Probe Executor for tool execution
            config: Execution configuration
        """
        self._foundry = star_foundry
        self._probe_executor = probe_executor
        self._config = config or ExecutionConfig()

        # Runtime components (initialized per-execution)
        self._sidekick: Optional[SidekickClient] = None
        self._worker_runtime: Optional[WorkerRuntime] = None
        self._phase_executor: Optional[PhaseExecutor] = None

    async def run(self, execution_input: ExecutionInput) -> ExecutionState:
        """Run a complete execution.

        Args:
            execution_input: The input parameters for the execution

        Returns:
            ExecutionState with results
        """
        # Use input config if provided
        config = execution_input.config or self._config

        # Get stars that will be used
        stars_used = self._get_stars_for_input(execution_input)

        # Initialize Sidekick
        async with SidekickClient.create(
            original_query=execution_input.query,
            stars_used=stars_used,
            probes_available=self._probe_executor.list_probes(),
            config=(
                config.model_dump() if hasattr(config, "model_dump") else config.dict()
            ),
            execution_id=execution_input.execution_id,
        ) as sidekick:
            self._sidekick = sidekick

            # Initialize runtime components
            self._worker_runtime = WorkerRuntime(
                star_foundry=self._foundry,
                probe_executor=self._probe_executor,
                sidekick=sidekick,
                config=config,
            )
            self._phase_executor = PhaseExecutor(
                worker_runtime=self._worker_runtime,
                sidekick=sidekick,
                config=config,
            )

            # Create initial state
            state = ExecutionState(
                execution_id=execution_input.execution_id,
                query=execution_input.query,
                constellation_id=execution_input.constellation_id,
                config=config,
                context=execution_input.context,
                status=ExecutionStatus.PENDING,
                started_at=datetime.utcnow(),
            )

            try:
                # Run the execution loop
                state = await self._run_execution_loop(state, execution_input)

                # Emit completion
                sidekick.emit_execution_completed(
                    final_output=state.final_output or "",
                    total_duration_seconds=state.duration_seconds,
                    total_llm_calls=state.total_llm_calls,
                    total_tool_calls=state.total_tool_calls,
                    total_tokens_used=state.total_tokens_used,
                )

                return state

            except Exception as e:
                state.status = ExecutionStatus.FAILED
                state.error = str(e)
                state.completed_at = datetime.utcnow()

                sidekick.emit_execution_failed(
                    error_message=str(e),
                    error_type=type(e).__name__,
                )

                raise

    async def _run_execution_loop(
        self,
        state: ExecutionState,
        execution_input: ExecutionInput,
    ) -> ExecutionState:
        """Run the main execution loop.

        Args:
            state: The current execution state
            execution_input: The original input

        Returns:
            Updated execution state
        """
        while True:
            # PLAN
            state = await self._plan(state, execution_input)
            if state.status == ExecutionStatus.FAILED:
                break

            # EXECUTE
            state = await self._execute(state)
            if state.status == ExecutionStatus.FAILED:
                break

            # EVALUATE
            state = await self._evaluate(state)
            if state.status == ExecutionStatus.FAILED:
                break

            # Check if we should replan or synthesize
            if not state.needs_replanning:
                break

            # Check replan limit
            if state.replan_count >= state.max_replans:
                logger.info(
                    f"Max replans ({state.max_replans}) reached, proceeding to synthesis"
                )
                break

            state.replan_count += 1
            logger.info(f"Replanning (attempt {state.replan_count})")

        # SYNTHESIZE
        state = await self._synthesize(state)

        return state

    async def _plan(
        self,
        state: ExecutionState,
        execution_input: ExecutionInput,
    ) -> ExecutionState:
        """Plan the execution.

        Args:
            state: Current execution state
            execution_input: Original input

        Returns:
            Updated state with plan
        """
        state.status = ExecutionStatus.PLANNING
        logger.info("Starting planning phase")

        try:
            if (
                execution_input.constellation_id
                and state.config.mode == ExecutionMode.STRICT
            ):
                # Use predefined Constellation
                # Note: For now, we'll use dynamic planning
                # Constellation loading would require additional infrastructure
                logger.info(
                    "Constellation mode not fully implemented, falling back to dynamic planning"
                )
                state.plan = await self._generate_dynamic_plan(state, execution_input)
            else:
                # Dynamic planning
                state.plan = await self._generate_dynamic_plan(state, execution_input)

            logger.info(f"Plan created with {len(state.plan.phases)} phases")

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            state.status = ExecutionStatus.FAILED
            state.error = f"Planning failed: {str(e)}"

        return state

    async def _generate_dynamic_plan(
        self,
        state: ExecutionState,
        execution_input: ExecutionInput,
    ) -> ExecutionPlan:
        """Generate a plan dynamically using an LLM.

        Args:
            state: Current execution state
            execution_input: Original input

        Returns:
            ExecutionPlan
        """
        llm = ChatOpenAI(
            model=self._config.default_model,
            temperature=0,
        )

        # Get available Stars
        available_stars = []
        for star in self._foundry.list_all():
            available_stars.append(
                {
                    "id": star.id,
                    "name": star.name,
                    "description": star.description,
                    "probes": star.probes,
                }
            )

        # Build context with any evaluation feedback
        context_str = ""
        if state.evaluation_feedback:
            context_str = (
                f"\n\n## Feedback from Previous Evaluation\n{state.evaluation_feedback}"
            )

        prompt = f"""Create an execution plan for the following query.

## Query
{state.query}

## Available Stars (prompt modules)
{json.dumps(available_stars, indent=2) if available_stars else "No specific stars available. Create generic workers."}

## Context
{json.dumps(state.context, indent=2) if state.context else "No additional context"}
{context_str}

## Instructions
Create a phased execution plan. Each phase can have multiple parallel workers.
Workers should use the most appropriate Star for their task.

Return your plan as JSON with this structure:
{{
    "reasoning": "Why this plan makes sense",
    "phases": [
        {{
            "phase_name": "Phase name",
            "phase_description": "What this phase accomplishes",
            "workers": [
                {{
                    "worker_name": "Descriptive name",
                    "star_id": "ID of Star to use (or 'default' if no Stars available)",
                    "task_description": "Specific task for this worker",
                    "needs_tools": true/false
                }}
            ]
        }}
    ]
}}"""

        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)

        # Parse response
        try:
            plan_data = json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re

            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
            else:
                # Create a default plan
                plan_data = {
                    "reasoning": "Default plan created due to parsing failure",
                    "phases": [
                        {
                            "phase_name": "Research",
                            "phase_description": "Research the query",
                            "workers": [
                                {
                                    "worker_name": "Researcher",
                                    "star_id": "default",
                                    "task_description": state.query,
                                    "needs_tools": True,
                                }
                            ],
                        }
                    ],
                }

        # Add phase indices
        for i, phase in enumerate(plan_data.get("phases", []), 1):
            phase["phase_index"] = i

        return ExecutionPlan(
            phases=plan_data.get("phases", []),
            reasoning=plan_data.get("reasoning", ""),
            estimated_duration_seconds=len(plan_data.get("phases", [])) * 60,
            estimated_total_workers=sum(
                len(p.get("workers", [])) for p in plan_data.get("phases", [])
            ),
        )

    async def _execute(self, state: ExecutionState) -> ExecutionState:
        """Execute all phases in the plan.

        Args:
            state: Current execution state

        Returns:
            Updated state
        """
        state.status = ExecutionStatus.EXECUTING
        logger.info(f"Starting execution with {len(state.plan.phases)} phases")

        for phase_def in state.plan.phases:
            phase_index = phase_def.get("phase_index", 0)
            phase_name = phase_def.get("phase_name", f"Phase {phase_index}")

            logger.info(f"Executing phase {phase_index}: {phase_name}")

            # Build phase state
            phase_state = await self._build_phase_state(phase_def, state)

            # Execute with Sidekick context
            if self._sidekick:
                async with self._sidekick.phase(
                    phase_name=phase_name,
                    phase_description=phase_def.get("phase_description", ""),
                    planned_workers=len(phase_def.get("workers", [])),
                    phase_index=phase_index,
                    phase_id=phase_state.phase_id,
                ):
                    phase_state = await self._phase_executor.execute(phase_state)
            else:
                phase_state = await self._phase_executor.execute(phase_state)

            state.phases.append(phase_state)
            state.current_phase_index = phase_index

            # Aggregate metrics
            state.total_phases += 1
            state.total_workers += len(phase_state.workers)
            state.total_llm_calls += sum(
                w.current_iteration for w in phase_state.workers
            )
            state.total_tool_calls += sum(
                len(w.tool_calls) for w in phase_state.workers
            )

            # Check for phase failure
            if (
                phase_state.status == PhaseStatus.FAILED
                and self._config.fail_fast_on_worker_error
            ):
                state.status = ExecutionStatus.FAILED
                state.error = f"Phase {phase_index} failed: {phase_state.error}"
                return state

        return state

    async def _build_phase_state(
        self,
        phase_def: Dict[str, Any],
        state: ExecutionState,
    ) -> PhaseState:
        """Build a PhaseState from a phase definition.

        Args:
            phase_def: Phase definition from the plan
            state: Current execution state

        Returns:
            PhaseState ready for execution
        """
        phase_state = PhaseState(
            phase_id=str(uuid.uuid4()),
            phase_name=phase_def.get("phase_name", ""),
            phase_index=phase_def.get("phase_index", 0),
            phase_description=phase_def.get("phase_description", ""),
        )

        # Build worker context from previous phases
        worker_context = self._build_worker_context(state)

        # Create WorkerStates
        for worker_def in phase_def.get("workers", []):
            star_id = worker_def.get("star_id", "default")

            # Try to get the star
            star = self._foundry.get_by_id(star_id)

            if star:
                compiled_prompt = self._foundry.resolve_star(star_id)
                available_probes = star.probes
            else:
                # Default prompt for when no Star is found
                compiled_prompt = "You are a helpful AI assistant. Complete the given task thoroughly and accurately."
                available_probes = (
                    self._probe_executor.list_probes()
                    if worker_def.get("needs_tools", False)
                    else []
                )

            worker_state = WorkerState(
                worker_id=str(uuid.uuid4()),
                worker_name=worker_def.get("worker_name", f"Worker-{star_id}"),
                phase_id=phase_state.phase_id,
                star_id=star_id,
                star_version=star.updated_on.isoformat() if star else "",
                compiled_prompt=compiled_prompt,
                task_description=worker_def.get("task_description", ""),
                input_context=worker_context,
                expected_output_format=worker_def.get("expected_output", ""),
                available_probes=available_probes,
            )

            phase_state.workers.append(worker_state)

        return phase_state

    def _build_worker_context(self, state: ExecutionState) -> str:
        """Build context for a worker from previous phase outputs.

        Args:
            state: Current execution state

        Returns:
            Context string
        """
        context_parts = [f"## Original Query\n{state.query}"]

        # Add execution context
        if state.context:
            context_parts.append(
                f"## Additional Context\n{json.dumps(state.context, indent=2)}"
            )

        # Add outputs from previous phases
        for phase in state.phases:
            if phase.phase_output:
                context_parts.append(
                    f"## Output from {phase.phase_name}\n{phase.phase_output}"
                )

        return "\n\n".join(context_parts)

    async def _evaluate(self, state: ExecutionState) -> ExecutionState:
        """Evaluate execution results and decide if replanning is needed.

        Args:
            state: Current execution state

        Returns:
            Updated state
        """
        state.status = ExecutionStatus.EVALUATING
        logger.info("Evaluating execution results")

        # Check if we've exceeded replan limit
        if state.replan_count >= state.max_replans:
            state.needs_replanning = False
            return state

        # Collect all phase outputs
        all_outputs = []
        for phase in state.phases:
            if phase.phase_output:
                all_outputs.append(f"## {phase.phase_name}\n{phase.phase_output}")

        # Simple evaluation: check if any phase failed
        failed_phases = [p for p in state.phases if p.status == PhaseStatus.FAILED]

        if failed_phases and state.config.mode != ExecutionMode.STRICT:
            state.needs_replanning = True
            state.evaluation_feedback = (
                f"Phases failed: {[p.phase_name for p in failed_phases]}. "
                f"Consider replanning to address failures."
            )
        else:
            # Use LLM to evaluate completeness
            try:
                eval_result = await self._llm_evaluate(state.query, all_outputs)

                if eval_result.get("is_complete", True):
                    state.needs_replanning = False
                else:
                    state.needs_replanning = True
                    missing = eval_result.get("missing_aspects", [])
                    state.evaluation_feedback = (
                        f"Evaluation score: {eval_result.get('completeness_score', 0):.2f}. "
                        f"Missing aspects: {', '.join(missing)}"
                    )

            except Exception as e:
                logger.warning(f"Evaluation failed: {e}, proceeding to synthesis")
                state.needs_replanning = False

        return state

    async def _llm_evaluate(
        self,
        query: str,
        outputs: List[str],
    ) -> Dict[str, Any]:
        """Use LLM to evaluate research completeness.

        Args:
            query: Original query
            outputs: Phase outputs

        Returns:
            Evaluation result dictionary
        """
        llm = ChatOpenAI(
            model=self._config.default_model,
            temperature=0,
        )

        prompt = f"""Evaluate whether these research outputs adequately address the original query.

## Original Query
{query}

## Research Outputs
{chr(10).join(outputs)}

## Instructions
Return your evaluation as JSON with these fields:
- completeness_score: float between 0 and 1
- is_complete: boolean (true if score >= 0.7)
- missing_aspects: list of strings describing gaps
- recommendation: "continue", "conclude", or "escalate"
- justification: string explaining your assessment"""

        messages = [
            SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"is_complete": True, "completeness_score": 1.0}

    async def _synthesize(self, state: ExecutionState) -> ExecutionState:
        """Synthesize final output from all phase outputs.

        Args:
            state: Current execution state

        Returns:
            Updated state with final output
        """
        state.status = ExecutionStatus.SYNTHESIZING
        logger.info("Synthesizing final output")

        llm = ChatOpenAI(
            model=self._config.default_model,
            temperature=0.3,  # Slightly higher for creative synthesis
        )

        # Collect all phase outputs
        all_outputs = []
        for phase in state.phases:
            if phase.phase_output:
                all_outputs.append(f"## {phase.phase_name}\n{phase.phase_output}")

        prompt = f"""Synthesize the following research outputs into a coherent final response.

## Original Query
{state.query}

## Phase Outputs
{chr(10).join(all_outputs)}

## Instructions
Create a well-structured, comprehensive response that:
1. Directly answers the original query
2. Incorporates insights from all phases
3. Is clear and well-organized
4. Acknowledges any limitations or uncertainties

Provide your synthesized response:"""

        messages = [
            SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)

        state.final_output = response.content
        state.status = ExecutionStatus.COMPLETED
        state.completed_at = datetime.utcnow()

        logger.info(f"Execution completed in {state.duration_seconds:.2f}s")

        return state

    def _get_stars_for_input(self, execution_input: ExecutionInput) -> List[str]:
        """Get Star IDs that will be used for this input.

        Args:
            execution_input: The execution input

        Returns:
            List of Star IDs
        """
        if execution_input.star_ids:
            return execution_input.star_ids

        # Return all available stars
        return [star.id for star in self._foundry.list_all()]
