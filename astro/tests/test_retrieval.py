"""Unit tests for core/memory/retrieval.py."""

from unittest.mock import AsyncMock

import pytest

from astro.core.memory.retrieval import MemoryRetriever
from astro.interfaces.memory import Memory


@pytest.fixture
def mock_backend():
    backend = AsyncMock()
    backend.search = AsyncMock(return_value=[])
    return backend


@pytest.fixture
def mock_embedding_provider():
    provider = AsyncMock()
    provider.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return provider


@pytest.fixture
def retriever(mock_backend, mock_embedding_provider):
    return MemoryRetriever(
        backend=mock_backend,
        embedding_provider=mock_embedding_provider,
        default_top_k=3,
    )


@pytest.mark.asyncio
async def test_retrieve_empty_queries(retriever):
    result = await retriever.retrieve([])
    assert result == []


@pytest.mark.asyncio
async def test_retrieve_single_query(retriever, mock_backend, mock_embedding_provider):
    mem = Memory(id="m1", content="Tesla revenue $25B", metadata={}, timestamp=1.0)
    mock_backend.search.return_value = [mem]

    result = await retriever.retrieve(["Tesla revenue"])

    mock_embedding_provider.embed.assert_called_once_with("Tesla revenue")
    mock_backend.search.assert_called_once_with(
        query_embedding=[0.1, 0.2, 0.3],
        limit=3,
        filter_metadata=None,
    )
    assert len(result) == 1
    assert result[0].content == "Tesla revenue $25B"


@pytest.mark.asyncio
async def test_retrieve_deduplicates_across_queries(retriever, mock_backend):
    mem1 = Memory(id="m1", content="result 1", metadata={}, timestamp=1.0)
    mem2 = Memory(id="m2", content="result 2", metadata={}, timestamp=2.0)
    # Both queries return m1; second also returns m2
    mock_backend.search.side_effect = [[mem1], [mem1, mem2]]

    result = await retriever.retrieve(["q1", "q2"])

    assert len(result) == 2
    assert {m.id for m in result} == {"m1", "m2"}


@pytest.mark.asyncio
async def test_retrieve_respects_top_k(retriever, mock_backend):
    mems = [Memory(id=f"m{i}", content=f"r{i}", metadata={}, timestamp=float(i)) for i in range(10)]
    mock_backend.search.return_value = mems

    result = await retriever.retrieve(["query"], top_k=2)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_retrieve_continues_on_error(retriever, mock_backend):
    mem = Memory(id="m1", content="good", metadata={}, timestamp=1.0)
    mock_backend.search.side_effect = [Exception("fail"), [mem]]

    result = await retriever.retrieve(["bad_query", "good_query"])
    assert len(result) == 1
    assert result[0].id == "m1"


@pytest.mark.asyncio
async def test_retrieve_text(retriever, mock_backend):
    mem = Memory(id="m1", content="hello world", metadata={}, timestamp=1.0)
    mock_backend.search.return_value = [mem]

    result = await retriever.retrieve_text(["query"])
    assert result == ["hello world"]


@pytest.mark.asyncio
async def test_retrieve_passes_filter_metadata(retriever, mock_backend):
    await retriever.retrieve(
        ["query"],
        filter_metadata={"type": "user_query"},
    )
    mock_backend.search.assert_called_once_with(
        query_embedding=[0.1, 0.2, 0.3],
        limit=3,
        filter_metadata={"type": "user_query"},
    )
