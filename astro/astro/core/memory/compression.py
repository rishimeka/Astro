"""Compression strategies for memory content.

This module provides different strategies for compressing conversation history
and memory content. Compression is used to manage token usage while retaining
important information.
"""

from typing import Protocol


class CompressionStrategy(Protocol):
    """Strategy for compressing memory content.

    Implementations define how to compress text while retaining important
    information. Different strategies trade off between compression ratio
    and information retention.
    """

    async def compress(self, content: str) -> str:
        """Compress content asynchronously.

        Args:
            content: Text to compress

        Returns:
            Compressed version of the content
        """
        ...


class NoOpCompression:
    """No compression - pass through unchanged.

    Useful for testing or when compression is not desired.
    """

    async def compress(self, content: str) -> str:
        """Return content unchanged.

        Args:
            content: Text to pass through

        Returns:
            Original content unchanged
        """
        return content

    def compress_sync(self, content: str) -> str:
        """Synchronous version for non-async contexts."""
        return content


class SummarizationCompression:
    """Compress via LLM summarization.

    Uses an LLM to intelligently summarize content while retaining
    key information. This provides the best information retention
    but requires an LLM call.
    """

    def __init__(self, llm: "LLMProvider" = None, max_chars: int = 1000):  # type: ignore
        """Initialize summarization compression.

        Args:
            llm: LLM provider for generating summaries
            max_chars: Target character count for summary
        """
        self.llm = llm
        self.max_chars = max_chars

    async def compress(self, content: str) -> str:
        """Summarize content using LLM.

        Args:
            content: Text to summarize

        Returns:
            Summarized version of content
        """
        if len(content) <= self.max_chars:
            return content

        if self.llm is None:
            # Fallback to truncation if no LLM provided
            return content[:self.max_chars] + "..."

        try:
            response = await self.llm.invoke([
                {
                    "role": "user",
                    "content": f"Summarize the following in approximately {self.max_chars} characters, "
                    f"retaining key information:\n\n{content}"
                }
            ])
            return response["content"]
        except Exception:
            # Fallback to truncation on error
            return content[:self.max_chars] + "..."

    def compress_sync(self, content: str) -> str:
        """Synchronous fallback - truncates to max_chars."""
        if len(content) <= self.max_chars:
            return content
        return content[:self.max_chars] + "..."


class TokenLimitCompression:
    """Compress by truncating to token limit.

    Simple strategy that truncates text to a maximum token count.
    Fast but may lose important information at the end.
    """

    def __init__(self, max_tokens: int = 500):
        """Initialize token limit compression.

        Args:
            max_tokens: Maximum token count (approximately 4 chars per token)
        """
        self.max_tokens = max_tokens

    async def compress(self, content: str) -> str:
        """Truncate to token limit.

        Uses a simple approximation of 4 characters per token.

        Args:
            content: Text to truncate

        Returns:
            Truncated content
        """
        max_chars = self.max_tokens * 4
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."

    def compress_sync(self, content: str) -> str:
        """Synchronous version - same as async."""
        max_chars = self.max_tokens * 4
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."
