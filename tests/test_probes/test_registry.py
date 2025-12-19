"""Tests for probes.registry module."""

from probes.registry import ProbeRegistry
from inspect import signature


class TestProbeRegistry:
    """Test suite for the ProbeRegistry class."""

    def setup_method(self):
        """Create a fresh ProbeRegistry for each test."""
        self.registry = ProbeRegistry()

    def test_registry_initialization(self):
        """Test that ProbeRegistry initializes with empty probes dictionary."""
        assert self.registry._probes == {}

    def test_register_probe(self):
        """Test registering a probe function."""

        def sample_func(x: int) -> int:
            return x * 2

        sig = signature(sample_func)
        param_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        return_schema = {"type": "integer"}

        self.registry.register(
            id="test_probe",
            fun=sample_func,
            description="Test probe",
            signature=sig,
            param_schema=param_schema,
            return_schema=return_schema,
        )

        probe = self.registry.get_probe("test_probe")
        assert probe is not None
        assert probe["id"] == "test_probe"
        assert probe["function"] == sample_func
        assert probe["description"] == "Test probe"
        assert probe["signature"] == sig
        assert probe["param_schema"] == param_schema
        assert probe["return_schema"] == return_schema

    def test_get_probe_nonexistent(self):
        """Test retrieving a probe that doesn't exist returns None."""
        result = self.registry.get_probe("nonexistent")
        assert result is None

    def test_list_probes_empty(self):
        """Test listing probes when registry is empty."""
        assert self.registry.list_probes() == []

    def test_list_probes_with_probes(self):
        """Test listing all registered probe IDs."""

        def func1(x: int) -> int:
            return x

        def func2(y: str) -> str:
            return y

        sig = signature(func1)
        self.registry.register(
            id="probe1",
            fun=func1,
            description="First probe",
            signature=sig,
            param_schema={},
        )

        sig2 = signature(func2)
        self.registry.register(
            id="probe2",
            fun=func2,
            description="Second probe",
            signature=sig2,
            param_schema={},
        )

        probes = self.registry.list_probes()
        assert len(probes) == 2
        assert "probe1" in probes
        assert "probe2" in probes

    def test_get_multiple_probes(self):
        """Test retrieving multiple probes by IDs."""

        def func1(x: int) -> int:
            return x

        def func2(y: str) -> str:
            return y

        sig1 = signature(func1)
        sig2 = signature(func2)

        self.registry.register(
            id="probe1", fun=func1, description="First", signature=sig1, param_schema={}
        )
        self.registry.register(
            id="probe2",
            fun=func2,
            description="Second",
            signature=sig2,
            param_schema={},
        )

        probes = self.registry.get_multiple(["probe1", "probe2"])
        assert len(probes) == 2
        assert "probe1" in probes
        assert "probe2" in probes
        assert probes["probe1"]["function"] == func1
        assert probes["probe2"]["function"] == func2

    def test_get_multiple_probes_partial_match(self):
        """Test retrieving multiple probes where some don't exist."""

        def func1(x: int) -> int:
            return x

        sig = signature(func1)
        self.registry.register(
            id="probe1", fun=func1, description="First", signature=sig, param_schema={}
        )

        probes = self.registry.get_multiple(["probe1", "nonexistent"])
        assert len(probes) == 1
        assert "probe1" in probes
        assert "nonexistent" not in probes

    def test_get_all_probes_empty(self):
        """Test getting all probes when registry is empty."""
        probes = self.registry.get_all()
        assert probes == {}

    def test_get_all_probes(self):
        """Test getting all registered probes."""

        def func1(x: int) -> int:
            return x

        def func2(y: str) -> str:
            return y

        sig1 = signature(func1)
        sig2 = signature(func2)

        self.registry.register(
            id="probe1",
            fun=func1,
            description="First",
            signature=sig1,
            param_schema={"type": "object"},
        )
        self.registry.register(
            id="probe2",
            fun=func2,
            description="Second",
            signature=sig2,
            param_schema={"type": "object"},
        )

        all_probes = self.registry.get_all()
        assert len(all_probes) == 2
        assert "probe1" in all_probes
        assert "probe2" in all_probes

    def test_get_planner_schemas_all(self):
        """Test getting planner schemas for all probes."""

        def func1(x: int) -> int:
            return x

        sig = signature(func1)
        param_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        return_schema = {"type": "integer"}

        self.registry.register(
            id="probe1",
            fun=func1,
            description="Test probe",
            signature=sig,
            param_schema=param_schema,
            return_schema=return_schema,
        )

        schemas = self.registry.get_planner_schemas()
        assert len(schemas) == 1
        assert "probe1" in schemas
        assert schemas["probe1"]["id"] == "probe1"
        assert schemas["probe1"]["description"] == "Test probe"
        assert schemas["probe1"]["params"] == param_schema
        assert schemas["probe1"]["returns"] == return_schema

    def test_get_planner_schemas_specific_ids(self):
        """Test getting planner schemas for specific probe IDs."""

        def func1(x: int) -> int:
            return x

        def func2(y: str) -> str:
            return y

        sig1 = signature(func1)
        sig2 = signature(func2)

        self.registry.register(
            id="probe1",
            fun=func1,
            description="First",
            signature=sig1,
            param_schema={"type": "object"},
            return_schema={"type": "integer"},
        )
        self.registry.register(
            id="probe2",
            fun=func2,
            description="Second",
            signature=sig2,
            param_schema={"type": "object"},
            return_schema={"type": "string"},
        )

        schemas = self.registry.get_planner_schemas(["probe1"])
        assert len(schemas) == 1
        assert "probe1" in schemas
        assert "probe2" not in schemas

    def test_get_planner_schemas_nonexistent_ids(self):
        """Test getting planner schemas for IDs that don't exist."""
        schemas = self.registry.get_planner_schemas(["nonexistent"])
        assert schemas == {}

    def test_register_probe_without_return_schema(self):
        """Test registering a probe without a return schema."""

        def func(x: int):
            return x

        sig = signature(func)
        self.registry.register(
            id="no_return",
            fun=func,
            description="No return schema",
            signature=sig,
            param_schema={"type": "object"},
        )

        probe = self.registry.get_probe("no_return")
        assert probe is not None
        assert probe["return_schema"] is None

    def test_register_overwrite_probe(self):
        """Test that registering a probe with same ID overwrites the previous one."""

        def func1(x: int) -> int:
            return x

        def func2(x: int) -> int:
            return x * 2

        sig1 = signature(func1)
        sig2 = signature(func2)

        self.registry.register(
            id="probe",
            fun=func1,
            description="First version",
            signature=sig1,
            param_schema={},
        )

        self.registry.register(
            id="probe",
            fun=func2,
            description="Second version",
            signature=sig2,
            param_schema={},
        )

        probe = self.registry.get_probe("probe")
        assert probe["function"] == func2
        assert probe["description"] == "Second version"
