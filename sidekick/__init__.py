"""Sidekick: Execution Observability and Tracing System.

Sidekick is a parallel observability system that captures structured execution
traces during agentic workflow runs. It operates as a non-blocking observer,
recording what happened, why decisions were made, and what each component produced.

Key design principle: Sidekick is a passive observer. It never modifies
execution flow, never blocks on logging operations, and fails silently
rather than crashing the main workflow.
"""

from sidekick.models.events import (
    EventType,
    SidekickEvent,
    ExecutionStartedPayload,
    ExecutionCompletedPayload,
    ExecutionFailedPayload,
    PhaseStartedPayload,
    PhaseCompletedPayload,
    PhaseFailedPayload,
    WorkerStartedPayload,
    WorkerLLMCallPayload,
    WorkerLLMResponsePayload,
    WorkerToolCallPayload,
    WorkerToolResponsePayload,
    WorkerCompletedPayload,
    WorkerFailedPayload,
    StarLoadedPayload,
    StarInjectedPayload,
)
from sidekick.models.traces import (
    ToolCall,
    WorkerTrace,
    PhaseTrace,
    ExecutionTrace,
)
from sidekick.client import SidekickClient
from sidekick.processor import SidekickProcessor
from sidekick.persistence import SidekickPersistence
from sidekick.callback import SidekickCallback
from sidekick.config import SidekickConfig

__all__ = [
    # Event types
    "EventType",
    "SidekickEvent",
    "ExecutionStartedPayload",
    "ExecutionCompletedPayload",
    "ExecutionFailedPayload",
    "PhaseStartedPayload",
    "PhaseCompletedPayload",
    "PhaseFailedPayload",
    "WorkerStartedPayload",
    "WorkerLLMCallPayload",
    "WorkerLLMResponsePayload",
    "WorkerToolCallPayload",
    "WorkerToolResponsePayload",
    "WorkerCompletedPayload",
    "WorkerFailedPayload",
    "StarLoadedPayload",
    "StarInjectedPayload",
    # Trace models
    "ToolCall",
    "WorkerTrace",
    "PhaseTrace",
    "ExecutionTrace",
    # Core components
    "SidekickClient",
    "SidekickProcessor",
    "SidekickPersistence",
    "SidekickCallback",
    "SidekickConfig",
]
