"""Phase Executor for managing parallel worker execution.

This module handles the execution of all workers within a phase,
supporting both parallel and sequential execution modes.
"""

import asyncio
from datetime import datetime
from typing import List, Optional
import logging

from execution.models.input import ExecutionConfig
from execution.models.state import PhaseState, WorkerState, PhaseStatus, WorkerStatus
from execution.worker_runtime import WorkerRuntime
from execution.sidekick import SidekickClient

logger = logging.getLogger(__name__)


class PhaseExecutor:
    """Executes a phase with parallel workers.

    Manages worker concurrency, timeouts, and aggregates results.
    """

    def __init__(
        self,
        worker_runtime: WorkerRuntime,
        sidekick: Optional[SidekickClient] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        """Initialize the phase executor.

        Args:
            worker_runtime: The WorkerRuntime for executing individual workers
            sidekick: Optional Sidekick client for observability
            config: Execution configuration
        """
        self._worker_runtime = worker_runtime
        self._sidekick = sidekick
        self._config = config or ExecutionConfig()

    async def execute(self, phase_state: PhaseState) -> PhaseState:
        """Execute all workers in a phase.

        Workers run in parallel up to max_workers_per_phase.

        Args:
            phase_state: The initial phase state with workers to execute

        Returns:
            The updated PhaseState with results
        """
        phase_state.status = PhaseStatus.RUNNING
        phase_state.started_at = datetime.utcnow()

        logger.info(
            f"Starting phase '{phase_state.phase_name}' with "
            f"{len(phase_state.workers)} workers"
        )

        try:
            if self._config.enable_parallel_workers:
                await self._execute_parallel(phase_state)
            else:
                await self._execute_sequential(phase_state)

            # Determine phase status based on worker results
            self._determine_phase_status(phase_state)

            # Aggregate phase output
            phase_state.phase_output = self._aggregate_outputs(phase_state.workers)

        except Exception as e:
            phase_state.status = PhaseStatus.FAILED
            phase_state.error = str(e)
            logger.error(f"Phase '{phase_state.phase_name}' failed: {e}")

        finally:
            phase_state.completed_at = datetime.utcnow()
            logger.info(
                f"Phase '{phase_state.phase_name}' completed with status "
                f"{phase_state.status.value} in {phase_state.duration_seconds:.2f}s"
            )

        return phase_state

    async def _execute_parallel(self, phase_state: PhaseState) -> None:
        """Execute workers in parallel with concurrency limit.

        Args:
            phase_state: The phase state containing workers
        """
        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self._config.max_workers_per_phase)

        async def execute_with_semaphore(worker: WorkerState) -> WorkerState:
            """Execute a single worker with semaphore protection."""
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self._execute_worker_with_sidekick(worker),
                        timeout=self._config.worker_timeout,
                    )
                except asyncio.TimeoutError:
                    worker.status = WorkerStatus.TIMEOUT
                    worker.error = (
                        f"Worker timed out after {self._config.worker_timeout}s"
                    )
                    worker.completed_at = datetime.utcnow()
                    return worker

        # Execute all workers in parallel
        tasks = [execute_with_semaphore(worker) for worker in phase_state.workers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                phase_state.workers[i].status = WorkerStatus.FAILED
                phase_state.workers[i].error = str(result)
                phase_state.workers[i].completed_at = datetime.utcnow()
                phase_state.workers_failed += 1
            else:
                phase_state.workers[i] = result
                if result.status == WorkerStatus.COMPLETED:
                    phase_state.workers_completed += 1
                else:
                    phase_state.workers_failed += 1

    async def _execute_sequential(self, phase_state: PhaseState) -> None:
        """Execute workers sequentially.

        Args:
            phase_state: The phase state containing workers
        """
        for i, worker in enumerate(phase_state.workers):
            try:
                result = await asyncio.wait_for(
                    self._execute_worker_with_sidekick(worker),
                    timeout=self._config.worker_timeout,
                )

                phase_state.workers[i] = result

                if result.status == WorkerStatus.COMPLETED:
                    phase_state.workers_completed += 1
                else:
                    phase_state.workers_failed += 1

                    if self._config.fail_fast_on_worker_error:
                        logger.warning(
                            f"Fail-fast enabled: stopping after worker "
                            f"'{worker.worker_name}' failed"
                        )
                        break

            except asyncio.TimeoutError:
                worker.status = WorkerStatus.TIMEOUT
                worker.error = f"Worker timed out after {self._config.worker_timeout}s"
                worker.completed_at = datetime.utcnow()
                phase_state.workers_failed += 1

                if self._config.fail_fast_on_worker_error:
                    break

            except Exception as e:
                worker.status = WorkerStatus.FAILED
                worker.error = str(e)
                worker.completed_at = datetime.utcnow()
                phase_state.workers_failed += 1

                if self._config.fail_fast_on_worker_error:
                    break

    async def _execute_worker_with_sidekick(
        self,
        worker: WorkerState,
    ) -> WorkerState:
        """Execute a worker with Sidekick context manager.

        Args:
            worker: The worker to execute

        Returns:
            The updated worker state
        """
        if self._sidekick:
            async with self._sidekick.worker(
                worker_name=worker.worker_name,
                star_id=worker.star_id,
                task_description=worker.task_description,
                worker_id=worker.worker_id,
            ):
                return await self._worker_runtime.execute(worker)
        else:
            return await self._worker_runtime.execute(worker)

    def _determine_phase_status(self, phase_state: PhaseState) -> None:
        """Determine the phase status based on worker results.

        Args:
            phase_state: The phase state to update
        """
        if phase_state.workers_failed == 0:
            phase_state.status = PhaseStatus.COMPLETED
        elif phase_state.workers_completed == 0:
            phase_state.status = PhaseStatus.FAILED
        else:
            phase_state.status = PhaseStatus.PARTIAL

    def _aggregate_outputs(self, workers: List[WorkerState]) -> str:
        """Aggregate worker outputs into a phase summary.

        Args:
            workers: List of worker states

        Returns:
            Formatted string with all worker outputs
        """
        outputs = []

        for worker in workers:
            if worker.status == WorkerStatus.COMPLETED and worker.final_output:
                outputs.append(f"### {worker.worker_name}\n{worker.final_output}")
            elif worker.status in (WorkerStatus.FAILED, WorkerStatus.TIMEOUT):
                outputs.append(
                    f"### {worker.worker_name}\n[{worker.status.value.upper()}: {worker.error}]"
                )

        return "\n\n".join(outputs)


class PhaseBuilder:
    """Helper class for building PhaseState objects."""

    def __init__(self, phase_id: str, phase_name: str, phase_index: int):
        """Initialize the phase builder.

        Args:
            phase_id: Unique identifier for the phase
            phase_name: Human-readable name
            phase_index: Index in the execution sequence
        """
        self._phase_state = PhaseState(
            phase_id=phase_id,
            phase_name=phase_name,
            phase_index=phase_index,
        )

    def with_description(self, description: str) -> "PhaseBuilder":
        """Set the phase description.

        Args:
            description: Phase description

        Returns:
            Self for chaining
        """
        self._phase_state.phase_description = description
        return self

    def add_worker(self, worker: WorkerState) -> "PhaseBuilder":
        """Add a worker to the phase.

        Args:
            worker: The worker state to add

        Returns:
            Self for chaining
        """
        worker.phase_id = self._phase_state.phase_id
        self._phase_state.workers.append(worker)
        return self

    def build(self) -> PhaseState:
        """Build and return the PhaseState.

        Returns:
            The constructed PhaseState
        """
        return self._phase_state
