"""Tests for the Run and NodeOutput models."""

from datetime import UTC, datetime

from astro_backend_service.executor.run import NodeOutput, Run, ToolCallRecord


class TestToolCallRecord:
    """Tests for ToolCallRecord model."""

    def test_create_with_result(self) -> None:
        """Test creating a tool call record with result."""
        record = ToolCallRecord(
            tool_name="search_web",
            arguments={"query": "test"},
            result="Search results here",
        )

        assert record.tool_name == "search_web"
        assert record.arguments == {"query": "test"}
        assert record.result == "Search results here"
        assert record.error is None

    def test_create_with_error(self) -> None:
        """Test creating a tool call record with error."""
        record = ToolCallRecord(
            tool_name="search_web",
            arguments={"query": "test"},
            error="Connection failed",
        )

        assert record.tool_name == "search_web"
        assert record.error == "Connection failed"
        assert record.result is None


class TestNodeOutput:
    """Tests for NodeOutput model."""

    def test_create_pending(self) -> None:
        """Test creating a pending node output."""
        output = NodeOutput(
            node_id="node_1",
            star_id="star_1",
        )

        assert output.node_id == "node_1"
        assert output.star_id == "star_1"
        assert output.status == "pending"
        assert output.started_at is None
        assert output.completed_at is None
        assert output.output is None
        assert output.error is None
        assert output.tool_calls == []

    def test_create_completed(self) -> None:
        """Test creating a completed node output."""
        now = datetime.now(UTC)
        output = NodeOutput(
            node_id="node_1",
            star_id="star_1",
            status="completed",
            started_at=now,
            completed_at=now,
            output="Result here",
        )

        assert output.status == "completed"
        assert output.output == "Result here"

    def test_create_failed(self) -> None:
        """Test creating a failed node output."""
        output = NodeOutput(
            node_id="node_1",
            star_id="star_1",
            status="failed",
            error="Something went wrong",
        )

        assert output.status == "failed"
        assert output.error == "Something went wrong"

    def test_with_tool_calls(self) -> None:
        """Test node output with tool calls."""
        output = NodeOutput(
            node_id="node_1",
            star_id="star_1",
            tool_calls=[
                ToolCallRecord(
                    tool_name="search_web",
                    arguments={"query": "test"},
                    result="Results",
                )
            ],
        )

        assert len(output.tool_calls) == 1
        assert output.tool_calls[0].tool_name == "search_web"


class TestRun:
    """Tests for Run model."""

    def test_create_run(self) -> None:
        """Test creating a new run."""
        now = datetime.now(UTC)
        run = Run(
            id="run_abc123",
            constellation_id="test_constellation",
            constellation_name="Test Constellation",
            started_at=now,
            variables={"company_name": "Tesla"},
        )

        assert run.id == "run_abc123"
        assert run.constellation_id == "test_constellation"
        assert run.constellation_name == "Test Constellation"
        assert run.status == "running"
        assert run.variables == {"company_name": "Tesla"}
        assert run.started_at == now
        assert run.completed_at is None
        assert run.node_outputs == {}
        assert run.final_output is None
        assert run.error is None
        assert run.awaiting_node_id is None
        assert run.awaiting_prompt is None

    def test_run_completed(self) -> None:
        """Test a completed run."""
        now = datetime.now(UTC)
        run = Run(
            id="run_abc123",
            constellation_id="test_constellation",
            constellation_name="Test Constellation",
            status="completed",
            started_at=now,
            completed_at=now,
            final_output="Final result here",
        )

        assert run.status == "completed"
        assert run.final_output == "Final result here"

    def test_run_failed(self) -> None:
        """Test a failed run."""
        now = datetime.now(UTC)
        run = Run(
            id="run_abc123",
            constellation_id="test_constellation",
            constellation_name="Test Constellation",
            status="failed",
            started_at=now,
            completed_at=now,
            error="Execution failed",
        )

        assert run.status == "failed"
        assert run.error == "Execution failed"

    def test_run_awaiting_confirmation(self) -> None:
        """Test a run waiting for user confirmation."""
        now = datetime.now(UTC)
        run = Run(
            id="run_abc123",
            constellation_id="test_constellation",
            constellation_name="Test Constellation",
            status="awaiting_confirmation",
            started_at=now,
            awaiting_node_id="node_1",
            awaiting_prompt="Review and confirm?",
        )

        assert run.status == "awaiting_confirmation"
        assert run.awaiting_node_id == "node_1"
        assert run.awaiting_prompt == "Review and confirm?"

    def test_run_with_node_outputs(self) -> None:
        """Test run with multiple node outputs."""
        now = datetime.now(UTC)
        run = Run(
            id="run_abc123",
            constellation_id="test_constellation",
            constellation_name="Test Constellation",
            started_at=now,
            node_outputs={
                "node_1": NodeOutput(
                    node_id="node_1",
                    star_id="star_1",
                    status="completed",
                    output="Output 1",
                ),
                "node_2": NodeOutput(
                    node_id="node_2",
                    star_id="star_2",
                    status="running",
                ),
            },
        )

        assert len(run.node_outputs) == 2
        assert run.node_outputs["node_1"].status == "completed"
        assert run.node_outputs["node_2"].status == "running"

    def test_run_cancelled(self) -> None:
        """Test a cancelled run."""
        now = datetime.now(UTC)
        run = Run(
            id="run_abc123",
            constellation_id="test_constellation",
            constellation_name="Test Constellation",
            status="cancelled",
            started_at=now,
            completed_at=now,
        )

        assert run.status == "cancelled"
