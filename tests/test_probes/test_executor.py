"""Tests for probes.executor module."""

import pytest
import asyncio
from probes.executor import ProbeExecutor
from probes.registry import probe_registry
from inspect import signature


class TestProbeExecutor:
    """Test suite for the ProbeExecutor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = ProbeExecutor()
        probe_registry._probes = {}

    def test_execute_probe_success(self):
        """Test executing a registered probe successfully."""

        def test_func(x: int, y: int) -> int:
            return x + y

        sig = signature(test_func)
        probe_registry.register(
            id="add_probe",
            fun=test_func,
            description="Add two numbers",
            signature=sig,
            param_schema={},
        )

        result = self.executor.execute_probe("add_probe", 5, 10)
        assert result == 15

    def test_execute_probe_with_kwargs(self):
        """Test executing a probe with keyword arguments."""

        def test_func(x: int, y: int = 10) -> int:
            return x * y

        sig = signature(test_func)
        probe_registry.register(
            id="multiply_probe",
            fun=test_func,
            description="Multiply two numbers",
            signature=sig,
            param_schema={},
        )

        result = self.executor.execute_probe("multiply_probe", x=5, y=3)
        assert result == 15

    def test_execute_probe_mixed_args_kwargs(self):
        """Test executing a probe with both positional and keyword arguments."""

        def test_func(x: int, y: int, z: int = 1) -> int:
            return x + y + z

        sig = signature(test_func)
        probe_registry.register(
            id="mixed_probe",
            fun=test_func,
            description="Mixed args probe",
            signature=sig,
            param_schema={},
        )

        result = self.executor.execute_probe("mixed_probe", 5, 10, z=20)
        assert result == 35

    def test_execute_probe_not_found(self):
        """Test executing a probe that doesn't exist raises KeyError."""
        with pytest.raises(KeyError, match="Probe with ID 'nonexistent' not found"):
            self.executor.execute_probe("nonexistent", 1, 2)

    def test_execute_probe_no_arguments(self):
        """Test executing a probe that takes no arguments."""

        def test_func() -> str:
            return "success"

        sig = signature(test_func)
        probe_registry.register(
            id="no_args_probe",
            fun=test_func,
            description="No arguments probe",
            signature=sig,
            param_schema={},
        )

        result = self.executor.execute_probe("no_args_probe")
        assert result == "success"

    def test_execute_probe_returns_none(self):
        """Test executing a probe that returns None."""

        def test_func(x: int) -> None:
            pass

        sig = signature(test_func)
        probe_registry.register(
            id="none_probe",
            fun=test_func,
            description="Returns None",
            signature=sig,
            param_schema={},
        )

        result = self.executor.execute_probe("none_probe", 5)
        assert result is None

    def test_execute_probe_with_exception(self):
        """Test that exceptions in probe functions are propagated."""

        def test_func(x: int) -> int:
            raise ValueError("Test error")

        sig = signature(test_func)
        probe_registry.register(
            id="error_probe",
            fun=test_func,
            description="Raises error",
            signature=sig,
            param_schema={},
        )

        with pytest.raises(ValueError, match="Test error"):
            self.executor.execute_probe("error_probe", 5)

    @pytest.mark.asyncio
    async def test_async_execute_probe_async_function(self):
        """Test asynchronously executing an async probe function."""

        async def async_func(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        sig = signature(async_func)
        probe_registry.register(
            id="async_probe",
            fun=async_func,
            description="Async probe",
            signature=sig,
            param_schema={},
        )

        result = await self.executor.async_execute_probe("async_probe", 5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_async_execute_probe_sync_function(self):
        """Test asynchronously executing a sync probe function (runs in executor)."""

        def sync_func(x: int) -> int:
            return x * 3

        sig = signature(sync_func)
        probe_registry.register(
            id="sync_probe",
            fun=sync_func,
            description="Sync probe",
            signature=sig,
            param_schema={},
        )

        result = await self.executor.async_execute_probe("sync_probe", 5)
        assert result == 15

    @pytest.mark.asyncio
    async def test_async_execute_probe_not_found(self):
        """Test async execution of non-existent probe raises KeyError."""
        with pytest.raises(KeyError, match="Probe with ID 'nonexistent' not found"):
            await self.executor.async_execute_probe("nonexistent", 1)

    @pytest.mark.asyncio
    async def test_async_execute_probe_with_kwargs(self):
        """Test async execution with keyword arguments."""

        async def async_func(x: int, y: int = 5) -> int:
            return x + y

        sig = signature(async_func)
        probe_registry.register(
            id="async_kwargs_probe",
            fun=async_func,
            description="Async with kwargs",
            signature=sig,
            param_schema={},
        )

        result = await self.executor.async_execute_probe(
            "async_kwargs_probe", x=10, y=20
        )
        assert result == 30

    def test_execute_probe_with_complex_return_types(self):
        """Test executing a probe that returns complex types."""

        def test_func(items: list) -> dict:
            return {"count": len(items), "items": items}

        sig = signature(test_func)
        probe_registry.register(
            id="complex_probe",
            fun=test_func,
            description="Returns complex type",
            signature=sig,
            param_schema={},
        )

        result = self.executor.execute_probe("complex_probe", [1, 2, 3])
        assert result == {"count": 3, "items": [1, 2, 3]}
