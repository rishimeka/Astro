# Sidekick: Execution Observability and Tracing System

## Architecture Specification v0.1

---

## 1. Purpose and Value Proposition

Sidekick is a parallel observability system that captures structured execution traces during agentic workflow runs. It operates as a non-blocking observer, recording what happened, why decisions were made, and what each component produced.

**Core value prop**: "Complete visibility into what your agents did and why, without modifying your execution code."

**What Sidekick provides**:
1. Real-time execution tracing with minimal performance overhead
2. Structured, queryable logs for debugging and auditing
3. Input data for Nebula's optimization engine
4. Human-readable execution summaries for observability dashboards

**Key design principle**: Sidekick is a passive observer. It never modifies execution flow, never blocks on logging operations, and fails silently rather than crashing the main workflow.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MAIN EXECUTION THREAD                             │
│                                                                             │
│  ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐                │
│  │ Planning │───▶│Execution│───▶│Evaluation│───▶│Synthesis │                │
│  └────┬─────┘    └────┬────┘    └────┬─────┘    └────┬─────┘                │
│       │               │               │               │                     │
│       │ emit          │ emit          │ emit          │ emit                │
│       ▼               ▼               ▼               ▼                     │
└───────┼───────────────┼───────────────┼───────────────┼─────────────────────┘
        │               │               │               │
        │   ┌───────────┴───────────────┴───────────────┘
        │   │
        ▼   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SIDEKICK                                       │
│                        (Parallel Thread/Process)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐                                                       │
│  │   Event Queue    │  (Thread-safe, non-blocking)                          │
│  │   (asyncio.Queue │                                                       │
│  │    or similar)   │                                                       │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │  Event Processor │                                                       │
│  │                  │                                                       │
│  │  - Aggregates    │                                                       │
│  │    events into   │                                                       │
│  │    traces        │                                                       │
│  │  - Maintains     │                                                       │
│  │    state         │                                                       │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                              │
│  │  Trace Builder   │────▶│   Persistence    │                              │
│  │                  │     │   (MongoDB)      │                              │
│  │  - Structures    │     │                  │                              │
│  │    data          │     │  - Async writes  │                              │
│  │  - Validates     │     │  - Batch inserts │                              │
│  │    completeness  │     │  - Retry logic   │                              │
│  └──────────────────┘     └──────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Concepts

### 3.1 Events vs Traces

**Events**: Individual occurrences emitted by the execution code. Examples:
- "Worker started"
- "Tool called"
- "LLM response received"
- "Phase completed"

**Traces**: Aggregated, structured records built from events. A single execution run produces one `ExecutionTrace` containing multiple `PhaseTrace` objects, each containing multiple `WorkerTrace` objects.

### 3.2 Event Types

```python
class EventType(str, Enum):
    # Execution-level events
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    
    # Phase-level events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    
    # Worker-level events
    WORKER_STARTED = "worker_started"
    WORKER_LLM_CALL = "worker_llm_call"
    WORKER_LLM_RESPONSE = "worker_llm_response"
    WORKER_TOOL_CALL = "worker_tool_call"
    WORKER_TOOL_RESPONSE = "worker_tool_response"
    WORKER_COMPLETED = "worker_completed"
    WORKER_FAILED = "worker_failed"
    
    # Star-level events (prompt tracking)
    STAR_LOADED = "star_loaded"
    STAR_INJECTED = "star_injected"
```

### 3.3 Non-Blocking Guarantee

Sidekick must NEVER slow down or block the main execution. This is achieved through:

1. **Fire-and-forget event emission**: Main thread puts events on queue and immediately continues
2. **Bounded queue with drop policy**: If queue is full, drop oldest events rather than blocking
3. **Async persistence**: Database writes happen asynchronously
4. **Silent failure**: If Sidekick crashes, main execution continues unaffected

---

## 4. Data Models

### 4.1 Event Schema

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid

class EventType(str, Enum):
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    WORKER_STARTED = "worker_started"
    WORKER_LLM_CALL = "worker_llm_call"
    WORKER_LLM_RESPONSE = "worker_llm_response"
    WORKER_TOOL_CALL = "worker_tool_call"
    WORKER_TOOL_RESPONSE = "worker_tool_response"
    WORKER_COMPLETED = "worker_completed"
    WORKER_FAILED = "worker_failed"
    STAR_LOADED = "star_loaded"
    STAR_INJECTED = "star_injected"


class SidekickEvent(BaseModel):
    """A single event emitted during execution."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Hierarchy identifiers (for aggregation)
    trace_id: str  # Execution-level ID
    phase_id: Optional[str] = None  # Phase-level ID (if applicable)
    worker_id: Optional[str] = None  # Worker-level ID (if applicable)
    
    # Event payload (varies by event type)
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
```

### 4.2 Event Payloads by Type

```python
# EXECUTION_STARTED payload
class ExecutionStartedPayload(BaseModel):
    original_query: str
    stars_used: List[str]  # Star IDs loaded for this execution
    probes_available: List[str]  # Probe IDs available
    config: Dict[str, Any]  # Execution configuration


# EXECUTION_COMPLETED payload
class ExecutionCompletedPayload(BaseModel):
    final_output: str
    total_duration_seconds: float
    total_llm_calls: int
    total_tool_calls: int
    total_tokens_used: Optional[int] = None


# EXECUTION_FAILED payload
class ExecutionFailedPayload(BaseModel):
    error_message: str
    error_type: str
    stack_trace: Optional[str] = None
    partial_output: Optional[str] = None


# PHASE_STARTED payload
class PhaseStartedPayload(BaseModel):
    phase_name: str
    phase_description: str
    planned_workers: int
    phase_index: int  # 1-indexed position in execution


# PHASE_COMPLETED payload
class PhaseCompletedPayload(BaseModel):
    phase_name: str
    duration_seconds: float
    workers_completed: int
    workers_failed: int


# PHASE_FAILED payload
class PhaseFailedPayload(BaseModel):
    phase_name: str
    error_message: str
    workers_completed: int
    workers_failed: int


# WORKER_STARTED payload
class WorkerStartedPayload(BaseModel):
    worker_name: str
    task_description: str
    star_id: str  # Which Star's prompt is being used
    star_version: str
    input_context: str  # What the worker received as input
    expected_output_format: str
    tools_available: List[str]  # Probe IDs this worker can use


# WORKER_LLM_CALL payload
class WorkerLLMCallPayload(BaseModel):
    messages: List[Dict[str, Any]]  # Full message history sent to LLM
    model: str
    temperature: float
    iteration: int  # Which iteration of the worker loop


# WORKER_LLM_RESPONSE payload
class WorkerLLMResponsePayload(BaseModel):
    response_content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None  # If LLM requested tool calls
    tokens_used: Optional[int] = None
    latency_ms: int
    iteration: int


# WORKER_TOOL_CALL payload
class WorkerToolCallPayload(BaseModel):
    tool_name: str
    tool_args: Dict[str, Any]
    tool_call_id: str
    iteration: int


# WORKER_TOOL_RESPONSE payload
class WorkerToolResponsePayload(BaseModel):
    tool_name: str
    tool_call_id: str
    result: str
    success: bool
    error: Optional[str] = None
    latency_ms: int
    iteration: int


# WORKER_COMPLETED payload
class WorkerCompletedPayload(BaseModel):
    worker_name: str
    final_output: str
    total_iterations: int
    total_tool_calls: int
    duration_seconds: float


# WORKER_FAILED payload
class WorkerFailedPayload(BaseModel):
    worker_name: str
    error_message: str
    error_type: str
    iterations_completed: int
    partial_output: Optional[str] = None


# STAR_LOADED payload
class StarLoadedPayload(BaseModel):
    star_id: str
    star_name: str
    star_version: str
    content_hash: str  # For detecting changes
    probes: List[str]


# STAR_INJECTED payload
class StarInjectedPayload(BaseModel):
    star_id: str
    worker_id: str
    injection_type: str  # "system_prompt", "nudge", etc.
    injected_content: str  # The actual prompt content used
```

### 4.3 Trace Schema (Aggregated Output)

These match the Nebula input schema exactly:

```python
class ToolCall(BaseModel):
    """Record of a single tool invocation."""
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: str
    success: bool
    error: Optional[str] = None
    latency_ms: int
    timestamp: datetime


class WorkerTrace(BaseModel):
    """Complete trace for a single worker execution."""
    worker_id: str
    worker_name: str
    star_id: str
    star_version: str
    task_description: str
    input_context: str
    expected_output_format: str
    
    # Full conversation history
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Tool usage
    tool_calls: List[ToolCall] = Field(default_factory=list)
    
    # Outcome
    final_output: str = ""
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: Optional[str] = None
    
    # Metrics
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tokens_used: Optional[int] = None
    duration_seconds: float = 0.0
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PhaseTrace(BaseModel):
    """Complete trace for a phase execution."""
    phase_id: str
    phase_name: str
    phase_description: str
    phase_index: int
    
    # Workers in this phase
    workers: List[WorkerTrace] = Field(default_factory=list)
    
    # Outcome
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: Optional[str] = None
    
    # Metrics
    workers_completed: int = 0
    workers_failed: int = 0
    duration_seconds: float = 0.0
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionTrace(BaseModel):
    """Complete trace for an entire execution run."""
    trace_id: str
    timestamp: datetime
    
    # Query
    original_query: str
    
    # Stars used
    stars_used: Dict[str, str] = Field(default_factory=dict)  # star_id -> version
    
    # Phases
    phases: List[PhaseTrace] = Field(default_factory=list)
    
    # Final outcome
    final_output: str = ""
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: Optional[str] = None
    
    # Aggregate metrics
    total_phases: int = 0
    total_workers: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens_used: Optional[int] = None
    total_duration_seconds: float = 0.0
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

---

## 5. System Components

### 5.1 Sidekick Client (Emitter)

The client is what execution code uses to emit events. It must be:
- Thread-safe
- Non-blocking
- Singleton per execution

```python
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
import uuid

class SidekickClient:
    """
    Client for emitting events to Sidekick.
    
    Usage:
        async with SidekickClient.create(query="...") as sidekick:
            sidekick.emit_phase_started(...)
            # ... execution code ...
    """
    
    _instance: Optional["SidekickClient"] = None
    
    def __init__(
        self,
        trace_id: str,
        original_query: str,
        queue: asyncio.Queue,
        max_queue_size: int = 10000
    ):
        self.trace_id = trace_id
        self.original_query = original_query
        self._queue = queue
        self._max_queue_size = max_queue_size
        self._current_phase_id: Optional[str] = None
        self._current_worker_id: Optional[str] = None
    
    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        original_query: str,
        stars_used: List[str],
        probes_available: List[str],
        config: Dict[str, Any] = None
    ):
        """
        Create a Sidekick client for an execution run.
        Starts the background processor and cleans up on exit.
        """
        trace_id = str(uuid.uuid4())
        queue = asyncio.Queue(maxsize=10000)
        
        client = cls(
            trace_id=trace_id,
            original_query=original_query,
            queue=queue
        )
        cls._instance = client
        
        # Start background processor
        processor = SidekickProcessor(queue, trace_id)
        processor_task = asyncio.create_task(processor.run())
        
        # Emit execution started
        client.emit_execution_started(
            stars_used=stars_used,
            probes_available=probes_available,
            config=config or {}
        )
        
        try:
            yield client
        finally:
            # Signal processor to stop
            await queue.put(None)  # Sentinel value
            await processor_task
            cls._instance = None
    
    @classmethod
    def get(cls) -> Optional["SidekickClient"]:
        """Get the current Sidekick client instance."""
        return cls._instance
    
    def _emit(self, event_type: EventType, payload: Dict[str, Any]):
        """
        Emit an event to the queue.
        Non-blocking: drops event if queue is full.
        """
        event = SidekickEvent(
            event_type=event_type,
            trace_id=self.trace_id,
            phase_id=self._current_phase_id,
            worker_id=self._current_worker_id,
            payload=payload
        )
        
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop event rather than blocking
            # Could log this to a separate error stream
            pass
    
    # ==================== Execution-level events ====================
    
    def emit_execution_started(
        self,
        stars_used: List[str],
        probes_available: List[str],
        config: Dict[str, Any]
    ):
        self._emit(EventType.EXECUTION_STARTED, {
            "original_query": self.original_query,
            "stars_used": stars_used,
            "probes_available": probes_available,
            "config": config
        })
    
    def emit_execution_completed(
        self,
        final_output: str,
        total_duration_seconds: float,
        total_llm_calls: int,
        total_tool_calls: int,
        total_tokens_used: Optional[int] = None
    ):
        self._emit(EventType.EXECUTION_COMPLETED, {
            "final_output": final_output,
            "total_duration_seconds": total_duration_seconds,
            "total_llm_calls": total_llm_calls,
            "total_tool_calls": total_tool_calls,
            "total_tokens_used": total_tokens_used
        })
    
    def emit_execution_failed(
        self,
        error_message: str,
        error_type: str,
        stack_trace: Optional[str] = None,
        partial_output: Optional[str] = None
    ):
        self._emit(EventType.EXECUTION_FAILED, {
            "error_message": error_message,
            "error_type": error_type,
            "stack_trace": stack_trace,
            "partial_output": partial_output
        })
    
    # ==================== Phase-level events ====================
    
    @asynccontextmanager
    async def phase(
        self,
        phase_name: str,
        phase_description: str,
        planned_workers: int,
        phase_index: int
    ):
        """Context manager for tracking a phase."""
        phase_id = str(uuid.uuid4())
        self._current_phase_id = phase_id
        
        self._emit(EventType.PHASE_STARTED, {
            "phase_name": phase_name,
            "phase_description": phase_description,
            "planned_workers": planned_workers,
            "phase_index": phase_index
        })
        
        start_time = datetime.utcnow()
        workers_completed = 0
        workers_failed = 0
        
        try:
            yield phase_id
        except Exception as e:
            self._emit(EventType.PHASE_FAILED, {
                "phase_name": phase_name,
                "error_message": str(e),
                "workers_completed": workers_completed,
                "workers_failed": workers_failed
            })
            raise
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._emit(EventType.PHASE_COMPLETED, {
                "phase_name": phase_name,
                "duration_seconds": duration,
                "workers_completed": workers_completed,
                "workers_failed": workers_failed
            })
            self._current_phase_id = None
    
    # ==================== Worker-level events ====================
    
    @asynccontextmanager
    async def worker(
        self,
        worker_name: str,
        task_description: str,
        star_id: str,
        star_version: str,
        input_context: str,
        expected_output_format: str,
        tools_available: List[str]
    ):
        """Context manager for tracking a worker."""
        worker_id = str(uuid.uuid4())
        self._current_worker_id = worker_id
        
        self._emit(EventType.WORKER_STARTED, {
            "worker_name": worker_name,
            "task_description": task_description,
            "star_id": star_id,
            "star_version": star_version,
            "input_context": input_context,
            "expected_output_format": expected_output_format,
            "tools_available": tools_available
        })
        
        start_time = datetime.utcnow()
        
        try:
            yield worker_id
        except Exception as e:
            self._emit(EventType.WORKER_FAILED, {
                "worker_name": worker_name,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "iterations_completed": 0,
                "partial_output": None
            })
            raise
        finally:
            self._current_worker_id = None
    
    def emit_worker_completed(
        self,
        worker_name: str,
        final_output: str,
        total_iterations: int,
        total_tool_calls: int,
        duration_seconds: float
    ):
        self._emit(EventType.WORKER_COMPLETED, {
            "worker_name": worker_name,
            "final_output": final_output,
            "total_iterations": total_iterations,
            "total_tool_calls": total_tool_calls,
            "duration_seconds": duration_seconds
        })
    
    def emit_worker_failed(
        self,
        worker_name: str,
        error_message: str,
        error_type: str,
        iterations_completed: int,
        partial_output: Optional[str] = None
    ):
        self._emit(EventType.WORKER_FAILED, {
            "worker_name": worker_name,
            "error_message": error_message,
            "error_type": error_type,
            "iterations_completed": iterations_completed,
            "partial_output": partial_output
        })
    
    # ==================== LLM events ====================
    
    def emit_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        iteration: int
    ):
        self._emit(EventType.WORKER_LLM_CALL, {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "iteration": iteration
        })
    
    def emit_llm_response(
        self,
        response_content: str,
        tool_calls: Optional[List[Dict[str, Any]]],
        tokens_used: Optional[int],
        latency_ms: int,
        iteration: int
    ):
        self._emit(EventType.WORKER_LLM_RESPONSE, {
            "response_content": response_content,
            "tool_calls": tool_calls,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "iteration": iteration
        })
    
    # ==================== Tool events ====================
    
    def emit_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_call_id: str,
        iteration: int
    ):
        self._emit(EventType.WORKER_TOOL_CALL, {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_call_id": tool_call_id,
            "iteration": iteration
        })
    
    def emit_tool_response(
        self,
        tool_name: str,
        tool_call_id: str,
        result: str,
        success: bool,
        latency_ms: int,
        iteration: int,
        error: Optional[str] = None
    ):
        self._emit(EventType.WORKER_TOOL_RESPONSE, {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "result": result,
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
            "iteration": iteration
        })
    
    # ==================== Star events ====================
    
    def emit_star_loaded(
        self,
        star_id: str,
        star_name: str,
        star_version: str,
        content_hash: str,
        probes: List[str]
    ):
        self._emit(EventType.STAR_LOADED, {
            "star_id": star_id,
            "star_name": star_name,
            "star_version": star_version,
            "content_hash": content_hash,
            "probes": probes
        })
    
    def emit_star_injected(
        self,
        star_id: str,
        worker_id: str,
        injection_type: str,
        injected_content: str
    ):
        self._emit(EventType.STAR_INJECTED, {
            "star_id": star_id,
            "worker_id": worker_id,
            "injection_type": injection_type,
            "injected_content": injected_content
        })
```

### 5.2 Sidekick Processor

The processor runs in the background, consuming events and building traces:

```python
class SidekickProcessor:
    """
    Background processor that consumes events and builds traces.
    """
    
    def __init__(self, queue: asyncio.Queue, trace_id: str):
        self._queue = queue
        self._trace_id = trace_id
        self._trace: Optional[ExecutionTrace] = None
        self._phases: Dict[str, PhaseTrace] = {}
        self._workers: Dict[str, WorkerTrace] = {}
        self._persistence = SidekickPersistence()
    
    async def run(self):
        """Main processing loop."""
        while True:
            event = await self._queue.get()
            
            # Sentinel value signals shutdown
            if event is None:
                break
            
            try:
                await self._process_event(event)
            except Exception as e:
                # Log error but don't crash
                print(f"Sidekick processor error: {e}")
            
            self._queue.task_done()
        
        # Final persistence on shutdown
        await self._finalize()
    
    async def _process_event(self, event: SidekickEvent):
        """Route event to appropriate handler."""
        handlers = {
            EventType.EXECUTION_STARTED: self._handle_execution_started,
            EventType.EXECUTION_COMPLETED: self._handle_execution_completed,
            EventType.EXECUTION_FAILED: self._handle_execution_failed,
            EventType.PHASE_STARTED: self._handle_phase_started,
            EventType.PHASE_COMPLETED: self._handle_phase_completed,
            EventType.PHASE_FAILED: self._handle_phase_failed,
            EventType.WORKER_STARTED: self._handle_worker_started,
            EventType.WORKER_LLM_CALL: self._handle_llm_call,
            EventType.WORKER_LLM_RESPONSE: self._handle_llm_response,
            EventType.WORKER_TOOL_CALL: self._handle_tool_call,
            EventType.WORKER_TOOL_RESPONSE: self._handle_tool_response,
            EventType.WORKER_COMPLETED: self._handle_worker_completed,
            EventType.WORKER_FAILED: self._handle_worker_failed,
            EventType.STAR_LOADED: self._handle_star_loaded,
            EventType.STAR_INJECTED: self._handle_star_injected,
        }
        
        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
    
    # ==================== Event Handlers ====================
    
    async def _handle_execution_started(self, event: SidekickEvent):
        payload = event.payload
        self._trace = ExecutionTrace(
            trace_id=self._trace_id,
            timestamp=event.timestamp,
            original_query=payload["original_query"],
            started_at=event.timestamp,
            status="running"
        )
        # Store star IDs (versions will be filled in by STAR_LOADED events)
        for star_id in payload.get("stars_used", []):
            self._trace.stars_used[star_id] = "unknown"
    
    async def _handle_execution_completed(self, event: SidekickEvent):
        if not self._trace:
            return
        
        payload = event.payload
        self._trace.final_output = payload["final_output"]
        self._trace.total_duration_seconds = payload["total_duration_seconds"]
        self._trace.total_llm_calls = payload["total_llm_calls"]
        self._trace.total_tool_calls = payload["total_tool_calls"]
        self._trace.total_tokens_used = payload.get("total_tokens_used")
        self._trace.completed_at = event.timestamp
        self._trace.status = "completed"
    
    async def _handle_execution_failed(self, event: SidekickEvent):
        if not self._trace:
            return
        
        payload = event.payload
        self._trace.error = payload["error_message"]
        self._trace.final_output = payload.get("partial_output", "")
        self._trace.completed_at = event.timestamp
        self._trace.status = "failed"
    
    async def _handle_phase_started(self, event: SidekickEvent):
        if not self._trace:
            return
        
        payload = event.payload
        phase = PhaseTrace(
            phase_id=event.phase_id,
            phase_name=payload["phase_name"],
            phase_description=payload["phase_description"],
            phase_index=payload["phase_index"],
            started_at=event.timestamp,
            status="running"
        )
        self._phases[event.phase_id] = phase
        self._trace.phases.append(phase)
        self._trace.total_phases += 1
    
    async def _handle_phase_completed(self, event: SidekickEvent):
        phase = self._phases.get(event.phase_id)
        if not phase:
            return
        
        payload = event.payload
        phase.duration_seconds = payload["duration_seconds"]
        phase.workers_completed = payload["workers_completed"]
        phase.workers_failed = payload["workers_failed"]
        phase.completed_at = event.timestamp
        phase.status = "completed"
    
    async def _handle_phase_failed(self, event: SidekickEvent):
        phase = self._phases.get(event.phase_id)
        if not phase:
            return
        
        payload = event.payload
        phase.error = payload["error_message"]
        phase.workers_completed = payload["workers_completed"]
        phase.workers_failed = payload["workers_failed"]
        phase.completed_at = event.timestamp
        phase.status = "failed"
    
    async def _handle_worker_started(self, event: SidekickEvent):
        phase = self._phases.get(event.phase_id)
        if not phase:
            return
        
        payload = event.payload
        worker = WorkerTrace(
            worker_id=event.worker_id,
            worker_name=payload["worker_name"],
            star_id=payload["star_id"],
            star_version=payload["star_version"],
            task_description=payload["task_description"],
            input_context=payload["input_context"],
            expected_output_format=payload["expected_output_format"],
            started_at=event.timestamp,
            status="running"
        )
        self._workers[event.worker_id] = worker
        phase.workers.append(worker)
        self._trace.total_workers += 1
    
    async def _handle_llm_call(self, event: SidekickEvent):
        worker = self._workers.get(event.worker_id)
        if not worker:
            return
        
        payload = event.payload
        # Store the messages for this iteration
        worker.messages = payload["messages"]
        self._trace.total_llm_calls += 1
    
    async def _handle_llm_response(self, event: SidekickEvent):
        worker = self._workers.get(event.worker_id)
        if not worker:
            return
        
        payload = event.payload
        # Append assistant response to messages
        worker.messages.append({
            "role": "assistant",
            "content": payload["response_content"],
            "tool_calls": payload.get("tool_calls")
        })
        
        if payload.get("tokens_used"):
            if worker.total_tokens_used is None:
                worker.total_tokens_used = 0
            worker.total_tokens_used += payload["tokens_used"]
        
        worker.total_iterations = payload["iteration"]
    
    async def _handle_tool_call(self, event: SidekickEvent):
        worker = self._workers.get(event.worker_id)
        if not worker:
            return
        
        # Tool call is recorded; result will come in TOOL_RESPONSE
        pass
    
    async def _handle_tool_response(self, event: SidekickEvent):
        worker = self._workers.get(event.worker_id)
        if not worker:
            return
        
        payload = event.payload
        tool_call = ToolCall(
            tool_name=payload["tool_name"],
            tool_args={},  # Args were in TOOL_CALL event
            tool_result=payload["result"],
            success=payload["success"],
            error=payload.get("error"),
            latency_ms=payload["latency_ms"],
            timestamp=event.timestamp
        )
        worker.tool_calls.append(tool_call)
        worker.total_tool_calls += 1
        self._trace.total_tool_calls += 1
    
    async def _handle_worker_completed(self, event: SidekickEvent):
        worker = self._workers.get(event.worker_id)
        if not worker:
            return
        
        payload = event.payload
        worker.final_output = payload["final_output"]
        worker.total_iterations = payload["total_iterations"]
        worker.total_tool_calls = payload["total_tool_calls"]
        worker.duration_seconds = payload["duration_seconds"]
        worker.completed_at = event.timestamp
        worker.status = "completed"
    
    async def _handle_worker_failed(self, event: SidekickEvent):
        worker = self._workers.get(event.worker_id)
        if not worker:
            return
        
        payload = event.payload
        worker.error = payload["error_message"]
        worker.total_iterations = payload["iterations_completed"]
        worker.final_output = payload.get("partial_output", "")
        worker.completed_at = event.timestamp
        worker.status = "failed"
    
    async def _handle_star_loaded(self, event: SidekickEvent):
        if not self._trace:
            return
        
        payload = event.payload
        self._trace.stars_used[payload["star_id"]] = payload["star_version"]
    
    async def _handle_star_injected(self, event: SidekickEvent):
        # Could store injection details if needed for debugging
        pass
    
    async def _finalize(self):
        """Save final trace to persistence."""
        if self._trace:
            await self._persistence.save_trace(self._trace)
```

### 5.3 Persistence Layer

```python
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os

class SidekickPersistence:
    """
    Persistence layer for Sidekick traces.
    Uses MongoDB with async writes.
    """
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
        self._traces_collection = None
    
    async def _ensure_connected(self):
        """Lazy connection to MongoDB."""
        if self._client is None:
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            db_name = os.getenv("SIDEKICK_DB", "astro")
            
            self._client = AsyncIOMotorClient(mongo_uri)
            self._db = self._client[db_name]
            self._traces_collection = self._db["execution_traces"]
            
            # Create indexes
            await self._traces_collection.create_index("trace_id", unique=True)
            await self._traces_collection.create_index("timestamp")
            await self._traces_collection.create_index("status")
            await self._traces_collection.create_index("original_query")
    
    async def save_trace(self, trace: ExecutionTrace):
        """Save an execution trace to MongoDB."""
        await self._ensure_connected()
        
        try:
            await self._traces_collection.insert_one(trace.dict())
        except Exception as e:
            # Log but don't crash
            print(f"Failed to save trace {trace.trace_id}: {e}")
    
    async def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a trace by ID."""
        await self._ensure_connected()
        
        doc = await self._traces_collection.find_one({"trace_id": trace_id})
        if doc:
            return ExecutionTrace(**doc)
        return None
    
    async def get_recent_traces(
        self,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[ExecutionTrace]:
        """Get recent traces, optionally filtered by status."""
        await self._ensure_connected()
        
        query = {}
        if status:
            query["status"] = status
        
        cursor = self._traces_collection.find(query).sort("timestamp", -1).limit(limit)
        traces = []
        async for doc in cursor:
            traces.append(ExecutionTrace(**doc))
        return traces
    
    async def get_traces_for_nebula(
        self,
        trace_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a trace formatted for Nebula input.
        Returns the trace plus all Star content used.
        """
        trace = await self.get_trace(trace_id)
        if not trace:
            return None
        
        # Fetch Star content from Star Foundry
        # (This would integrate with your Star Foundry implementation)
        stars = {}
        for star_id, version in trace.stars_used.items():
            # star_content = await star_foundry.get_star(star_id, version)
            # stars[star_id] = StarContent(...)
            pass
        
        return {
            "execution_trace": trace,
            "stars": stars
        }
```

---

## 6. Integration with Execution Code

### 6.1 Minimal Integration Example

Here's how to integrate Sidekick with the research agent pattern you showed me:

```python
# research_agent.py - Modified for Sidekick integration

from sidekick import SidekickClient

async def run_research(query: str, stars: List[str], probes: List[str]):
    """Run research with Sidekick tracing."""
    
    async with SidekickClient.create(
        original_query=query,
        stars_used=stars,
        probes_available=probes,
        config={"max_phases": 10, "max_workers_per_phase": 4}
    ) as sidekick:
        
        state = AgentState(query=query)
        
        try:
            # Run the graph
            final_state = await research_graph.ainvoke(state)
            
            # Emit completion
            sidekick.emit_execution_completed(
                final_output=final_state.final_report,
                total_duration_seconds=calculate_duration(state),
                total_llm_calls=count_llm_calls(final_state),
                total_tool_calls=count_tool_calls(final_state)
            )
            
            return final_state
            
        except Exception as e:
            sidekick.emit_execution_failed(
                error_message=str(e),
                error_type=type(e).__name__,
                stack_trace=traceback.format_exc()
            )
            raise
```

### 6.2 Phase Integration

```python
# execution.py - Modified for Sidekick integration

async def execution_node(state: AgentState) -> AgentState:
    """Execution node with Sidekick tracing."""
    
    sidekick = SidekickClient.get()
    
    for phase_idx, phase in enumerate(state.plan.phases, 1):
        async with sidekick.phase(
            phase_name=phase.name,
            phase_description=phase.description,
            planned_workers=len(phase.worker_tasks),
            phase_index=phase_idx
        ):
            await execute_phase_parallel(phase, sidekick)
    
    state.status = "evaluating"
    return state
```

### 6.3 Worker Integration

```python
# worker_agent.py - Modified for Sidekick integration

async def execute_worker_with_tracing(task: WorkerTask, sidekick: SidekickClient):
    """Execute a worker with full Sidekick tracing."""
    
    async with sidekick.worker(
        worker_name=task.name,
        task_description=task.description,
        star_id=task.star_id,
        star_version=task.star_version,
        input_context=task.input_context,
        expected_output_format=task.expected_output,
        tools_available=task.tools
    ) as worker_id:
        
        # Create worker graph
        worker_graph = create_worker_graph(task)
        
        # Execute with tracing callbacks
        result = await worker_graph.ainvoke(
            worker_state,
            config={
                "callbacks": [SidekickCallback(sidekick, worker_id)]
            }
        )
        
        sidekick.emit_worker_completed(
            worker_name=task.name,
            final_output=result["final_result"],
            total_iterations=result["iteration_count"],
            total_tool_calls=result["tool_calls_count"],
            duration_seconds=result["duration"]
        )
        
        return result
```

### 6.4 LangGraph Callback Handler

For automatic LLM and tool call tracing:

```python
from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List

class SidekickCallback(BaseCallbackHandler):
    """
    LangChain callback handler that emits events to Sidekick.
    Automatically captures LLM calls, responses, and tool usage.
    """
    
    def __init__(self, sidekick: SidekickClient, worker_id: str):
        self.sidekick = sidekick
        self.worker_id = worker_id
        self.iteration = 0
        self._call_start_times: Dict[str, datetime] = {}
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs
    ):
        self.iteration += 1
        self._call_start_times["llm"] = datetime.utcnow()
        
        # Extract messages from kwargs if available
        messages = kwargs.get("messages", [])
        
        self.sidekick.emit_llm_call(
            messages=[self._serialize_message(m) for m in messages],
            model=serialized.get("name", "unknown"),
            temperature=kwargs.get("invocation_params", {}).get("temperature", 0),
            iteration=self.iteration
        )
    
    def on_llm_end(self, response, **kwargs):
        start_time = self._call_start_times.pop("llm", None)
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000) if start_time else 0
        
        # Extract response content
        generation = response.generations[0][0] if response.generations else None
        content = generation.text if generation else ""
        tool_calls = getattr(generation.message, "tool_calls", None) if generation else None
        
        self.sidekick.emit_llm_response(
            response_content=content,
            tool_calls=tool_calls,
            tokens_used=response.llm_output.get("token_usage", {}).get("total_tokens") if response.llm_output else None,
            latency_ms=latency_ms,
            iteration=self.iteration
        )
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs
    ):
        tool_call_id = kwargs.get("run_id", str(uuid.uuid4()))
        self._call_start_times[tool_call_id] = datetime.utcnow()
        
        self.sidekick.emit_tool_call(
            tool_name=serialized.get("name", "unknown"),
            tool_args=kwargs.get("inputs", {}),
            tool_call_id=str(tool_call_id),
            iteration=self.iteration
        )
    
    def on_tool_end(self, output: str, **kwargs):
        tool_call_id = kwargs.get("run_id", "")
        start_time = self._call_start_times.pop(str(tool_call_id), None)
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000) if start_time else 0
        
        self.sidekick.emit_tool_response(
            tool_name=kwargs.get("name", "unknown"),
            tool_call_id=str(tool_call_id),
            result=str(output),
            success=True,
            latency_ms=latency_ms,
            iteration=self.iteration
        )
    
    def on_tool_error(self, error: Exception, **kwargs):
        tool_call_id = kwargs.get("run_id", "")
        start_time = self._call_start_times.pop(str(tool_call_id), None)
        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000) if start_time else 0
        
        self.sidekick.emit_tool_response(
            tool_name=kwargs.get("name", "unknown"),
            tool_call_id=str(tool_call_id),
            result="",
            success=False,
            error=str(error),
            latency_ms=latency_ms,
            iteration=self.iteration
        )
    
    def _serialize_message(self, message) -> Dict[str, Any]:
        """Convert a LangChain message to a dict."""
        return {
            "role": message.type,
            "content": message.content,
            "tool_calls": getattr(message, "tool_calls", None)
        }
```

---

## 7. API Interface

### 7.1 Query API

```python
from fastapi import FastAPI, HTTPException
from typing import Optional, List

app = FastAPI()
persistence = SidekickPersistence()

@app.get("/traces/{trace_id}")
async def get_trace(trace_id: str) -> ExecutionTrace:
    """Get a single trace by ID."""
    trace = await persistence.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@app.get("/traces")
async def list_traces(
    limit: int = 10,
    status: Optional[str] = None
) -> List[ExecutionTrace]:
    """List recent traces."""
    return await persistence.get_recent_traces(limit=limit, status=status)


@app.get("/traces/{trace_id}/for-nebula")
async def get_trace_for_nebula(trace_id: str) -> Dict[str, Any]:
    """
    Get a trace formatted for Nebula input.
    Includes execution trace and all Star content used.
    """
    result = await persistence.get_traces_for_nebula(trace_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


@app.get("/traces/{trace_id}/summary")
async def get_trace_summary(trace_id: str) -> Dict[str, Any]:
    """Get a human-readable summary of a trace."""
    trace = await persistence.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return {
        "trace_id": trace.trace_id,
        "query": trace.original_query[:100] + "..." if len(trace.original_query) > 100 else trace.original_query,
        "status": trace.status,
        "duration_seconds": trace.total_duration_seconds,
        "phases": len(trace.phases),
        "workers": trace.total_workers,
        "llm_calls": trace.total_llm_calls,
        "tool_calls": trace.total_tool_calls,
        "timestamp": trace.timestamp.isoformat(),
        "error": trace.error
    }
```

### 7.2 CLI Interface

```python
# sidekick_cli.py

import asyncio
import click
from rich.console import Console
from rich.table import Table

console = Console()
persistence = SidekickPersistence()

@click.group()
def cli():
    """Sidekick CLI for viewing execution traces."""
    pass


@cli.command()
@click.option("--limit", default=10, help="Number of traces to show")
@click.option("--status", default=None, help="Filter by status")
def list(limit: int, status: str):
    """List recent execution traces."""
    traces = asyncio.run(persistence.get_recent_traces(limit=limit, status=status))
    
    table = Table(title="Recent Traces")
    table.add_column("Trace ID", style="cyan")
    table.add_column("Query", style="white")
    table.add_column("Status", style="green")
    table.add_column("Duration", style="yellow")
    table.add_column("Workers", style="blue")
    
    for trace in traces:
        query = trace.original_query[:40] + "..." if len(trace.original_query) > 40 else trace.original_query
        table.add_row(
            trace.trace_id[:8],
            query,
            trace.status,
            f"{trace.total_duration_seconds:.1f}s",
            str(trace.total_workers)
        )
    
    console.print(table)


@cli.command()
@click.argument("trace_id")
def show(trace_id: str):
    """Show details for a specific trace."""
    trace = asyncio.run(persistence.get_trace(trace_id))
    
    if not trace:
        console.print(f"[red]Trace {trace_id} not found[/red]")
        return
    
    console.print(f"\n[bold]Trace: {trace.trace_id}[/bold]")
    console.print(f"Query: {trace.original_query}")
    console.print(f"Status: {trace.status}")
    console.print(f"Duration: {trace.total_duration_seconds:.2f}s")
    console.print(f"LLM Calls: {trace.total_llm_calls}")
    console.print(f"Tool Calls: {trace.total_tool_calls}")
    
    for phase in trace.phases:
        console.print(f"\n[bold cyan]Phase {phase.phase_index}: {phase.phase_name}[/bold cyan]")
        console.print(f"  Status: {phase.status}")
        console.print(f"  Duration: {phase.duration_seconds:.2f}s")
        
        for worker in phase.workers:
            status_color = "green" if worker.status == "completed" else "red"
            console.print(f"    [{status_color}]Worker: {worker.worker_name}[/{status_color}]")
            console.print(f"      Star: {worker.star_id} (v{worker.star_version})")
            console.print(f"      Iterations: {worker.total_iterations}")
            console.print(f"      Tool calls: {worker.total_tool_calls}")
            if worker.error:
                console.print(f"      [red]Error: {worker.error}[/red]")


@cli.command()
@click.argument("trace_id")
@click.argument("output_file")
def export(trace_id: str, output_file: str):
    """Export a trace to JSON for Nebula."""
    result = asyncio.run(persistence.get_traces_for_nebula(trace_id))
    
    if not result:
        console.print(f"[red]Trace {trace_id} not found[/red]")
        return
    
    import json
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    console.print(f"[green]Exported to {output_file}[/green]")


if __name__ == "__main__":
    cli()
```

---

## 8. File Structure

```
sidekick/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── events.py         # SidekickEvent, EventType, all payload models
│   └── traces.py         # ExecutionTrace, PhaseTrace, WorkerTrace, ToolCall
├── client.py             # SidekickClient (emitter)
├── processor.py          # SidekickProcessor (event consumer)
├── persistence.py        # SidekickPersistence (MongoDB)
├── callback.py           # SidekickCallback (LangChain integration)
├── api.py                # FastAPI endpoints
├── cli.py                # CLI interface
└── utils/
    ├── __init__.py
    └── serialization.py  # Helper functions for serializing messages, etc.
```

---

## 9. Configuration

```python
# config.py

from pydantic import BaseSettings

class SidekickConfig(BaseSettings):
    """Configuration for Sidekick."""
    
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "astro"
    traces_collection: str = "execution_traces"
    
    # Queue
    max_queue_size: int = 10000
    drop_policy: str = "oldest"  # "oldest" or "newest"
    
    # Persistence
    batch_size: int = 100  # Number of events to batch before writing
    flush_interval_seconds: float = 1.0  # Max time between flushes
    
    # Retention
    trace_retention_days: int = 30  # How long to keep traces
    
    # Performance
    enable_compression: bool = True  # Compress large payloads
    max_message_size_bytes: int = 1_000_000  # 1MB max per message
    truncate_large_outputs: bool = True
    max_output_length: int = 50000  # Truncate outputs longer than this
    
    class Config:
        env_prefix = "SIDEKICK_"
```

---

## 10. Error Handling

### 10.1 Design Principles

1. **Never crash the main execution**: All Sidekick errors are caught and logged, not propagated
2. **Degrade gracefully**: If MongoDB is down, buffer locally and retry
3. **Drop rather than block**: If the queue is full, drop events rather than slowing execution
4. **Partial traces are better than no traces**: Save what we have even if incomplete

### 10.2 Implementation

```python
class ResilientSidekickProcessor(SidekickProcessor):
    """
    Processor with enhanced error handling.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._local_buffer: List[SidekickEvent] = []
        self._max_buffer_size = 1000
        self._retry_interval = 5.0  # seconds
    
    async def _process_event(self, event: SidekickEvent):
        """Process with error handling."""
        try:
            await super()._process_event(event)
        except Exception as e:
            # Buffer the event for retry
            if len(self._local_buffer) < self._max_buffer_size:
                self._local_buffer.append(event)
            # Log but don't crash
            print(f"Sidekick: Failed to process event {event.event_id}: {e}")
    
    async def _finalize(self):
        """Save trace with retry logic."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                await super()._finalize()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Sidekick: Retry {attempt + 1} saving trace: {e}")
                    await asyncio.sleep(self._retry_interval)
                else:
                    # Last resort: save to local file
                    await self._save_to_local_file()
    
    async def _save_to_local_file(self):
        """Fallback: save trace to local JSON file."""
        if self._trace:
            import json
            from pathlib import Path
            
            fallback_dir = Path("./sidekick_fallback")
            fallback_dir.mkdir(exist_ok=True)
            
            filepath = fallback_dir / f"{self._trace.trace_id}.json"
            with open(filepath, "w") as f:
                json.dump(self._trace.dict(), f, default=str)
            
            print(f"Sidekick: Saved trace to fallback file: {filepath}")
```

---

## 11. Performance Considerations

### 11.1 Memory Management

```python
class MemoryAwareSidekickClient(SidekickClient):
    """
    Client that manages memory for large traces.
    """
    
    def __init__(self, *args, max_message_history: int = 100, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_message_history = max_message_history
    
    def emit_llm_call(self, messages: List[Dict], *args, **kwargs):
        """Emit LLM call with message truncation."""
        # Only keep last N messages to avoid memory bloat
        if len(messages) > self._max_message_history:
            messages = messages[-self._max_message_history:]
        
        # Truncate individual message content if too large
        truncated_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 10000:
                msg = {**msg, "content": content[:10000] + "... [truncated]"}
            truncated_messages.append(msg)
        
        super().emit_llm_call(truncated_messages, *args, **kwargs)
```

### 11.2 Benchmarks to Target

- Event emission: < 1ms (non-blocking)
- Queue throughput: > 10,000 events/second
- Memory overhead: < 50MB for typical execution
- Persistence latency: < 100ms per trace (async, non-blocking)

---

## 12. Implementation Phases

### Phase 1: v0.1 (MVP)
- [ ] Implement all data models (events and traces)
- [ ] Implement SidekickClient (emitter)
- [ ] Implement SidekickProcessor (event consumer)
- [ ] Basic MongoDB persistence
- [ ] CLI for viewing traces
- [ ] Manual integration with research agent

### Phase 2: v0.2 (Integration)
- [ ] LangChain callback handler for automatic tracing
- [ ] FastAPI endpoints
- [ ] Nebula integration (export format)
- [ ] Basic UI for trace visualization

### Phase 3: v0.5 (Production)
- [ ] Full Star Foundry integration
- [ ] Automatic Star content capture
- [ ] Performance optimizations (batching, compression)
- [ ] Trace retention and cleanup

### Phase 4: v1.0 (Complete)
- [ ] Real-time streaming to UI
- [ ] Alerting on failures
- [ ] Trace comparison tools
- [ ] Integration with Nebula feedback loop

---

## 13. Open Questions for Developer

1. **MongoDB vs alternatives**: Is MongoDB confirmed, or should we support other backends (PostgreSQL, local files)?

2. **Message serialization**: LangChain messages have various formats. Confirm the exact serialization approach for different message types (SystemMessage, HumanMessage, AIMessage, ToolMessage).

3. **Star content capture**: Should Sidekick capture the full Star content at execution time, or just reference star_id + version and let Nebula fetch content later?

4. **Trace size limits**: What's the maximum acceptable trace size? Need to set truncation limits appropriately.

5. **Real-time vs batch**: Should traces be queryable during execution (real-time updates to MongoDB), or only after completion?

6. **Authentication**: Will the API need authentication? If so, what mechanism?

---

## 14. Success Criteria for v0.1

- [ ] Can trace a full research agent execution end-to-end
- [ ] Captures all phases, workers, LLM calls, and tool calls
- [ ] Stores traces to MongoDB successfully
- [ ] CLI can list and show traces
- [ ] Export format matches Nebula's input schema exactly
- [ ] No measurable impact on execution performance (< 5% overhead)
- [ ] Graceful handling of MongoDB failures (doesn't crash execution)

---

## 15. Integration Diagram with Nebula

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ASTRO SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         EXECUTION LAYER                                │ │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │ │
│  │  │ Planning │───▶│ Execution│───▶│Evaluation│───▶│Synthesis │          │ │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
│                               │ events                                      │
│                               ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                           SIDEKICK                                     │ │
│  │                     (Observability Layer)                              │ │
│  │                                                                        │ │
│  │  Events ──▶ Processor ──▶ Trace Builder ──▶ MongoDB                    │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
│                               │ trace + feedback                            │
│                               ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                            NEBULA                                      │ │
│  │                     (Optimization Layer)                               │ │
│  │                                                                        │ │
│  │  Trace ──▶ Attribution ──▶ Optimization ──▶ Proposed Changes           │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
│                               │ approved changes                            │
│                               ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        STAR FOUNDRY                                    │ │
│  │                      (Prompt Registry)                                 │ │
│  │                                                                        │ │
│  │  Stars ◀── Updated Stars                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 16. Example Trace Output

Here's what a complete trace looks like in JSON:

```json
{
  "trace_id": "abc123-def456-ghi789",
  "timestamp": "2024-01-15T10:30:00Z",
  "original_query": "Research the impact of AI on healthcare diagnostics",
  "stars_used": {
    "planning_star": "1.2.0",
    "research_star": "2.0.1",
    "synthesis_star": "1.0.0"
  },
  "phases": [
    {
      "phase_id": "phase-001",
      "phase_name": "Initial Research",
      "phase_description": "Gather foundational information",
      "phase_index": 1,
      "status": "completed",
      "duration_seconds": 45.2,
      "workers": [
        {
          "worker_id": "worker-001",
          "worker_name": "AI Healthcare Overview",
          "star_id": "research_star",
          "star_version": "2.0.1",
          "task_description": "Research current AI applications in healthcare diagnostics",
          "input_context": "Focus on FDA-approved AI diagnostic tools",
          "messages": [
            {"role": "system", "content": "You are a research assistant..."},
            {"role": "user", "content": "Research current AI applications..."},
            {"role": "assistant", "content": "I'll search for information...", "tool_calls": [...]},
            {"role": "tool", "content": "Search results: ..."},
            {"role": "assistant", "content": "Based on my research..."}
          ],
          "tool_calls": [
            {
              "tool_name": "web_search",
              "tool_args": {"query": "FDA approved AI diagnostic tools 2024"},
              "tool_result": "Found 15 results...",
              "success": true,
              "latency_ms": 1200,
              "timestamp": "2024-01-15T10:30:15Z"
            }
          ],
          "final_output": "AI in healthcare diagnostics has seen significant growth...",
          "status": "completed",
          "total_iterations": 3,
          "total_tool_calls": 2,
          "duration_seconds": 22.5
        }
      ]
    }
  ],
  "final_output": "# AI in Healthcare Diagnostics: A Comprehensive Report\n\n...",
  "status": "completed",
  "total_phases": 3,
  "total_workers": 8,
  "total_llm_calls": 24,
  "total_tool_calls": 15,
  "total_duration_seconds": 180.5
}
```

This trace format is exactly what Nebula expects as input, ensuring seamless integration between the two systems.
