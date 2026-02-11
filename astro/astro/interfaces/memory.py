"""Thin memory storage interface - implementation details left to backends."""

from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Memory:
    """A single memory entry."""
    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: float


class MemoryBackend(Protocol):
    """Storage backend for long-term memory.

    Defines ONLY the storage contract. Compression, embedding strategy,
    and retrieval logic are implementation details.

    Implementations can be:
    - Vector databases (Pinecone, Weaviate, Chroma)
    - MongoDB with vector search
    - PostgreSQL with pgvector
    - In-memory (for testing)
    """

    async def store(
        self,
        id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Store a memory entry with its vector embedding.

        Args:
            id: Unique memory ID
            content: Text content (may be compressed)
            embedding: Vector embedding of content
            metadata: Additional metadata (query, directives, timestamp, etc.)
        """
        ...

    async def retrieve(self, id: str) -> Optional[Memory]:
        """Retrieve a specific memory by ID.

        Args:
            id: Unique memory identifier

        Returns:
            Memory object if found, None otherwise
        """
        ...

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Memory]:
        """Vector similarity search for relevant memories.

        Args:
            query_embedding: Vector to search for
            limit: Maximum number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of memories sorted by relevance (cosine similarity)
        """
        ...

    async def delete(self, id: str) -> bool:
        """Delete a memory entry.

        Args:
            id: Unique memory identifier

        Returns:
            True if deleted, False if not found
        """
        ...
