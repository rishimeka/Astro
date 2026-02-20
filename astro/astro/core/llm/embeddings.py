"""OpenAI embedding provider implementing the EmbeddingProvider protocol."""

import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingProvider:
    """OpenAI implementation of EmbeddingProvider.

    Uses OpenAI's embedding API to generate vector representations of text.
    Supports text-embedding-3-small (1536 dims) and text-embedding-3-large (3072 dims).
    """

    def __init__(
        self,
        model: str = DEFAULT_EMBEDDING_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize the OpenAI embedding provider.

        Args:
            model: OpenAI embedding model name.
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            base_url: Optional custom base URL. Falls back to OPENAI_BASE_URL env var.
        """
        self.model = model
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key."
            )

        resolved_base = base_url or os.getenv("OPENAI_BASE_URL")

        self._client = AsyncOpenAI(
            api_key=resolved_key,
            base_url=resolved_base,
        )
        logger.info(f"OpenAI embedding provider initialized: model={model}")

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
        )
        # Sort by index to preserve input order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
