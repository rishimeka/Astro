"""Tests for MongoDBCoreStorage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from astro_mongodb.core_storage import MongoDBCoreStorage


@pytest.fixture
def mock_directive():
    """Create a mock Directive object."""

    class MockDirective:
        def __init__(self):
            self.id = "test_directive"
            self.name = "Test Directive"
            self.description = "A test directive"
            self.content = "Test content"
            self.probe_ids = ["test_probe"]
            self.reference_ids = []
            self.template_variables = []
            self.metadata = {"domain": "test"}

        def model_dump(self):
            return {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "content": self.content,
                "probe_ids": self.probe_ids,
                "reference_ids": self.reference_ids,
                "template_variables": self.template_variables,
                "metadata": self.metadata,
            }

    return MockDirective()


@pytest.fixture
def storage():
    """Create MongoDBCoreStorage instance."""
    return MongoDBCoreStorage(
        uri="mongodb://localhost:27017", database="test_astro", collection="directives"
    )


@pytest.mark.asyncio
async def test_startup_success(storage):
    """Test successful startup."""
    with patch(
        "astro_mongodb.core_storage.AsyncIOMotorClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_client.admin.command = AsyncMock(return_value={})
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_collection.create_index = AsyncMock()

        mock_client_class.return_value = mock_client

        await storage.startup()

        assert storage._client is not None
        assert storage._db is not None
        mock_client.admin.command.assert_called_once_with("ping")
        assert mock_collection.create_index.call_count == 2


@pytest.mark.asyncio
async def test_startup_connection_failure(storage):
    """Test startup with connection failure."""
    with patch("astro_mongodb.core_storage.AsyncIOMotorClient") as mock_client_class:
        from pymongo.errors import ConnectionFailure

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=ConnectionFailure("Test"))
        mock_client_class.return_value = mock_client

        with pytest.raises(ConnectionError):
            await storage.startup()


@pytest.mark.asyncio
async def test_shutdown(storage):
    """Test shutdown."""
    mock_client = MagicMock()
    storage._client = mock_client

    await storage.shutdown()

    mock_client.close.assert_called_once()
    assert storage._client is None
    assert storage._db is None


@pytest.mark.asyncio
async def test_save_directive(storage, mock_directive):
    """Test saving a directive."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.replace_one = AsyncMock()

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.save_directive(mock_directive)

    assert result == mock_directive
    mock_collection.replace_one.assert_called_once()

    # Verify _id was used
    call_args = mock_collection.replace_one.call_args
    assert call_args[0][0] == {"_id": "test_directive"}
    assert call_args[0][1]["_id"] == "test_directive"
    assert "id" not in call_args[0][1]


@pytest.mark.asyncio
async def test_save_directive_not_initialized(storage, mock_directive):
    """Test saving directive when storage not initialized."""
    with pytest.raises(RuntimeError, match="Storage not initialized"):
        await storage.save_directive(mock_directive)


@pytest.mark.asyncio
async def test_get_directive_found(storage):
    """Test getting a directive that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    doc = {
        "_id": "test_directive",
        "name": "Test Directive",
        "description": "Test",
        "content": "Content",
        "probe_ids": [],
        "reference_ids": [],
        "template_variables": [],
        "metadata": {},
    }
    mock_collection.find_one = AsyncMock(return_value=doc)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.core.models.directive.Directive") as mock_directive_class:
        mock_instance = MagicMock()
        mock_directive_class.return_value = mock_instance
        result = await storage.get_directive("test_directive")

        assert result == mock_instance
        mock_collection.find_one.assert_called_once_with({"_id": "test_directive"})

        # Verify id was converted back from _id
        call_args = mock_directive_class.call_args
        assert call_args is not None
        # Check keyword arguments
        kwargs = call_args[1] if len(call_args) > 1 else call_args.kwargs
        assert "id" in kwargs
        assert "_id" not in kwargs


@pytest.mark.asyncio
async def test_get_directive_not_found(storage):
    """Test getting a directive that doesn't exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.get_directive("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_directives_no_filter(storage):
    """Test listing all directives."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "dir1",
            "name": "Dir 1",
            "description": "Test 1",
            "content": "Content 1",
            "probe_ids": [],
            "reference_ids": [],
            "template_variables": [],
            "metadata": {"domain": "test"},
        },
        {
            "_id": "dir2",
            "name": "Dir 2",
            "description": "Test 2",
            "content": "Content 2",
            "probe_ids": [],
            "reference_ids": [],
            "template_variables": [],
            "metadata": {"domain": "finance"},
        },
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.core.models.directive.Directive") as mock_directive_class:
        # Create mock instances for each directive
        mock_instances = [MagicMock(id="dir1"), MagicMock(id="dir2")]
        mock_directive_class.side_effect = mock_instances

        results = await storage.list_directives()

        assert len(results) == 2
        mock_collection.find.assert_called_once_with({})


@pytest.mark.asyncio
async def test_list_directives_with_filter(storage):
    """Test listing directives with metadata filter."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "dir1",
            "name": "Dir 1",
            "description": "Test 1",
            "content": "Content 1",
            "probe_ids": [],
            "reference_ids": [],
            "template_variables": [],
            "metadata": {"domain": "finance"},
        }
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.core.models.directive.Directive") as mock_directive_class:
        mock_instance = MagicMock(id="dir1")
        mock_directive_class.side_effect = [mock_instance]

        results = await storage.list_directives(filter_metadata={"domain": "finance"})

        assert len(results) == 1
        mock_collection.find.assert_called_once_with({"metadata.domain": "finance"})


@pytest.mark.asyncio
async def test_list_directives_multiple_filters(storage):
    """Test listing directives with multiple metadata filters."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    await storage.list_directives(
        filter_metadata={"domain": "finance", "author": "alice"}
    )

    mock_collection.find.assert_called_once_with(
        {"metadata.domain": "finance", "metadata.author": "alice"}
    )


@pytest.mark.asyncio
async def test_delete_directive_success(storage):
    """Test deleting a directive that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.delete_directive("test_directive")

    assert result is True
    mock_collection.delete_one.assert_called_once_with({"_id": "test_directive"})


@pytest.mark.asyncio
async def test_delete_directive_not_found(storage):
    """Test deleting a directive that doesn't exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 0
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.delete_directive("nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_delete_directive_not_initialized(storage):
    """Test deleting directive when storage not initialized."""
    with pytest.raises(RuntimeError, match="Storage not initialized"):
        await storage.delete_directive("test")
