"""Execution stream handlers for real-time event delivery.

This module provides the stream abstraction and implementations for
delivering execution events to various consumers (SSE, WebSocket, logging, etc.).
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional

from astro.core.runtime.events import StreamEvent

logger = logging.getLogger(__name__)


class ExecutionStream(ABC):
    """Abstract base class for execution event streams.

    Implementations handle how events are delivered to consumers.
    The stream is created before execution begins and closed when
    execution completes (successfully or with error).
    """

    @abstractmethod
    async def emit(self, event: StreamEvent) -> None:
        """Emit an event to the stream.

        Args:
            event: The event to emit.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the stream.

        Called when execution completes. Implementations should
        signal to consumers that no more events will be sent.
        """
        pass

    async def __aenter__(self) -> "ExecutionStream":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures stream is closed."""
        await self.close()


class NoOpStream(ExecutionStream):
    """Silent stream that discards all events.

    Use for batch execution or testing where events aren't needed.
    """

    async def emit(self, event: StreamEvent) -> None:
        """Discard the event."""
        pass

    async def close(self) -> None:
        """No-op close."""
        pass


class AsyncQueueStream(ExecutionStream):
    """Stream implementation using asyncio.Queue.

    Perfect for SSE endpoints - events are put on a queue that
    can be consumed by an async generator.

    Example:
        stream = AsyncQueueStream()

        async def event_generator():
            async for event in stream:
                yield {"event": event.event_type, "data": event.model_dump_json()}

        # In another coroutine:
        await stream.emit(NodeStartedEvent(...))
        await stream.close()
    """

    def __init__(self, maxsize: int = 0) -> None:
        """Initialize the queue stream.

        Args:
            maxsize: Maximum queue size (0 = unlimited).
        """
        self.queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue(maxsize=maxsize)
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        """Put an event on the queue.

        Args:
            event: The event to emit.
        """
        if self._closed:
            logger.warning(f"Attempted to emit to closed stream: {event.event_type}")
            return
        await self.queue.put(event)

    async def close(self) -> None:
        """Close the stream by putting a sentinel value."""
        if not self._closed:
            self._closed = True
            await self.queue.put(None)

    @property
    def is_closed(self) -> bool:
        """Check if the stream is closed."""
        return self._closed

    async def get(self, timeout: Optional[float] = None) -> Optional[StreamEvent]:
        """Get the next event from the queue.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            The next event, or None if stream is closed.
        """
        try:
            if timeout:
                event = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            else:
                event = await self.queue.get()
            return event
        except asyncio.TimeoutError:
            return None

    def __aiter__(self) -> AsyncIterator[StreamEvent]:
        """Iterate over events until stream closes."""
        return self

    async def __anext__(self) -> StreamEvent:
        """Get next event or raise StopAsyncIteration."""
        event = await self.queue.get()
        if event is None:
            raise StopAsyncIteration
        return event


class CallbackStream(ExecutionStream):
    """Stream that invokes a callback for each event.

    Useful for simple integrations or when you need custom handling.

    Example:
        async def my_handler(event):
            print(f"Got event: {event.event_type}")

        stream = CallbackStream(my_handler)
    """

    def __init__(
        self,
        callback: Callable[[StreamEvent], Awaitable[None]],
        on_close: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """Initialize with callback function.

        Args:
            callback: Async function to call for each event.
            on_close: Optional async function to call on close.
        """
        self._callback = callback
        self._on_close = on_close
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        """Invoke the callback with the event.

        Args:
            event: The event to emit.
        """
        if self._closed:
            return
        try:
            await self._callback(event)
        except Exception as e:
            logger.error(f"Callback error for {event.event_type}: {e}")

    async def close(self) -> None:
        """Mark closed and invoke close callback if provided."""
        if not self._closed:
            self._closed = True
            if self._on_close:
                try:
                    await self._on_close()
                except Exception as e:
                    logger.error(f"Close callback error: {e}")


class CompositeStream(ExecutionStream):
    """Stream that fans out events to multiple child streams.

    Use when you need to send events to multiple destinations
    (e.g., SSE + logging + metrics).

    Example:
        sse_stream = AsyncQueueStream()
        log_stream = LoggingStream()
        stream = CompositeStream([sse_stream, log_stream])
    """

    def __init__(self, streams: List[ExecutionStream]) -> None:
        """Initialize with list of child streams.

        Args:
            streams: List of streams to forward events to.
        """
        self._streams = streams
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        """Emit to all child streams concurrently.

        Args:
            event: The event to emit.
        """
        if self._closed:
            return
        await asyncio.gather(
            *[stream.emit(event) for stream in self._streams],
            return_exceptions=True,
        )

    async def close(self) -> None:
        """Close all child streams."""
        if not self._closed:
            self._closed = True
            await asyncio.gather(
                *[stream.close() for stream in self._streams],
                return_exceptions=True,
            )

    def add_stream(self, stream: ExecutionStream) -> None:
        """Add a stream to the composite.

        Args:
            stream: Stream to add.
        """
        self._streams.append(stream)


class LoggingStream(ExecutionStream):
    """Stream that logs events using Python logging.

    Useful for debugging and audit trails.
    """

    def __init__(
        self,
        logger_name: str = "astro.execution",
        level: int = logging.INFO,
    ) -> None:
        """Initialize the logging stream.

        Args:
            logger_name: Name for the logger.
            level: Logging level for events.
        """
        self._logger = logging.getLogger(logger_name)
        self._level = level
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        """Log the event.

        Args:
            event: The event to log.
        """
        if self._closed:
            return

        # Format based on event type
        msg = self._format_event(event)
        self._logger.log(self._level, msg)

    async def close(self) -> None:
        """Mark stream as closed."""
        self._closed = True

    def _format_event(self, event: StreamEvent) -> str:
        """Format event for logging."""
        base = f"[{event.run_id}] {event.event_type}"

        if hasattr(event, "node_id"):
            base += f" node={event.node_id}"
        if hasattr(event, "node_name"):
            base += f" ({event.node_name})"
        if hasattr(event, "error"):
            base += f" error={event.error}"
        if hasattr(event, "tool_name"):
            base += f" tool={event.tool_name}"
        if hasattr(event, "duration_ms"):
            base += f" duration={event.duration_ms}ms"

        return base


class BufferedStream(ExecutionStream):
    """Stream that buffers events and flushes periodically.

    Useful when you want to batch events for efficiency.
    """

    def __init__(
        self,
        target: ExecutionStream,
        buffer_size: int = 10,
        flush_interval: float = 0.1,
    ) -> None:
        """Initialize the buffered stream.

        Args:
            target: Target stream to flush to.
            buffer_size: Number of events before auto-flush.
            flush_interval: Seconds between auto-flushes.
        """
        self._target = target
        self._buffer: List[StreamEvent] = []
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._closed = False
        self._flush_task: Optional[asyncio.Task[None]] = None

    async def emit(self, event: StreamEvent) -> None:
        """Buffer the event, flushing if buffer is full.

        Args:
            event: The event to buffer.
        """
        if self._closed:
            return

        self._buffer.append(event)

        if len(self._buffer) >= self._buffer_size:
            await self._flush()

    async def _flush(self) -> None:
        """Flush buffered events to target."""
        if not self._buffer:
            return

        events = self._buffer
        self._buffer = []

        for event in events:
            await self._target.emit(event)

    async def close(self) -> None:
        """Flush remaining events and close."""
        if not self._closed:
            self._closed = True
            await self._flush()
            await self._target.close()


def serialize_event_for_sse(event: StreamEvent) -> Dict[str, str]:
    """Serialize a stream event for SSE transmission.

    Args:
        event: The event to serialize.

    Returns:
        Dict with 'event' and 'data' keys for SSE.
    """
    return {
        "event": event.event_type,
        "data": event.model_dump_json(),
    }


def serialize_event_dict(event: StreamEvent) -> Dict[str, Any]:
    """Serialize a stream event to a dictionary.

    Args:
        event: The event to serialize.

    Returns:
        Dict representation of the event.
    """
    data = event.model_dump()
    # Convert datetime to ISO string for JSON
    if "timestamp" in data:
        data["timestamp"] = data["timestamp"].isoformat()
    return data
