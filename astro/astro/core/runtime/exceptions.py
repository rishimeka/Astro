"""Exceptions for the executor module."""

from typing import List


class ParallelExecutionError(Exception):
    """Raised when one or more nodes fail during parallel execution.

    Attributes:
        message: Summary error message.
        errors: List of individual exceptions from failed nodes.
    """

    def __init__(self, message: str, errors: List[Exception]) -> None:
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
