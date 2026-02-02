"""Tests for ConstellationRunner."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from astro_backend_service.executor import ConstellationRunner, ExecutionContext, Run
from astro_backend_service.executor.runner import generate_run_id
from astro_backend_service.models import (
    Constellation,
    Directive,
    EvalDecision,
    StarType,
    WorkerStar,
)
from astro_backend_service.models.nodes import NodeType


class TestGenerateRunId:
    """Tests for run ID generation."""

    def test_generates_unique_ids(self) -> None:
        """Test that IDs are unique."""
        ids = {generate_run_id() for _ in range(100)}
        assert len(ids) == 100

    def test_id_format(self) -> None:
        """Test ID format."""
        run_id = generate_run_id()
        assert run_id.startswith("run_")
        assert len(run_id) == 16  # "run_" + 12 hex chars


class TestConstellationRunner:
    """Tests for ConstellationRunner."""

    def test_init(self, mock_foundry: Any) -> None:
        """Test runner initialization."""
        runner = ConstellationRunner(mock_foundry)
        assert runner.foundry is mock_foundry

    @pytest.mark.asyncio
    async def test_run_constellation_not_found(self, mock_foundry: Any) -> None:
        """Test running with invalid constellation ID."""
        runner = ConstellationRunner(mock_foundry)

        with pytest.raises(ValueError, match="not found"):
            await runner.run("nonexistent", {})

    @pytest.mark.asyncio
    async def test_run_simple_constellation(
        self,
        mock_foundry: Any,
        simple_constellation: Constellation,
        simple_star: WorkerStar,
        simple_directive: Directive,
    ) -> None:
        """Test running a simple linear constellation."""
        mock_foundry.add_constellation(simple_constellation)
        mock_foundry.add_star(simple_star)
        mock_foundry.add_directive(simple_directive)

        runner = ConstellationRunner(mock_foundry)

        run = await runner.run(
            "test_constellation",
            {"company_name": "Tesla"},
            "Analyze Tesla",
        )

        assert run.id.startswith("run_")
        assert run.constellation_id == "test_constellation"
        assert run.constellation_name == "Test Constellation"
        assert run.variables == {"company_name": "Tesla"}
        # Status depends on star execution (stub returns dict)
        assert run.status in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_run_creates_run_record(
        self,
        mock_foundry: Any,
        simple_constellation: Constellation,
        simple_star: WorkerStar,
        simple_directive: Directive,
    ) -> None:
        """Test that run creates proper Run record."""
        mock_foundry.add_constellation(simple_constellation)
        mock_foundry.add_star(simple_star)
        mock_foundry.add_directive(simple_directive)

        runner = ConstellationRunner(mock_foundry)

        run = await runner.run(
            "test_constellation",
            {"company_name": "Tesla"},
        )

        assert run.started_at is not None
        assert run.started_at <= datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_run_handles_error(self, mock_foundry: Any) -> None:
        """Test that run handles errors gracefully."""
        # Create constellation but not the star it references
        from astro_backend_service.models import (
            Constellation,
            Edge,
            EndNode,
            Position,
            StarNode,
            StartNode,
        )

        constellation = Constellation(
            id="broken",
            name="Broken",
            description="Missing star",
            start=StartNode(
                id="start", type=NodeType.START, position=Position(x=0, y=0)
            ),
            end=EndNode(id="end", type=NodeType.END, position=Position(x=200, y=0)),
            nodes=[
                StarNode(
                    id="node1",
                    type=NodeType.STAR,
                    position=Position(x=100, y=0),
                    star_id="missing_star",
                    display_name=None,
                )
            ],
            edges=[
                Edge(id="e1", source="start", target="node1", condition=None),
                Edge(id="e2", source="node1", target="end", condition=None),
            ],
        )
        mock_foundry.add_constellation(constellation)

        runner = ConstellationRunner(mock_foundry)
        run = await runner.run("broken", {})

        assert run.status == "failed"
        assert run.error is not None
        assert "not found" in run.error

    @pytest.mark.asyncio
    async def test_resolve_bindings(
        self,
        mock_foundry: Any,
        simple_star: WorkerStar,
        simple_directive: Directive,
    ) -> None:
        """Test variable binding resolution."""
        mock_foundry.add_star(simple_star)
        mock_foundry.add_directive(simple_directive)

        runner = ConstellationRunner(mock_foundry)

        from astro_backend_service.models import Position, StarNode

        node = StarNode(
            id="test_node",
            type=NodeType.STAR,
            position=Position(x=0, y=0),
            star_id="test_star",
            display_name=None,
        )

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="test",
            variables={"company_name": "Tesla"},
            foundry=mock_foundry,
        )

        bindings = runner._resolve_bindings(node, context)
        assert bindings == {"company_name": "Tesla"}

    @pytest.mark.asyncio
    async def test_resolve_bindings_missing_required(
        self,
        mock_foundry: Any,
        simple_star: WorkerStar,
        simple_directive: Directive,
    ) -> None:
        """Test that missing required variable raises error."""
        mock_foundry.add_star(simple_star)
        mock_foundry.add_directive(simple_directive)

        runner = ConstellationRunner(mock_foundry)

        from astro_backend_service.models import Position, StarNode

        node = StarNode(
            id="test_node",
            type=NodeType.STAR,
            position=Position(x=0, y=0),
            star_id="test_star",
            display_name=None,
        )

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="test",
            variables={},  # Missing required variable
            foundry=mock_foundry,
        )

        with pytest.raises(ValueError, match="Required variable"):
            runner._resolve_bindings(node, context)

    @pytest.mark.asyncio
    async def test_cancel_run(self, mock_foundry: Any) -> None:
        """Test cancelling a run."""
        runner = ConstellationRunner(mock_foundry)

        # Mock the _get_run method
        now = datetime.now(timezone.utc)
        mock_run = Run(
            id="run_123",
            constellation_id="test",
            constellation_name="Test",
            status="running",
            started_at=now,
        )

        runner._get_run = AsyncMock(return_value=mock_run)  # type: ignore[method-assign]
        runner._save_run = AsyncMock()  # type: ignore[method-assign]

        cancelled = await runner.cancel_run("run_123")

        assert cancelled.status == "cancelled"
        assert cancelled.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_already_completed(self, mock_foundry: Any) -> None:
        """Test that cancelling completed run does nothing."""
        runner = ConstellationRunner(mock_foundry)

        now = datetime.now(timezone.utc)
        mock_run = Run(
            id="run_123",
            constellation_id="test",
            constellation_name="Test",
            status="completed",
            started_at=now,
            completed_at=now,
        )

        runner._get_run = AsyncMock(return_value=mock_run)  # type: ignore[method-assign]

        result = await runner.cancel_run("run_123")
        assert result.status == "completed"


class TestEvalRouting:
    """Tests for EvalStar routing logic."""

    @pytest.mark.asyncio
    async def test_handle_continue_decision(
        self,
        mock_foundry: Any,
        eval_loop_constellation: Constellation,
    ) -> None:
        """Test that continue decision proceeds normally."""
        mock_foundry.add_constellation(eval_loop_constellation)

        runner = ConstellationRunner(mock_foundry)

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="eval_loop_constellation",
            foundry=mock_foundry,
        )

        now = datetime.now(timezone.utc)
        run = Run(
            id="run_123",
            constellation_id="eval_loop_constellation",
            constellation_name="Eval Loop",
            started_at=now,
        )

        decision = EvalDecision(decision="continue", reasoning="Looks good")

        # Should not raise, should not loop
        await runner._handle_eval_decision(
            decision, eval_loop_constellation, context, run
        )

        assert context.loop_count == 0  # No loop occurred

    @pytest.mark.asyncio
    async def test_handle_loop_decision_increments_count(
        self,
        mock_foundry: Any,
        eval_loop_constellation: Constellation,
    ) -> None:
        """Test that loop decision increments loop count."""
        from astro_backend_service.models import EvalStar, PlanningStar

        # Add all required stars
        planning_star = PlanningStar(
            id="planning_star",
            name="Planning",
            type=StarType.PLANNING,
            directive_id="directive_1",
        )
        worker_star = WorkerStar(
            id="worker_star",
            name="Worker",
            type=StarType.WORKER,
            directive_id="directive_1",
        )
        eval_star = EvalStar(
            id="eval_star",
            name="Eval",
            type=StarType.EVAL,
            directive_id="directive_1",
        )
        mock_foundry.add_constellation(eval_loop_constellation)
        mock_foundry.add_star(planning_star)
        mock_foundry.add_star(worker_star)
        mock_foundry.add_star(eval_star)

        runner = ConstellationRunner(mock_foundry)

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="eval_loop_constellation",
            foundry=mock_foundry,
        )

        now = datetime.now(timezone.utc)
        run = Run(
            id="run_123",
            constellation_id="eval_loop_constellation",
            constellation_name="Eval Loop",
            started_at=now,
        )

        decision = EvalDecision(decision="loop", reasoning="Need more work")

        # Mock _execute_from_node to prevent full re-execution
        runner._execute_from_node = AsyncMock()  # type: ignore

        await runner._handle_eval_decision(
            decision, eval_loop_constellation, context, run
        )

        assert context.loop_count == 1

    @pytest.mark.asyncio
    async def test_loop_forced_continue_at_max(
        self,
        mock_foundry: Any,
        eval_loop_constellation: Constellation,
    ) -> None:
        """Test that loop is forced to continue at max iterations."""
        mock_foundry.add_constellation(eval_loop_constellation)

        runner = ConstellationRunner(mock_foundry)

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="eval_loop_constellation",
            foundry=mock_foundry,
            loop_count=2,  # Already at 2, max is 3
        )

        now = datetime.now(timezone.utc)
        run = Run(
            id="run_123",
            constellation_id="eval_loop_constellation",
            constellation_name="Eval Loop",
            started_at=now,
        )

        decision = EvalDecision(decision="loop", reasoning="Want more")

        await runner._handle_eval_decision(
            decision, eval_loop_constellation, context, run
        )

        # Decision should be changed to continue
        assert decision.decision == "continue"
        assert "forced continue" in decision.reasoning


class TestHumanInTheLoop:
    """Tests for human-in-the-loop functionality."""

    @pytest.mark.asyncio
    async def test_pause_for_confirmation(
        self,
        mock_foundry: Any,
        hitl_constellation: Constellation,
    ) -> None:
        """Test that HITL node pauses execution."""
        mock_foundry.add_constellation(hitl_constellation)

        # Add the star
        worker_star = WorkerStar(
            id="worker_star",
            name="Worker",
            type=StarType.WORKER,
            directive_id="directive_1",
        )
        mock_foundry.add_star(worker_star)

        runner = ConstellationRunner(mock_foundry)
        runner._save_run = AsyncMock()  # type: ignore[method-assign]

        now = datetime.now(timezone.utc)
        run = Run(
            id="run_123",
            constellation_id="hitl_constellation",
            constellation_name="HITL",
            started_at=now,
        )

        from astro_backend_service.models import Position, StarNode

        node = StarNode(
            id="worker",
            type=NodeType.STAR,
            position=Position(x=0, y=0),
            star_id="worker_star",
            display_name=None,
            requires_confirmation=True,
            confirmation_prompt="Review and confirm?",
        )

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="hitl_constellation",
            variables={},
            foundry=mock_foundry,
        )

        await runner._pause_for_confirmation(node, run, context)

        assert run.status == "awaiting_confirmation"
        assert run.awaiting_node_id == "worker"
        assert run.awaiting_prompt == "Review and confirm?"

    @pytest.mark.asyncio
    async def test_resume_run_not_awaiting(self, mock_foundry: Any) -> None:
        """Test that resuming non-paused run raises error."""
        runner = ConstellationRunner(mock_foundry)

        now = datetime.now(timezone.utc)
        mock_run = Run(
            id="run_123",
            constellation_id="test",
            constellation_name="Test",
            status="running",  # Not awaiting
            started_at=now,
        )

        runner._get_run = AsyncMock(return_value=mock_run)  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="not awaiting confirmation"):
            await runner.resume_run("run_123")


class TestParallelExecution:
    """Tests for parallel execution."""

    @pytest.mark.asyncio
    async def test_execute_parallel_nodes_success(
        self,
        mock_foundry: Any,
        parallel_constellation: Constellation,
    ) -> None:
        """Test successful parallel execution."""
        mock_foundry.add_constellation(parallel_constellation)

        # Add directive needed by stars
        directive = Directive(
            id="directive_1",
            name="Test Directive",
            description="Test",
            content="Test prompt",
        )
        mock_foundry.add_directive(directive)

        # Add stars
        for star_id in ["star_1", "star_2", "synthesis_star"]:
            star = WorkerStar(
                id=star_id,
                name=star_id,
                type=StarType.WORKER,
                directive_id="directive_1",
            )
            mock_foundry.add_star(star)

        runner = ConstellationRunner(mock_foundry)

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="parallel_constellation",
            foundry=mock_foundry,
        )

        now = datetime.now(timezone.utc)
        run = Run(
            id="run_123",
            constellation_id="parallel_constellation",
            constellation_name="Parallel",
            started_at=now,
        )

        # Get the parallel nodes
        parallel_nodes = [
            n for n in parallel_constellation.nodes if n.id in ["worker_1", "worker_2"]
        ]

        results = await runner._execute_parallel_nodes(
            parallel_nodes, parallel_constellation, context, run
        )

        assert len(results) == 2


class TestRetryLogic:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, mock_foundry: Any) -> None:
        """Test that failed execution retries."""
        from astro_backend_service.models import (
            Constellation,
            Edge,
            EndNode,
            Position,
            StarNode,
            StartNode,
        )

        constellation = Constellation(
            id="retry_test",
            name="Retry Test",
            description="Test retries",
            start=StartNode(
                id="start", type=NodeType.START, position=Position(x=0, y=0)
            ),
            end=EndNode(id="end", type=NodeType.END, position=Position(x=200, y=0)),
            nodes=[
                StarNode(
                    id="node1",
                    type=NodeType.STAR,
                    position=Position(x=100, y=0),
                    star_id="star_1",
                    display_name=None,
                )
            ],
            edges=[
                Edge(id="e1", source="start", target="node1", condition=None),
                Edge(id="e2", source="node1", target="end", condition=None),
            ],
            max_retry_attempts=2,
            retry_delay_base=0.5,  # Minimum allowed value
        )
        mock_foundry.add_constellation(constellation)

        # Add directive needed by star
        directive = Directive(
            id="directive_1",
            name="Test Directive",
            description="Test",
            content="Test prompt",
        )
        mock_foundry.add_directive(directive)

        # Create a star that will fail
        failing_star = WorkerStar(
            id="star_1",
            name="Failing Star",
            type=StarType.WORKER,
            directive_id="directive_1",
        )
        mock_foundry.add_star(failing_star)

        runner = ConstellationRunner(mock_foundry)

        # Track call count
        call_count = 0
        original_execute = runner._execute_node

        async def counting_execute(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise ValueError("Simulated failure")
            return await original_execute(*args, **kwargs)

        runner._execute_node = counting_execute  # type: ignore

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="retry_test",
            foundry=mock_foundry,
        )

        now = datetime.now(timezone.utc)
        run = Run(
            id="run_123",
            constellation_id="retry_test",
            constellation_name="Retry Test",
            started_at=now,
        )

        node = constellation.nodes[0]

        # Should succeed on 3rd attempt
        await runner._execute_with_retry(
            node, constellation, context, run, max_attempts=2, delay_base=0.01
        )

        assert call_count == 3
