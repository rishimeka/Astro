"""Tests for output models."""

import pytest

from astro_backend_service.models import (
    WorkerOutput,
    Task,
    Plan,
    EvalDecision,
    SynthesisOutput,
    ExecutionResult,
    DocumentExtraction,
    DocExResult,
)
from astro_backend_service.models.outputs import ToolCall


class TestWorkerOutput:
    """Test WorkerOutput model."""

    def test_minimal_instantiation(self):
        """Test creating WorkerOutput with required fields."""
        output = WorkerOutput(result="Analysis complete")
        assert output.result == "Analysis complete"
        assert output.tool_calls == []
        assert output.iterations == 1
        assert output.status == "completed"

    def test_full_instantiation(self):
        """Test creating WorkerOutput with all fields."""
        tool_call = ToolCall(
            tool_name="web_search",
            arguments={"query": "AAPL stock"},
            result="Stock info...",
        )
        output = WorkerOutput(
            result="Searched and analyzed",
            tool_calls=[tool_call],
            iterations=3,
            status="completed",
        )
        assert len(output.tool_calls) == 1
        assert output.iterations == 3

    def test_json_serialization(self):
        """Test JSON round-trip."""
        output = WorkerOutput(result="Test", iterations=2)
        json_str = output.model_dump_json()
        restored = WorkerOutput.model_validate_json(json_str)
        assert restored == output


class TestPlan:
    """Test Plan model."""

    def test_instantiation(self):
        """Test creating Plan."""
        tasks = [
            Task(id="t1", description="Fetch data"),
            Task(id="t2", description="Analyze data", dependencies=["t1"]),
        ]
        plan = Plan(
            tasks=tasks,
            context="Analyzing company financials",
            success_criteria="All metrics extracted",
        )
        assert len(plan.tasks) == 2
        assert plan.tasks[1].dependencies == ["t1"]

    def test_json_serialization(self):
        """Test JSON round-trip."""
        plan = Plan(
            tasks=[Task(id="t1", description="Task 1")],
            context="Context",
            success_criteria="Success",
        )
        json_str = plan.model_dump_json()
        restored = Plan.model_validate_json(json_str)
        assert restored == plan


class TestEvalDecision:
    """Test EvalDecision model."""

    def test_continue_decision(self):
        """Test continue decision."""
        decision = EvalDecision(
            decision="continue",
            reasoning="Quality is acceptable",
        )
        assert decision.decision == "continue"
        assert decision.loop_target is None

    def test_loop_decision(self):
        """Test loop decision."""
        decision = EvalDecision(
            decision="loop",
            reasoning="Need more detail",
            loop_target="planning_star_1",
        )
        assert decision.decision == "loop"
        assert decision.loop_target == "planning_star_1"

    def test_invalid_decision(self):
        """Test invalid decision value."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EvalDecision(decision="invalid")


class TestSynthesisOutput:
    """Test SynthesisOutput model."""

    def test_instantiation(self):
        """Test creating SynthesisOutput."""
        output = SynthesisOutput(
            formatted_result="# Summary\n\nKey findings...",
            format_type="markdown",
            sources=["worker1", "worker2"],
            metadata={"word_count": 150},
        )
        assert output.format_type == "markdown"
        assert len(output.sources) == 2


class TestExecutionResult:
    """Test ExecutionResult model."""

    def test_instantiation(self):
        """Test creating ExecutionResult."""
        outputs = [
            WorkerOutput(result="Result 1"),
            WorkerOutput(result="Result 2"),
        ]
        result = ExecutionResult(
            worker_outputs=outputs,
            status="completed",
        )
        assert len(result.worker_outputs) == 2
        assert result.errors == []


class TestDocExResult:
    """Test DocExResult model."""

    def test_instantiation(self):
        """Test creating DocExResult."""
        docs = [
            DocumentExtraction(
                doc_id="doc1",
                extracted_content="Content from doc 1",
                metadata={"page_count": 5},
            ),
            DocumentExtraction(
                doc_id="doc2",
                extracted_content="Content from doc 2",
            ),
        ]
        result = DocExResult(documents=docs)
        assert len(result.documents) == 2
        assert result.documents[0].metadata["page_count"] == 5
