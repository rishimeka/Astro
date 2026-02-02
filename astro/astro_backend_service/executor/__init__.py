"""Executor module - constellation execution engine.

The executor handles running constellations, including:
- Traversing the DAG in topological order
- Executing Stars with proper context
- Managing parallel execution with retry logic
- Enforcing loop limits for EvalStar cycles
- Human-in-the-loop confirmation pause/resume

Example:
    from astro_backend_service.executor import ConstellationRunner, ExecutionContext, Run

    runner = ConstellationRunner(foundry)
    run = await runner.run(
        constellation_id="company_analysis",
        variables={"company_name": "Tesla"},
        original_query="Analyze Tesla's financials"
    )
    print(f"Status: {run.status}, Output: {run.final_output}")
"""

from astro_backend_service.executor.context import ExecutionContext, WorkerContext
from astro_backend_service.executor.events import (
    AnyStreamEvent,
    LogEvent,
    NodeCompletedEvent,
    NodeFailedEvent,
    NodeStartedEvent,
    ProgressEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunPausedEvent,
    RunStartedEvent,
    StreamEvent,
    ThoughtEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    truncate_output,
)
from astro_backend_service.executor.exceptions import (
    ExecutionError,
    ParallelExecutionError,
    RunNotFoundError,
)
from astro_backend_service.executor.run import (
    NodeOutput,
    Run,
    RunStatus,
    ToolCallRecord,
)
from astro_backend_service.executor.runner import ConstellationRunner
from astro_backend_service.executor.stream import (
    AsyncQueueStream,
    BufferedStream,
    CallbackStream,
    CompositeStream,
    ExecutionStream,
    LoggingStream,
    NoOpStream,
    serialize_event_dict,
    serialize_event_for_sse,
)

__all__ = [
    # Runner
    "ConstellationRunner",
    # Context
    "ExecutionContext",
    "WorkerContext",
    # Run models
    "Run",
    "NodeOutput",
    "RunStatus",
    "ToolCallRecord",
    # Stream events
    "StreamEvent",
    "AnyStreamEvent",
    "RunStartedEvent",
    "RunCompletedEvent",
    "RunFailedEvent",
    "RunPausedEvent",
    "NodeStartedEvent",
    "NodeCompletedEvent",
    "NodeFailedEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ThoughtEvent",
    "TokenEvent",
    "ProgressEvent",
    "LogEvent",
    "truncate_output",
    # Stream handlers
    "ExecutionStream",
    "AsyncQueueStream",
    "CallbackStream",
    "CompositeStream",
    "NoOpStream",
    "LoggingStream",
    "BufferedStream",
    "serialize_event_for_sse",
    "serialize_event_dict",
    # Exceptions
    "ParallelExecutionError",
    "ExecutionError",
    "RunNotFoundError",
]
