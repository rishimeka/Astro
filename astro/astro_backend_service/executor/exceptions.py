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
