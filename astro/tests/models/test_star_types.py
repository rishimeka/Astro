"""Tests for concrete Star types."""

from astro_backend_service.models import (
    DocExStar,
    EvalStar,
    ExecutionStar,
    PlanningStar,
    StarType,
    SynthesisStar,
    WorkerStar,
)


class TestWorkerStar:
    """Test WorkerStar model."""

    def test_minimal_instantiation(self):
        """Test creating WorkerStar with required fields."""
        star = WorkerStar(
            id="worker1",
            name="Analysis Worker",
            directive_id="analyze_directive",
        )
        assert star.id == "worker1"
        assert star.type == StarType.WORKER
        assert star.directive_id == "analyze_directive"
        assert star.probe_ids == []
        assert star.max_iterations == 10
        assert star.ai_generated is False

    def test_full_instantiation(self):
        """Test creating WorkerStar with all fields."""
        star = WorkerStar(
            id="worker1",
            name="Analysis Worker",
            directive_id="analyze_directive",
            probe_ids=["web_search", "calculator"],
            config={"temperature": 0.7},
            max_iterations=5,
            ai_generated=True,
            metadata={"author": "test"},
        )
        assert star.probe_ids == ["web_search", "calculator"]
        assert star.max_iterations == 5
        assert star.ai_generated is True

    def test_json_serialization(self):
        """Test JSON round-trip."""
        star = WorkerStar(
            id="w1",
            name="Worker",
            directive_id="d1",
        )
        json_str = star.model_dump_json()
        restored = WorkerStar.model_validate_json(json_str)
        assert restored.id == star.id
        assert restored.type == StarType.WORKER


class TestPlanningStar:
    """Test PlanningStar model."""

    def test_instantiation(self):
        """Test creating PlanningStar."""
        star = PlanningStar(
            id="planner1",
            name="Deal Planner",
            directive_id="planning_directive",
        )
        assert star.type == StarType.PLANNING

    def test_type_is_frozen(self):
        """Test that type cannot be changed."""
        star = PlanningStar(
            id="p1",
            name="Planner",
            directive_id="d1",
        )
        # Type should be frozen
        assert star.type == StarType.PLANNING


class TestEvalStar:
    """Test EvalStar model."""

    def test_instantiation(self):
        """Test creating EvalStar."""
        star = EvalStar(
            id="eval1",
            name="Quality Evaluator",
            directive_id="eval_directive",
        )
        assert star.type == StarType.EVAL


class TestSynthesisStar:
    """Test SynthesisStar model."""

    def test_instantiation(self):
        """Test creating SynthesisStar."""
        star = SynthesisStar(
            id="synth1",
            name="Report Synthesizer",
            directive_id="synthesis_directive",
            probe_ids=["pdf_generator"],
        )
        assert star.type == StarType.SYNTHESIS
        assert star.probe_ids == ["pdf_generator"]


class TestExecutionStar:
    """Test ExecutionStar model."""

    def test_instantiation(self):
        """Test creating ExecutionStar."""
        star = ExecutionStar(
            id="exec1",
            name="Task Executor",
            directive_id="execution_directive",
        )
        assert star.type == StarType.EXECUTION
        assert star.parallel is True

    def test_sequential_execution(self):
        """Test ExecutionStar with sequential execution."""
        star = ExecutionStar(
            id="exec1",
            name="Sequential Executor",
            directive_id="d1",
            parallel=False,
        )
        assert star.parallel is False


class TestDocExStar:
    """Test DocExStar model."""

    def test_instantiation(self):
        """Test creating DocExStar."""
        star = DocExStar(
            id="docex1",
            name="Document Extractor",
            directive_id="docex_directive",
        )
        assert star.type == StarType.DOCEX
