"""LLM provider interface for text generation.

This module defines the protocol for LLM text generation. It is separate from
EmbeddingProvider because not all LLM providers support both generation and
embeddings, and you typically use different models for each purpose.
"""

from typing import Any, Protocol


class LLMProvider(Protocol):
    """LLM provider interface for text generation.

    This protocol defines the contract for text generation with optional tool calling.
    Separate from EmbeddingProvider because:
    - Not all LLM providers support embeddings
    - You typically use different models (e.g., Claude for generation,
      text-embedding-3-small for embeddings)
    - Generation and embeddings have different performance characteristics

    Implementations can be:
    - Anthropic (Claude)
    - OpenAI (GPT)
    - Custom API gateways
    - Local models (Ollama, llama.cpp)

    Example usage:
        ```python
        from astro.interfaces.llm import LLMProvider

        # Use Claude for generation
        llm = ClaudeLLMProvider(model="claude-3-5-sonnet-20241022")

        # Simple generation
        response = await llm.invoke(
            messages=[
                {"role": "user", "content": "What is the capital of France?"}
            ]
        )
        print(response["content"])

        # With tools
        tools = [search_tool, calculator_tool]
        response = await llm.invoke(
            messages=[
                {"role": "user", "content": "What's 2+2 and what's the weather?"}
            ],
            tools=tools,
        )
        if response["tool_calls"]:
            for call in response["tool_calls"]:
                print(f"Calling: {call['name']}")
        ```
    """

    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]:
        """Invoke LLM with messages and optional tools.

        This is the core method for text generation. It supports both simple
        generation and tool-calling (function calling).

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Role can be: 'system', 'user', 'assistant', 'tool'
                     Example: [{"role": "user", "content": "Hello"}]
            tools: Optional list of tool definitions (LangChain format)
                  Tools enable function calling - LLM can request to call tools
                  Format depends on implementation (typically LangChain StructuredTool)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
                        Lower values make output more focused and deterministic
                        Higher values make output more random and creative
            max_tokens: Maximum tokens to generate (None = model default)
                       Includes both input and output tokens for some models
            stop_sequences: Sequences that stop generation when encountered
                           Example: ["</answer>", "DONE"]

        Returns:
            Dict with the following keys:
            - content: str - Generated text response
            - tool_calls: List[Dict] - Tool calls requested by LLM (empty list if none)
                         Each tool call has: name, arguments, id
            - stop_reason: str - Why generation stopped
                          Values: "end_turn", "tool_use", "max_tokens", "stop_sequence"
            - usage: Dict - Token usage statistics
                    Keys: prompt_tokens, completion_tokens, total_tokens

        Raises:
            LLMError: If LLM call fails (rate limit, timeout, invalid request)

        Example:
            ```python
            # Simple generation
            response = await llm.invoke(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.5,
            )
            print(response["content"])  # "Hello! How can I help you?"

            # With tool calling
            response = await llm.invoke(
                messages=[{"role": "user", "content": "What's the weather in NYC?"}],
                tools=[weather_tool],
            )
            if response["tool_calls"]:
                call = response["tool_calls"][0]
                print(f"LLM wants to call: {call['name']} with {call['arguments']}")
            ```

        Note:
            Tool calling support varies by model:
            - Claude 3+: Full support
            - GPT-4+: Full support
            - Older models: May not support tools
            - Custom gateways: May strip tools parameter
        """
        ...


class EmbeddingProvider(Protocol):
    """Embedding provider interface for vector representations.

    This protocol defines the contract for generating embeddings (vector
    representations of text). Separate from LLMProvider because:
    - Not all LLM providers support embeddings
    - You typically use different models (e.g., Claude for generation,
      text-embedding-3-small for embeddings)
    - Embedding models are specialized and cheaper

    Implementations can be:
    - OpenAI (text-embedding-3-small, text-embedding-3-large)
    - Cohere (embed-english-v3.0)
    - Sentence Transformers (local, all-MiniLM-L6-v2)
    - Voyage AI
    - HuggingFace models

    Example usage:
        ```python
        from astro.interfaces.embedding import EmbeddingProvider

        # Use OpenAI for embeddings
        embeddings = OpenAIEmbeddingProvider(model="text-embedding-3-small")

        # Single text
        vector = await embeddings.embed("Hello world")
        print(len(vector))  # 1536 dimensions for text-embedding-3-small

        # Batch processing
        vectors = await embeddings.embed_batch([
            "First text",
            "Second text",
            "Third text",
        ])
        print(len(vectors))  # 3 vectors
        ```
    """

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Used by Second Brain for semantic search. Converts text into a dense
        vector representation that captures semantic meaning.

        Args:
            text: Text to embed (typically a sentence or paragraph)
                 Very long text may be truncated depending on model limits
                 (e.g., 8191 tokens for text-embedding-3-small)

        Returns:
            List of floats (embedding vector)
            - Dimensions depend on model (typically 768-3072)
            - text-embedding-3-small: 1536 dimensions
            - text-embedding-3-large: 3072 dimensions
            - sentence-transformers: 384-768 dimensions

        Raises:
            EmbeddingError: If embedding generation fails

        Example:
            ```python
            text = "The capital of France is Paris."
            vector = await embeddings.embed(text)
            print(len(vector))  # 1536
            print(vector[:3])   # [0.123, -0.456, 0.789, ...]
            ```

        Note:
            Embeddings are normalized to unit length for most models.
            Use cosine similarity to compare embeddings.
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batch optimization).

        More efficient than calling embed() multiple times because:
        - Single API call instead of multiple
        - Better throughput
        - Lower latency overall

        Args:
            texts: List of texts to embed
                  Each text is embedded independently
                  Order is preserved in output

        Returns:
            List of embedding vectors (one per input text)
            Each vector has the same dimensions as embed()

        Raises:
            EmbeddingError: If embedding generation fails for any text

        Example:
            ```python
            texts = [
                "The capital of France is Paris.",
                "Python is a programming language.",
                "The sky is blue.",
            ]
            vectors = await embeddings.embed_batch(texts)
            print(len(vectors))      # 3
            print(len(vectors[0]))   # 1536

            # Calculate similarity between first two
            from numpy import dot
            from numpy.linalg import norm
            similarity = dot(vectors[0], vectors[1]) / (norm(vectors[0]) * norm(vectors[1]))
            print(similarity)  # 0.123 (low similarity - different topics)
            ```

        Note:
            Some providers have batch size limits:
            - OpenAI: 2048 texts per batch
            - Cohere: 96 texts per batch
            Check provider documentation for limits.
        """
        ...
