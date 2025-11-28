"""Probe decorator for registering functions as probes.

This module provides a decorator that registers functions as probes in the
probe registry, making them discoverable and callable through the probe system.
"""

from functools import wraps
from inspect import getdoc
from probes.registry import probe_registry
from probes.introspection import build_probe_metadata


def probe(id: str, description: str):
    """Decorator to register a function as a probe.

    Args:
        id: Unique identifier for the probe
        description: Human-readable description of what the probe does.
                    Can be empty if the function has a docstring.

    Returns:
        Decorated function registered in the probe registry

    Raises:
        ValueError: If neither description nor function docstring is provided
    """

    def decorator(fn):
        if not description and not getdoc(fn):
            raise ValueError(
                f"Probe '{id}' must have a description either in the decorator or in the docstring."
            )
        final_description = description or getdoc(fn)

        # Build comprehensive probe metadata
        metadata = build_probe_metadata(fn, id, final_description)

        probe_registry.register(
            id=id,
            fun=fn,
            description=final_description,
            signature=metadata["signature"],
            param_schema=metadata["param_schema"],
            return_schema=metadata["return_schema"],
        )

        print(f"Registered probe: {id} - {final_description}")

        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    return decorator
