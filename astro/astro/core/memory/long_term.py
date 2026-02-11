"""Partition 2: Long-Term Memory (permanent storage).

This module implements long-term memory with vector search capabilities.
Content is converted to embeddings and stored permanently, enabling
semantic search for relevant historical context.
"""

import uuid
from typing import Any

from astro.core.memory.compression import CompressionStrategy
from astro.interfaces.llm import EmbeddingProvider, LLMProvider
from astro.interfaces.memory import Memory, MemoryBackend


class LongTermMemory:
    """Long-term memory - permanent storage.

    Partition 2 of Second Brain:
    - Never automatically deleted (or compressed differently than context window)
    - Converted to embeddings for semantic search
    - Retrieved via vector similarity
    - Enables RAG-like behavior without explicit RAG

    Long-term memory stores conversation results, analysis outputs, and
    other important information that should be retained across sessions.
    Content is embedded using an embedding provider and stored in a
    vector database for efficient similarity search.

    Example:
        # Create long-term memory
        memory = LongTermMemory(
            backend=mongo_memory_backend,
            embedding_provider=openai_embeddings,
            llm_provider=claude_llm,  # Optional, for compression
        )

        # Store a memory
        memory_id = await memory.store(
            content="Tesla's Q4 revenue was $25.2B",
            metadata={"query": "Tesla revenue", "timestamp": "2024-01-15"}
        )

        # Retrieve relevant memories
        relevant = await memory.retrieve(
            query="What was Tesla's recent revenue?",
            limit=5
        )
        for mem in relevant:
            print(mem.content)
    """

    def __init__(
        self,
        backend: MemoryBackend,
        embedding_provider: EmbeddingProvider,
        compression_strategy: CompressionStrategy | None = None,
        llm_provider: LLMProvider | None = None,
    ):
        """Initialize long-term memory.

        Args:
            backend: Storage backend for memories (vector database)
            embedding_provider: Provider for generating embeddings
            compression_strategy: Optional strategy for compressing before storage
            llm_provider: Optional LLM provider (only needed if compression uses LLM)
        """
        self.backend = backend
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.compression = compression_strategy

    async def store(
        self,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """Store content in long-term memory.

        The content is optionally compressed, then embedded, and finally
        stored in the backend with its embedding for future vector search.

        Args:
            content: Text content to store
            metadata: Metadata to attach (e.g., query, directives, timestamp)

        Returns:
            Memory ID for the stored memory

        Example:
            memory_id = await memory.store(
                content="Analysis results: ...",
                metadata={
                    "query": "Analyze Tesla",
                    "directives": ["financial_analysis"],
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            )
        """
        # Optionally compress (uses llm_provider if compression needs LLM)
        stored_content = content
        if self.compression:
            stored_content = await self.compression.compress(content)

        # Generate embedding (uses embedding_provider)
        embedding = await self.embedding_provider.embed(stored_content)

        # Store via backend
        memory_id = self._generate_id()
        await self.backend.store(memory_id, stored_content, embedding, metadata)

        return memory_id

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """Retrieve relevant memories via vector search.

        Performs semantic similarity search to find memories most relevant
        to the query. The query is embedded and compared against stored
        embeddings using cosine similarity.

        Args:
            query: Search query (will be embedded)
            limit: Maximum number of memories to return
            filter_metadata: Optional metadata filters to narrow search

        Returns:
            List of relevant memories, sorted by similarity (most relevant first)

        Example:
            # Find relevant memories
            memories = await memory.retrieve(
                query="Tesla financial performance",
                limit=5,
                filter_metadata={"directives": ["financial_analysis"]}
            )

            for mem in memories:
                print(f"[{mem.timestamp}] {mem.content}")
        """
        # Use embedding_provider for query embedding
        query_embedding = await self.embedding_provider.embed(query)

        # Search via backend
        return await self.backend.search(
            query_embedding,
            limit,
            filter_metadata,
        )

    async def retrieve_by_id(self, memory_id: str) -> Memory | None:
        """Retrieve a specific memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory if found, None otherwise
        """
        return await self.backend.retrieve(memory_id)

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if deleted, False if not found
        """
        return await self.backend.delete(memory_id)

    def _generate_id(self) -> str:
        """Generate unique memory ID.

        Returns:
            Unique memory identifier (mem_<12 hex chars>)
        """
        return f"mem_{uuid.uuid4().hex[:12]}"
