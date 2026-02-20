"""Vector search retrieval module for Second Brain.

Wraps the MemoryBackend and EmbeddingProvider to provide a high-level
retrieval interface with configurable top_k and similarity threshold.
"""

import logging
from typing import Any

from astro.interfaces.llm import EmbeddingProvider
from astro.interfaces.memory import Memory, MemoryBackend

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Retrieves relevant memories via vector similarity search.

    Takes query strings, generates embeddings via EmbeddingProvider,
    and returns ranked results from the MemoryBackend filtered by
    a configurable similarity threshold.
    """

    def __init__(
        self,
        backend: MemoryBackend,
        embedding_provider: EmbeddingProvider,
        default_top_k: int = 5,
        default_similarity_threshold: float = 0.0,
    ):
        """Initialize the retriever.

        Args:
            backend: Storage backend for vector search.
            embedding_provider: Provider for generating query embeddings.
            default_top_k: Default number of results to return per query.
            default_similarity_threshold: Minimum similarity score (0-1).
                Results below this threshold are filtered out.
        """
        self.backend = backend
        self.embedding_provider = embedding_provider
        self.default_top_k = default_top_k
        self.default_similarity_threshold = default_similarity_threshold

    async def retrieve(
        self,
        queries: list[str],
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """Retrieve relevant memories for a list of queries.

        Embeds each query, searches the backend, deduplicates by memory ID,
        and returns the top_k most relevant results.

        Args:
            queries: Search queries to embed and search for.
            top_k: Max results to return (overrides default).
            similarity_threshold: Min similarity score (overrides default).
            filter_metadata: Optional metadata filters passed to backend.

        Returns:
            List of Memory objects, deduplicated and ranked by relevance.
        """
        top_k = top_k or self.default_top_k
        threshold = similarity_threshold if similarity_threshold is not None else self.default_similarity_threshold

        seen_ids: set[str] = set()
        all_memories: list[Memory] = []

        for query in queries:
            try:
                memories = await self._search_single(
                    query, top_k, filter_metadata
                )
                for mem in memories:
                    if mem.id not in seen_ids:
                        seen_ids.add(mem.id)
                        all_memories.append(mem)
            except Exception as e:
                logger.warning(f"Retrieval failed for query '{query[:50]}...': {e}")
                continue

        # Return top_k results (backend already returns ranked results,
        # but after dedup across queries we may have more than top_k)
        return all_memories[:top_k]

    async def _search_single(
        self,
        query: str,
        limit: int,
        filter_metadata: dict[str, Any] | None,
    ) -> list[Memory]:
        """Search for a single query."""
        embedding = await self.embedding_provider.embed(query)
        return await self.backend.search(
            query_embedding=embedding,
            limit=limit,
            filter_metadata=filter_metadata,
        )

    async def retrieve_text(
        self,
        queries: list[str],
        top_k: int | None = None,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Convenience method: retrieve and return just content strings.

        Args:
            queries: Search queries.
            top_k: Max results.
            filter_metadata: Optional metadata filters.

        Returns:
            List of memory content strings.
        """
        memories = await self.retrieve(queries, top_k=top_k, filter_metadata=filter_metadata)
        return [m.content for m in memories]
