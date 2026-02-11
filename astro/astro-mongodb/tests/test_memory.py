"""Tests for MongoDBMemory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from astro_mongodb.memory import MongoDBMemory


@pytest.fixture
def memory():
    """Create MongoDBMemory instance."""
    return MongoDBMemory(
        uri="mongodb://localhost:27017",
        database="test_astro",
        collection="memories",
        use_atlas_search=False,  # Use aggregation for testing
    )


@pytest.fixture
def sample_embedding():
    """Create a sample embedding vector."""
    return [0.1] * 1536  # Typical OpenAI embedding size


@pytest.mark.asyncio
async def test_startup_success(memory):
    """Test successful startup."""
    with patch("astro_mongodb.memory.AsyncIOMotorClient") as mock_client_class:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_client.admin.command = AsyncMock(return_value={})
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_collection.create_index = AsyncMock()

        mock_client_class.return_value = mock_client

        await memory.startup()

        assert memory._client is not None
        assert memory._db is not None
        mock_client.admin.command.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_shutdown(memory):
    """Test shutdown."""
    mock_client = MagicMock()
    memory._client = mock_client

    await memory.shutdown()

    mock_client.close.assert_called_once()
    assert memory._client is None
    assert memory._db is None


@pytest.mark.asyncio
async def test_store_memory(memory, sample_embedding):
    """Test storing a memory."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.replace_one = AsyncMock()

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    await memory.store(
        id="memory_123",
        content="Test content",
        embedding=sample_embedding,
        metadata={"domain": "test"},
    )

    mock_collection.replace_one.assert_called_once()

    # Verify the document structure
    call_args = mock_collection.replace_one.call_args
    doc = call_args[0][1]
    assert doc["_id"] == "memory_123"
    assert doc["content"] == "Test content"
    assert doc["embedding"] == sample_embedding
    assert doc["metadata"] == {"domain": "test"}
    assert "timestamp" in doc


@pytest.mark.asyncio
async def test_store_memory_not_initialized(memory, sample_embedding):
    """Test storing memory when storage not initialized."""
    with pytest.raises(RuntimeError, match="Storage not initialized"):
        await memory.store(
            id="test",
            content="Test",
            embedding=sample_embedding,
            metadata={},
        )


@pytest.mark.asyncio
async def test_retrieve_memory_found(memory):
    """Test retrieving a memory that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    doc = {
        "_id": "memory_123",
        "content": "Test content",
        "metadata": {"domain": "test"},
        "timestamp": 1234567890.0,
    }
    mock_collection.find_one = AsyncMock(return_value=doc)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.interfaces.memory.Memory") as mock_memory_class:
        mock_instance = MagicMock()
        mock_memory_class.return_value = mock_instance
        result = await memory.retrieve("memory_123")

        assert result == mock_instance
        mock_collection.find_one.assert_called_once_with({"_id": "memory_123"})


@pytest.mark.asyncio
async def test_retrieve_memory_not_found(memory):
    """Test retrieving a memory that doesn't exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await memory.retrieve("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_search_aggregation(memory, sample_embedding):
    """Test search using aggregation pipeline (non-Atlas)."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    # Mock documents with embeddings
    docs = [
        {
            "_id": "mem1",
            "content": "Content 1",
            "embedding": [0.1] * 1536,
            "metadata": {"domain": "test"},
            "timestamp": 1234567890.0,
        },
        {
            "_id": "mem2",
            "content": "Content 2",
            "embedding": [0.2] * 1536,
            "metadata": {"domain": "test"},
            "timestamp": 1234567891.0,
        },
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.interfaces.memory.Memory") as mock_memory_class:
        mock_instances = [MagicMock(id="mem1"), MagicMock(id="mem2")]
        mock_memory_class.side_effect = mock_instances

        # Mock numpy for similarity calculation
        with patch("astro_mongodb.memory.np") as mock_np:
            mock_np.array.side_effect = lambda x: x
            mock_np.linalg.norm.return_value = 1.0
            mock_np.dot.return_value = 0.9

            results = await memory.search(
                query_embedding=sample_embedding,
                limit=5,
                filter_metadata={"domain": "test"},
            )

            assert len(results) == 2
            mock_collection.find.assert_called_once()


@pytest.mark.asyncio
async def test_search_with_metadata_filter(memory, sample_embedding):
    """Test search with metadata filtering."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "mem1",
            "content": "Finance content",
            "embedding": [0.1] * 1536,
            "metadata": {"domain": "finance"},
            "timestamp": 1234567890.0,
        }
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.interfaces.memory.Memory") as mock_memory_class:
        mock_instance = MagicMock(id="mem1")
        mock_memory_class.side_effect = [mock_instance]

        with patch("astro_mongodb.memory.np") as mock_np:
            mock_np.array.side_effect = lambda x: x
            mock_np.linalg.norm.return_value = 1.0
            mock_np.dot.return_value = 0.9

            _ = await memory.search(
                query_embedding=sample_embedding,
                limit=5,
                filter_metadata={"domain": "finance"},
            )

            # Verify filter was applied
            call_args = mock_collection.find.call_args
            assert "metadata.domain" in call_args[0][0]
            assert call_args[0][0]["metadata.domain"] == "finance"


@pytest.mark.asyncio
async def test_search_no_results(memory, sample_embedding):
    """Test search when no memories match."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    results = await memory.search(query_embedding=sample_embedding, limit=5)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_atlas(sample_embedding):
    """Test search using Atlas vector search."""
    memory = MongoDBMemory(
        uri="mongodb://localhost:27017",
        database="test_astro",
        collection="memories",
        use_atlas_search=True,
        atlas_index_name="test_index",
    )

    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "mem1",
            "content": "Content 1",
            "metadata": {"domain": "test"},
            "timestamp": 1234567890.0,
            "score": 0.95,
        }
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.aggregate = MagicMock(return_value=mock_cursor)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.interfaces.memory.Memory") as mock_memory_class:
        mock_instance = MagicMock(id="mem1")
        mock_memory_class.side_effect = [mock_instance]

        results = await memory.search(
            query_embedding=sample_embedding,
            limit=5,
            filter_metadata={"domain": "test"},
        )

        assert len(results) == 1
        mock_collection.aggregate.assert_called_once()

        # Verify pipeline structure
        call_args = mock_collection.aggregate.call_args
        pipeline = call_args[0][0]
        assert len(pipeline) == 2
        assert "$vectorSearch" in pipeline[0]
        assert pipeline[0]["$vectorSearch"]["index"] == "test_index"


@pytest.mark.asyncio
async def test_delete_memory_success(memory):
    """Test deleting a memory that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await memory.delete("memory_123")

    assert result is True
    mock_collection.delete_one.assert_called_once_with({"_id": "memory_123"})


@pytest.mark.asyncio
async def test_delete_memory_not_found(memory):
    """Test deleting a memory that doesn't exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 0
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    memory._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await memory.delete("nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_delete_memory_not_initialized(memory):
    """Test deleting memory when storage not initialized."""
    with pytest.raises(RuntimeError, match="Storage not initialized"):
        await memory.delete("test")
