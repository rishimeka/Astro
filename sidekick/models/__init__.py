"""Sidekick data models for events and traces."""

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
]
