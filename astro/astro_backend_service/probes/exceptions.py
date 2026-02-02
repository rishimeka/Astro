"""Exceptions for the probes module."""


class DuplicateProbeError(Exception):
    """Raised when attempting to register a probe with a duplicate name.

    The error message includes the locations of both the existing and
    duplicate probe definitions to help with debugging.
    """

    pass
