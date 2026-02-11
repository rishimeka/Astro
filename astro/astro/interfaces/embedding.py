"""Embedding provider interface for vector representations.

This module re-exports EmbeddingProvider from llm.py for convenience.
The EmbeddingProvider protocol is defined in llm.py alongside LLMProvider.
"""

from astro.interfaces.llm import EmbeddingProvider

__all__ = ["EmbeddingProvider"]
