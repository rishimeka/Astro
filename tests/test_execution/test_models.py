"""Tests for execution engine data models."""

from datetime import datetime

from execution.models.input import (
    ExecutionInput,
    ExecutionConfig,
    ExecutionMode,
)
from execution.models.state import (
    ExecutionState,
    PhaseState,
    WorkerState,
    ToolCallRecord,
    ExecutionStatus,
    PhaseStatus,
    WorkerStatus,
)
from execution.models.constellation import (
    Constellation,
    ConstellationNode,
    ConstellationEdge,
)


class TestExecutionConfig:
    """Tests for ExecutionConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ExecutionConfig()

        assert config.mode == ExecutionMode.STRICT
        assert config.max_phases == 10
        assert config.max_workers_per_phase == 8
        assert config.max_iterations_per_worker == 10
        assert config.default_temperature == 0.0
        assert config.enable_parallel_workers is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ExecutionConfig(
            mode=ExecutionMode.DYNAMIC,
            max_phases=5,
            max_workers_per_phase=4,
            default_model="gpt-4",
            default_temperature=0.7,
        )

        assert config.mode == ExecutionMode.DYNAMIC
        assert config.max_phases == 5
        assert config.max_workers_per_phase == 4
        assert config.default_model == "gpt-4"
        assert config.default_temperature == 0.7


class TestExecutionInput:
    """Tests for ExecutionInput model."""

    def test_minimal_input(self):
        """Test creating input with just query."""
        input_obj = ExecutionInput(query="Test query")

        assert input_obj.query == "Test query"
        assert input_obj.execution_id is not None
        assert input_obj.constellation_id is None
        assert input_obj.context == {}

    def test_full_input(self):
        """Test creating input with all fields."""
        input_obj = ExecutionInput(
            query="Test query",
            constellation_id="test-constellation",
            star_ids=["star-1", "star-2"],
            context={"key": "value"},
            user_id="user-123",
            session_id="session-456",
        )

        assert input_obj.query == "Test query"
        assert input_obj.constellation_id == "test-constellation"
        assert input_obj.star_ids == ["star-1", "star-2"]
        assert input_obj.context == {"key": "value"}
        assert input_obj.user_id == "user-123"
        assert input_obj.session_id == "session-456"


class TestWorkerState:
    """Tests for WorkerState model."""

    def test_default_state(self):
        """Test default worker state."""
        worker = WorkerState(
            worker_name="Test Worker",
            phase_id="phase-1",
            star_id="star-1",
        )

        assert worker.status == WorkerStatus.PENDING
        assert worker.current_iteration == 0
        assert worker.messages == []
        assert worker.tool_calls == []
        assert worker.final_output is None

    def test_duration_calculation(self):
        """Test duration property calculation."""
        worker = WorkerState(
            worker_name="Test Worker",
            phase_id="phase-1",
            star_id="star-1",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 0, 30),
        )

        assert worker.duration_seconds == 30.0


class TestPhaseState:
    """Tests for PhaseState model."""

    def test_default_state(self):
        """Test default phase state."""
        phase = PhaseState(
            phase_name="Test Phase",
            phase_index=1,
        )

        assert phase.status == PhaseStatus.PENDING
        assert phase.workers == []
        assert phase.workers_completed == 0
        assert phase.workers_failed == 0


class TestExecutionState:
    """Tests for ExecutionState model."""

    def test_default_state(self):
        """Test default execution state."""
        state = ExecutionState(query="Test query")

        assert state.query == "Test query"
        assert state.status == ExecutionStatus.PENDING
        assert state.phases == []
        assert state.total_phases == 0
        assert state.final_output is None


class TestConstellation:
    """Tests for Constellation model."""

    def test_basic_constellation(self):
        """Test creating a basic constellation."""
        constellation = Constellation(
            id="test-constellation",
            name="Test Constellation",
            entry_node="node-1",
            exit_nodes=["node-2"],
            nodes=[
                ConstellationNode(node_id="node-1", star_id="star-1"),
                ConstellationNode(node_id="node-2", star_id="star-2"),
            ],
            edges=[
                ConstellationEdge(from_node="node-1", to_node="node-2"),
            ],
        )

        assert constellation.id == "test-constellation"
        assert len(constellation.nodes) == 2
        assert len(constellation.edges) == 1

    def test_get_node(self):
        """Test getting a node by ID."""
        constellation = Constellation(
            id="test",
            name="Test",
            entry_node="node-1",
            nodes=[
                ConstellationNode(node_id="node-1", star_id="star-1"),
                ConstellationNode(node_id="node-2", star_id="star-2"),
            ],
        )

        node = constellation.get_node("node-1")
        assert node is not None
        assert node.star_id == "star-1"

        missing = constellation.get_node("node-999")
        assert missing is None

    def test_topological_sort(self):
        """Test topological sorting of nodes."""
        constellation = Constellation(
            id="test",
            name="Test",
            entry_node="node-1",
            exit_nodes=["node-3"],
            nodes=[
                ConstellationNode(node_id="node-1", star_id="star-1"),
                ConstellationNode(node_id="node-2", star_id="star-2"),
                ConstellationNode(node_id="node-3", star_id="star-3"),
            ],
            edges=[
                ConstellationEdge(from_node="node-1", to_node="node-2"),
                ConstellationEdge(from_node="node-2", to_node="node-3"),
            ],
        )

        phases = constellation.topological_sort()

        # Should have 3 phases (sequential)
        assert len(phases) == 3
        assert phases[0] == ["node-1"]
        assert phases[1] == ["node-2"]
        assert phases[2] == ["node-3"]

    def test_topological_sort_parallel(self):
        """Test topological sort with parallel nodes."""
        constellation = Constellation(
            id="test",
            name="Test",
            entry_node="node-1",
            exit_nodes=["node-4"],
            nodes=[
                ConstellationNode(node_id="node-1", star_id="star-1"),
                ConstellationNode(node_id="node-2", star_id="star-2"),
                ConstellationNode(node_id="node-3", star_id="star-3"),
                ConstellationNode(node_id="node-4", star_id="star-4"),
            ],
            edges=[
                ConstellationEdge(from_node="node-1", to_node="node-2"),
                ConstellationEdge(from_node="node-1", to_node="node-3"),
                ConstellationEdge(from_node="node-2", to_node="node-4"),
                ConstellationEdge(from_node="node-3", to_node="node-4"),
            ],
        )

        phases = constellation.topological_sort()

        # Should have 3 phases: [node-1], [node-2, node-3], [node-4]
        assert len(phases) == 3
        assert phases[0] == ["node-1"]
        assert set(phases[1]) == {"node-2", "node-3"}
        assert phases[2] == ["node-4"]


class TestToolCallRecord:
    """Tests for ToolCallRecord model."""

    def test_successful_record(self):
        """Test creating a successful tool call record."""
        record = ToolCallRecord(
            probe_id="test-probe",
            probe_name="test-probe",
            arguments={"query": "test"},
            result="Success",
            success=True,
            latency_ms=100,
        )

        assert record.success is True
        assert record.result == "Success"
        assert record.error is None
        assert record.latency_ms == 100

    def test_failed_record(self):
        """Test creating a failed tool call record."""
        record = ToolCallRecord(
            probe_id="test-probe",
            probe_name="test-probe",
            arguments={},
            success=False,
            error="Connection timeout",
        )

        assert record.success is False
        assert record.error == "Connection timeout"
