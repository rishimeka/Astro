"""Probe registry for managing registered probe functions.

This module provides the ProbeRegistry class which stores and manages
all registered probe functions in the system.
"""

from probes.introspection import schema_for_planner


class ProbeRegistry:
    """Registry for storing and retrieving probe functions.

    The registry maintains a mapping of probe IDs to their metadata including
    the function reference, description, and signature.
    """

    def __init__(self):
        """Initialize an empty probe registry."""
        self._probes = {}

    def register(
        self, id, fun, description, signature, param_schema, return_schema=None
    ):
        """Register a new probe function.

        Args:
            id: Unique identifier for the probe
            fun: The function to register
            description: Description of what the probe does
            signature: Function signature information
            param_schema: JSON schema for the function's parameters
            return_schema: Optional JSON schema for the function's return type
        """
        self._probes[id] = {
            "id": id,
            "function": fun,
            "description": description,
            "signature": signature,
            "param_schema": param_schema,
            "return_schema": return_schema,
        }

    def get_probe(self, id):
        """Retrieve a specific probe by its ID.

        Args:
            id: The unique identifier of the probe

        Returns:
            Probe metadata dictionary if found, None otherwise
        """
        return self._probes.get(id)

    def list_probes(self):
        """Get a list of all registered probe IDs.

        Returns:
            List of probe IDs
        """
        return list(self._probes.keys())

    def get_multiple(self, ids):
        """Retrieve multiple probes by their IDs.

        Args:
            ids: Iterable of probe IDs to retrieve

        Returns:
            Dictionary mapping probe IDs to their metadata for probes that exist
        """
        return {id: self._probes[id] for id in ids if id in self._probes}

    def get_all(self):
        """Get all registered probes.

        Returns:
            Dictionary mapping probe IDs to their metadata
        """
        return self._probes

    def get_planner_schemas(self, ids=None):
        """
        Retrieve probe schemas formatted for the Planner.
        Args:
            ids: Optional iterable of probe IDs to retrieve. If None, retrieves all probes.
        Returns:
            Dictionary mapping probe IDs to their Planner-formatted schemas
        """
        if ids is None:
            # all probes
            return {k: schema_for_planner(v) for k, v in self._probes.items()}
        else:
            return {
                i: schema_for_planner(self._probes[i]) for i in ids if i in self._probes
            }


# Module-level registry instance used by the `probe` decorator and other modules
probe_registry = ProbeRegistry()
