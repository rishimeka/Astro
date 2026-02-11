"""StarType enum - defines the execution pattern for each Star."""

from enum import Enum


class StarType(str, Enum):
    """Execution pattern for a Star."""

    PLANNING = "planning"
    EXECUTION = "execution"
    DOCEX = "docex"
    EVAL = "eval"
    WORKER = "worker"
    SYNTHESIS = "synthesis"
