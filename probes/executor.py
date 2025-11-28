from probes.registry import probe_registry
import asyncio


class ProbeExecutor:
    def execute_probe(self, probe_id: str, *args, **kwargs):
        """Execute a registered probe by its ID with the given arguments.

        Args:
            probe_id: The unique identifier of the probe to execute
            *args: Positional arguments to pass to the probe function
            **kwargs: Keyword arguments to pass to the probe function

        Returns:
            The result of the probe function execution

        Raises:
            KeyError: If the probe ID is not found in the registry
        """
        probe_entry = probe_registry.get_probe(probe_id)
        if not probe_entry:
            raise KeyError(f"Probe with ID '{probe_id}' not found.")

        probe_function = probe_entry["function"]
        return probe_function(*args, **kwargs)

    async def async_execute_probe(self, probe_id: str, *args, **kwargs):
        """Asynchronously execute a registered probe by its ID with the given arguments.

        Args:
            probe_id: The unique identifier of the probe to execute
            *args: Positional arguments to pass to the probe function
            **kwargs: Keyword arguments to pass to the probe function

        Returns:
            The result of the probe function execution

        Raises:
            KeyError: If the probe ID is not found in the registry
        """
        probe_entry = probe_registry.get_probe(probe_id)
        if not probe_entry:
            raise KeyError(f"Probe with ID '{probe_id}' not found.")

        probe_function = probe_entry["function"]

        if asyncio.iscoroutinefunction(probe_function):
            return asyncio.run(probe_function(*args, **kwargs))
        else:
            # If the function is not async, run it in a thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, probe_function, *args, **kwargs)
