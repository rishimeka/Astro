"""Runtime infrastructure for Astro V2.

This module exports execution context, events, streaming, and exceptions
for the runtime layer.
"""

from astro.core.runtime.context import ExecutionContext

# Note: events, stream, and exceptions will be imported when needed
# to avoid circular dependencies

__all__ = [
    "ExecutionContext",
]
