"""Exceptions for the executor module."""


class ParallelExecutionError(Exception):
    """Raised when one or more nodes fail during parallel execution.

    Attributes:
        message: Summary error message.
        errors: List of individual exceptions from failed nodes.
    """

    def __init__(self, message: str, errors: list[Exception]) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors

    def __str__(self) -> str:
        error_details = "\n".join(f"  - {type(e).__name__}: {e}" for e in self.errors)
        return f"{self.message}\n{error_details}"


class ExecutionError(Exception):
    """General execution error."""

    pass


class RunNotFoundError(Exception):
    """Raised when a run cannot be found."""

    pass


class PermissionDeniedError(Exception):
    """Raised when a tool call is denied due to probe scoping.

    The tool exists globally in the ProbeRegistry but is not permitted
    for the current star/directive context.

    Attributes:
        tool_name: Name of the denied tool.
        star_name: Name of the star that attempted the call.
    """

    def __init__(self, tool_name: str, star_name: str = "") -> None:
        self.tool_name = tool_name
        self.star_name = star_name
        super().__init__(
            f"Permission denied: tool '{tool_name}' exists but is not permitted "
            f"for star '{star_name}'"
        )


class ExecutionPausedException(Exception):
    """Raised when execution pauses for human-in-the-loop confirmation.

    This is a control flow exception, not an error. It signals that
    execution should halt gracefully without marking the run as failed.

    Attributes:
        run_id: The ID of the paused run.
        node_id: The ID of the node awaiting confirmation.
    """

    def __init__(self, run_id: str, node_id: str) -> None:
        self.run_id = run_id
        self.node_id = node_id
        super().__init__(f"Execution paused at node '{node_id}' awaiting confirmation")
