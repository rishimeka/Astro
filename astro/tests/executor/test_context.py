"""Tests for ExecutionContext and WorkerContext."""

import pytest
from astro_backend_service.executor.context import ExecutionContext, WorkerContext
from astro_backend_service.models import Plan, Task


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_create_context(self) -> None:
        """Test creating an execution context."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
            original_query="Analyze Tesla",
            constellation_purpose="Financial analysis",
            variables={"company_name": "Tesla"},
        )

        assert context.run_id == "run_123"
        assert context.constellation_id == "constellation_1"
        assert context.original_query == "Analyze Tesla"
        assert context.constellation_purpose == "Financial analysis"
        assert context.variables == {"company_name": "Tesla"}
        assert context.node_outputs == {}
        assert context.loop_count == 0
        assert context.foundry is None

    def test_get_directive_without_foundry(self) -> None:
        """Test that get_directive raises without foundry."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
        )

        with pytest.raises(ValueError, match="Foundry not set"):
            context.get_directive("some_directive")

    def test_get_constellation_without_foundry(self) -> None:
        """Test that get_constellation raises without foundry."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
        )

        with pytest.raises(ValueError, match="Foundry not set"):
            context.get_constellation()

    def test_get_upstream_output(self) -> None:
        """Test getting upstream output by type."""
        plan = Plan(
            tasks=[Task(id="t1", description="Do something")],
            context="Some context",
        )

        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
            node_outputs={"planning_node": plan},
        )

        result = context.get_upstream_output(Plan)
        assert result is plan

    def test_get_upstream_output_not_found(self) -> None:
        """Test getting upstream output when type not present."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
            node_outputs={"some_node": {"result": "data"}},
        )

        result = context.get_upstream_output(Plan)
        assert result is None

    def test_get_documents_from_variables(self) -> None:
        """Test getting documents from variables."""
        docs = [{"id": "doc1", "content": "Content"}]
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
            variables={"documents": docs},
        )

        result = context.get_documents()
        assert result == docs

    def test_get_documents_empty(self) -> None:
        """Test getting documents when none available."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
        )

        result = context.get_documents()
        assert result == []

    def test_find_star_for_task_stub(self) -> None:
        """Test that find_star_for_task returns None (stub)."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
        )
        task = Task(id="t1", description="Do something")

        result = context.find_star_for_task(task)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_dynamic_star_raises_without_foundry(self) -> None:
        """Test that create_dynamic_star raises ValueError without foundry."""
        context = ExecutionContext(
            run_id="run_123",
            constellation_id="constellation_1",
        )
        task = Task(id="t1", description="Do something")

        with pytest.raises(ValueError, match="Foundry not set"):
            await context.create_dynamic_star(task)


class TestWorkerContext:
    """Tests for WorkerContext."""

    def test_create_worker_context(self) -> None:
        """Test creating a worker context."""
        context = WorkerContext(
            task_description="Analyze financial data",
            variable_bindings={"ticker": "TSLA"},
            original_query="Analyze Tesla",
            constellation_purpose="Financial analysis",
            available_probes=["search_web", "get_financial_data"],
            constraints=None,
            role=None,
        )

        assert context.task_description == "Analyze financial data"
        assert context.variable_bindings == {"ticker": "TSLA"}
        assert context.original_query == "Analyze Tesla"
        assert context.constellation_purpose == "Financial analysis"
        assert context.available_probes == ["search_web", "get_financial_data"]
        assert context.constraints is None
        assert context.role is None
        assert "ambiguous" in context.error_handling

    def test_worker_context_with_constraints(self) -> None:
        """Test worker context with constraints."""
        context = WorkerContext(
            task_description="Analyze data",
            constraints="Only use public data sources",
            role="Financial Analyst",
        )

        assert context.constraints == "Only use public data sources"
        assert context.role == "Financial Analyst"

    def test_worker_context_with_upstream_outputs(self) -> None:
        """Test worker context with upstream outputs."""
        upstream = [{"result": "Data from upstream"}]  # type: ignore[list-item]
        context = WorkerContext(
            task_description="Process data",
            upstream_outputs=upstream,
            constraints=None,
            role=None,
        )

        assert context.upstream_outputs == upstream
