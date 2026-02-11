"""Partition 1: Active Context Window (working memory).

This module implements the active context window - recent conversation history
that is fully provided to the LLM on every call. It automatically compresses
when the size exceeds a threshold to keep token usage manageable.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from astro.core.memory.compression import CompressionStrategy, SummarizationCompression


@dataclass
class Message:
    """A single message in the context window.

    Messages capture both user and assistant messages in the conversation,
    along with metadata for tracking and debugging.
    """

    role: str  # 'user', 'assistant', or 'system'
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ContextWindow:
    """Active context window - working memory.

    Partition 1 of Second Brain:
    - Contains recent conversation history
    - Compressed at character threshold to manage token usage
    - Fully provided to LLM every call
    - Older messages are summarized, recent ones kept in full

    The context window maintains a sliding window of conversation history.
    When it exceeds the max_chars threshold, it automatically compresses
    older messages while keeping the most recent messages intact.

    Example:
        # Create context window
        window = ContextWindow(max_chars=50000)

        # Add messages
        window.add_message("Hello!", {"role": "user"})
        window.add_message("Hi! How can I help?", {"role": "assistant"})

        # Add exchange (convenience method)
        window.add_exchange(
            user_message="What's the weather?",
            assistant_message="The weather is sunny."
        )

        # Get recent messages
        recent = window.get_recent(limit=10)
        for msg in recent:
            print(f"{msg.role}: {msg.content}")
    """

    def __init__(
        self,
        max_chars: int = 50000,
        compression_strategy: CompressionStrategy | None = None,
    ):
        """Initialize context window.

        Args:
            max_chars: Maximum character count before compression triggers
            compression_strategy: Strategy for compressing old messages
                                (defaults to summarization)
        """
        self.max_chars = max_chars
        self.compression = compression_strategy or SummarizationCompression()
        self.messages: list[Message] = []

    def add_message(self, content: str, metadata: dict[str, Any]) -> None:
        """Add a message to context window.

        Compresses if size exceeds threshold after adding the message.

        Args:
            content: Message content
            metadata: Message metadata (must include 'role')
        """
        message = Message(
            role=metadata.get("role", "assistant"),
            content=content,
            metadata=metadata,
            timestamp=time.time(),
        )
        self.messages.append(message)

        # Compress if needed
        if self._size() > self.max_chars:
            self._compress()

    def add_exchange(
        self,
        user_message: str,
        assistant_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a user-assistant exchange (convenience method).

        Args:
            user_message: User's message
            assistant_message: Assistant's response
            metadata: Optional metadata to attach to both messages
        """
        metadata = metadata or {}
        self.add_message(user_message, {"role": "user", **metadata})
        self.add_message(assistant_message, {"role": "assistant", **metadata})

    def get_recent(self, limit: int = 10) -> list[Message]:
        """Get recent messages.

        Args:
            limit: Maximum number of recent messages to return

        Returns:
            List of most recent messages (up to limit)
        """
        return self.messages[-limit:]

    def get_all(self) -> list[Message]:
        """Get all messages in context window.

        Returns:
            All messages including compressed summaries
        """
        return self.messages.copy()

    def clear(self) -> None:
        """Clear all messages from context window."""
        self.messages = []

    def _size(self) -> int:
        """Calculate total character count of all messages.

        Returns:
            Total characters across all message content
        """
        return sum(len(msg.content) for msg in self.messages)

    def _compress(self) -> None:
        """Compress older messages while keeping recent ones.

        Strategy:
        - Keep most recent N messages (default 5) in full
        - Summarize all older messages into a single summary message
        - Replace old messages with the summary

        This ensures recent context is always available while managing
        the overall token count.
        """
        keep_recent = 5
        if len(self.messages) <= keep_recent:
            return

        # Split into old and recent
        old_messages = self.messages[:-keep_recent]
        recent_messages = self.messages[-keep_recent:]

        # Compress old messages
        compressed_content = self._compress_messages(old_messages)

        # Replace with summary
        self.messages = [
            Message(
                role="system",
                content=f"[Summary of earlier conversation]\n{compressed_content}",
                metadata={"compressed": True},
                timestamp=old_messages[0].timestamp,
            )
        ] + recent_messages

    def _compress_messages(self, messages: list[Message]) -> str:
        """Compress a list of messages into a summary.

        Args:
            messages: Messages to compress

        Returns:
            Compressed summary of messages
        """
        # Combine all message content
        combined = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        # Note: The compression strategy should be async, but for simplicity
        # in this context, we'll make it synchronous. In production, this
        # should be handled with async/await.
        try:
            # If compression strategy has a sync method, use it
            if hasattr(self.compression, "compress_sync"):
                return self.compression.compress_sync(combined)  # type: ignore
            else:
                # Fallback: simple truncation
                max_chars = 1000
                if len(combined) <= max_chars:
                    return combined
                return combined[:max_chars] + "..."
        except Exception:
            # Fallback on error: simple truncation
            max_chars = 1000
            return (
                combined[:max_chars] + "..." if len(combined) > max_chars else combined
            )
