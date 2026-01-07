"""Enhanced Probe Executor for the Execution Engine.

This module provides probe execution with permission checking,
timeout handling, and rate limiting.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from probes import ProbeRegistry
from probes.executor import ProbeExecutor as BaseProbeExecutor
from execution.models.state import ToolCallRecord

logger = logging.getLogger(__name__)


class ProbePermissionError(Exception):
    """Raised when a Probe is called without permission."""

    pass


class ProbeExecutionError(Exception):
    """Raised when a Probe execution fails."""

    pass


class ProbeTimeoutError(ProbeExecutionError):
    """Raised when a Probe execution times out."""

    pass


class ExecutionProbeExecutor:
    """Enhanced Probe Executor with permission checking and timeouts.

    Wraps the existing ProbeExecutor and adds:
    - Permission checking against authorized probe lists
    - Configurable timeouts
    - Rate limiting support
    - Detailed execution records
    """

    def __init__(
        self,
        probe_registry: ProbeRegistry,
        default_timeout: float = 30.0,
    ):
        """Initialize the execution probe executor.

        Args:
            probe_registry: The ProbeRegistry containing available probes
            default_timeout: Default timeout in seconds for probe execution
        """
        self._registry = probe_registry
        self._base_executor = BaseProbeExecutor()
        self._default_timeout = default_timeout
        self._rate_limiters: Dict[str, asyncio.Semaphore] = {}

    @property
    def registry(self) -> ProbeRegistry:
        """Get the underlying probe registry."""
        return self._registry

    def setup_rate_limit(self, probe_id: str, max_concurrent: int) -> None:
        """Set up rate limiting for a specific probe.

        Args:
            probe_id: The ID of the probe
            max_concurrent: Maximum concurrent executions allowed
        """
        self._rate_limiters[probe_id] = asyncio.Semaphore(max_concurrent)

    async def execute(
        self,
        probe_id: str,
        arguments: Dict[str, Any],
        authorized_probes: List[str],
        timeout: Optional[float] = None,
    ) -> str:
        """Execute a Probe with permission checking.

        Args:
            probe_id: The Probe to execute
            arguments: Arguments to pass to the Probe
            authorized_probes: List of Probe IDs the caller is authorized to use
            timeout: Optional timeout override

        Returns:
            The Probe's result as a string

        Raises:
            ProbePermissionError: If caller isn't authorized for this Probe
            ProbeExecutionError: If the Probe execution fails
            ProbeTimeoutError: If the Probe execution times out
        """
        # Permission check
        if probe_id not in authorized_probes:
            raise ProbePermissionError(
                f"Probe '{probe_id}' is not authorized. "
                f"Available probes: {authorized_probes}"
            )

        # Get Probe metadata
        probe_meta = self._registry.get_probe(probe_id)
        if not probe_meta:
            raise ProbeExecutionError(f"Probe not found: {probe_id}")

        # Determine timeout
        exec_timeout = timeout or self._default_timeout

        # Check for rate limiter
        rate_limiter = self._rate_limiters.get(probe_id)

        if rate_limiter:
            async with rate_limiter:
                return await self._execute_with_timeout(
                    probe_id, arguments, exec_timeout
                )
        else:
            return await self._execute_with_timeout(probe_id, arguments, exec_timeout)

    async def _execute_with_timeout(
        self,
        probe_id: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> str:
        """Execute probe with timeout handling.

        Args:
            probe_id: The Probe to execute
            arguments: Arguments to pass to the Probe
            timeout: Timeout in seconds

        Returns:
            The Probe's result as a string
        """
        try:
            result = await asyncio.wait_for(
                self._base_executor.async_execute_probe(probe_id, **arguments),
                timeout=timeout,
            )
            return str(result) if result is not None else ""

        except asyncio.TimeoutError:
            raise ProbeTimeoutError(f"Probe '{probe_id}' timed out after {timeout}s")
        except KeyError as e:
            raise ProbeExecutionError(f"Probe not found: {e}")
        except Exception as e:
            raise ProbeExecutionError(f"Probe '{probe_id}' failed: {str(e)}")

    async def execute_with_record(
        self,
        probe_id: str,
        arguments: Dict[str, Any],
        authorized_probes: List[str],
        timeout: Optional[float] = None,
        tool_call_id: Optional[str] = None,
    ) -> ToolCallRecord:
        """Execute a Probe and return a detailed record.

        Args:
            probe_id: The Probe to execute
            arguments: Arguments to pass to the Probe
            authorized_probes: List of Probe IDs the caller is authorized to use
            timeout: Optional timeout override
            tool_call_id: Optional ID for the tool call record

        Returns:
            ToolCallRecord with execution details
        """
        import uuid

        probe_meta = self._registry.get_probe(probe_id)
        probe_name = probe_meta["id"] if probe_meta else probe_id

        record = ToolCallRecord(
            tool_call_id=tool_call_id or str(uuid.uuid4()),
            probe_id=probe_id,
            probe_name=probe_name,
            arguments=arguments,
        )

        start_time = datetime.utcnow()

        try:
            result = await self.execute(
                probe_id=probe_id,
                arguments=arguments,
                authorized_probes=authorized_probes,
                timeout=timeout,
            )

            record.result = result
            record.success = True

        except ProbePermissionError as e:
            record.success = False
            record.error = str(e)

        except ProbeTimeoutError as e:
            record.success = False
            record.error = str(e)

        except ProbeExecutionError as e:
            record.success = False
            record.error = str(e)

        except Exception as e:
            record.success = False
            record.error = f"Unexpected error: {str(e)}"

        finally:
            end_time = datetime.utcnow()
            record.latency_ms = int((end_time - start_time).total_seconds() * 1000)
            record.timestamp = start_time

        return record

    def get_tools_schema(self, authorized_probes: List[str]) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tools schema for authorized Probes.

        Args:
            authorized_probes: List of probe IDs to include

        Returns:
            List of tool definitions in OpenAI format
        """
        tools = []

        for probe_id in authorized_probes:
            probe_meta = self._registry.get_probe(probe_id)
            if not probe_meta:
                continue

            # Build OpenAI tool schema
            tool = {
                "type": "function",
                "function": {
                    "name": probe_id,
                    "description": probe_meta.get("description", ""),
                    "parameters": probe_meta.get(
                        "param_schema",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }

            tools.append(tool)

        return tools

    def get_langchain_tools(self, authorized_probes: List[str]) -> List[Any]:
        """Get LangChain tool objects for authorized Probes.

        Args:
            authorized_probes: List of probe IDs to include

        Returns:
            List of LangChain tool objects
        """
        from langchain.tools import StructuredTool

        tools = []

        for probe_id in authorized_probes:
            probe_meta = self._registry.get_probe(probe_id)
            if not probe_meta:
                continue

            # Get the original function
            probe_func = probe_meta.get("function")
            if not probe_func:
                continue

            # Create a LangChain StructuredTool
            tool = StructuredTool.from_function(
                func=probe_func,
                name=probe_id,
                description=probe_meta.get("description", ""),
            )

            tools.append(tool)

        return tools

    def list_probes(self) -> List[str]:
        """Get a list of all available probe IDs.

        Returns:
            List of probe IDs
        """
        return self._registry.list_probes()

    def get_probe_info(self, probe_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific probe.

        Args:
            probe_id: The ID of the probe

        Returns:
            Probe metadata dictionary if found, None otherwise
        """
        return self._registry.get_probe(probe_id)
