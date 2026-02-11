"""Tests for MongoDBOrchestrationStorage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from astro_mongodb.orchestration_storage import MongoDBOrchestrationStorage


@pytest.fixture
def mock_star():
    """Create a mock Star object."""

    class MockStar:
        def __init__(self):
            self.id = "test_star"
            self.name = "Test Star"
            self.type = "worker"
            self.directive_id = "test_directive"
            self.probe_ids = ["test_probe"]
            self.config = {"max_tokens": 1000}
            self.metadata = {}

        def model_dump(self):
            return {
                "id": self.id,
                "name": self.name,
                "type": self.type,
                "directive_id": self.directive_id,
                "probe_ids": self.probe_ids,
                "config": self.config,
                "metadata": self.metadata,
            }

    return MockStar()


@pytest.fixture
def mock_constellation():
    """Create a mock Constellation object."""

    class MockConstellation:
        def __init__(self):
            self.id = "test_constellation"
            self.name = "Test Constellation"
            self.description = "Test description"
            self.start = {"id": "start", "type": "start"}
            self.end = {"id": "end", "type": "end"}
            self.nodes = []
            self.edges = []
            self.metadata = {}

        def model_dump(self):
            return {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "start": self.start,
                "end": self.end,
                "nodes": self.nodes,
                "edges": self.edges,
                "metadata": self.metadata,
            }

    return MockConstellation()


@pytest.fixture
def mock_run():
    """Create a mock Run object."""

    class MockRun:
        def __init__(self):
            self.id = "test_run"
            self.constellation_id = "test_constellation"
            self.constellation_name = "Test Constellation"
            self.status = "running"
            self.variables = {}
            self.started_at = datetime.utcnow()
            self.node_outputs = {}

        def model_dump(self):
            return {
                "id": self.id,
                "constellation_id": self.constellation_id,
                "constellation_name": self.constellation_name,
                "status": self.status,
                "variables": self.variables,
                "started_at": self.started_at,
                "node_outputs": self.node_outputs,
            }

    return MockRun()


@pytest.fixture
def storage():
    """Create MongoDBOrchestrationStorage instance."""
    return MongoDBOrchestrationStorage(
        uri="mongodb://localhost:27017", database="test_astro"
    )


@pytest.mark.asyncio
async def test_startup_success(storage):
    """Test successful startup."""
    with patch(
        "astro_mongodb.orchestration_storage.AsyncIOMotorClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_db = MagicMock()

        mock_client.admin.command = AsyncMock(return_value={})
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        # Mock collections
        mock_stars_collection = MagicMock()
        mock_runs_collection = MagicMock()
        mock_stars_collection.create_index = AsyncMock()
        mock_runs_collection.create_index = AsyncMock()

        def get_collection(name):
            if name == "stars":
                return mock_stars_collection
            elif name == "runs":
                return mock_runs_collection
            return MagicMock()

        mock_db.__getitem__ = get_collection

        mock_client_class.return_value = mock_client

        await storage.startup()

        assert storage._client is not None
        assert storage._db is not None
        mock_client.admin.command.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_save_star(storage, mock_star):
    """Test saving a star."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.replace_one = AsyncMock()

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.save_star(mock_star)

    assert result == mock_star
    mock_collection.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_star_found(storage):
    """Test getting a star that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    doc = {
        "_id": "test_star",
        "name": "Test Star",
        "type": "worker",
        "directive_id": "test_directive",
        "config": {},
        "metadata": {},
    }
    mock_collection.find_one = AsyncMock(return_value=doc)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.orchestration.stars.base.BaseStar") as mock_star_class:
        mock_instance = MagicMock()
        mock_star_class.return_value = mock_instance
        result = await storage.get_star("test_star")

        assert result == mock_instance
        mock_collection.find_one.assert_called_once_with({"_id": "test_star"})


@pytest.mark.asyncio
async def test_get_star_not_found(storage):
    """Test getting a star that doesn't exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.get_star("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_stars_no_filter(storage):
    """Test listing all stars."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "star1",
            "name": "Star 1",
            "type": "worker",
            "directive_id": "dir1",
            "config": {},
            "metadata": {},
        },
        {
            "_id": "star2",
            "name": "Star 2",
            "type": "planning",
            "directive_id": "dir2",
            "config": {},
            "metadata": {},
        },
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.orchestration.stars.base.BaseStar") as mock_star_class:
        mock_instances = [MagicMock(id="star1"), MagicMock(id="star2")]
        mock_star_class.side_effect = mock_instances
        results = await storage.list_stars()

        assert len(results) == 2
        mock_collection.find.assert_called_once_with({})


@pytest.mark.asyncio
async def test_list_stars_with_filter(storage):
    """Test listing stars with type filter."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "star1",
            "name": "Star 1",
            "type": "worker",
            "directive_id": "dir1",
            "config": {},
            "metadata": {},
        }
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.orchestration.stars.base.BaseStar") as mock_star_class:
        mock_instance = MagicMock(id="star1")
        mock_star_class.side_effect = [mock_instance]
        results = await storage.list_stars(filter_type="worker")

        assert len(results) == 1
        mock_collection.find.assert_called_once_with({"type": "worker"})


@pytest.mark.asyncio
async def test_delete_star_success(storage):
    """Test deleting a star that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.delete_star("test_star")
    assert result is True


@pytest.mark.asyncio
async def test_delete_star_not_found(storage):
    """Test deleting a star that doesn't exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 0
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.delete_star("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_save_constellation(storage, mock_constellation):
    """Test saving a constellation."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.replace_one = AsyncMock()

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.save_constellation(mock_constellation)

    assert result == mock_constellation
    mock_collection.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_constellation_found(storage):
    """Test getting a constellation that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    doc = {
        "_id": "test_constellation",
        "name": "Test",
        "description": "Test",
        "start": {"id": "start", "type": "start"},
        "end": {"id": "end", "type": "end"},
        "nodes": [],
        "edges": [],
        "metadata": {},
        "max_loop_iterations": 3,
        "max_retry_attempts": 3,
        "retry_delay_base": 2.0,
    }
    mock_collection.find_one = AsyncMock(return_value=doc)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch(
        "astro_mongodb.orchestration_storage.Constellation"
    ) as mock_constellation_class:
        mock_instance = MagicMock()
        mock_constellation_class.return_value = mock_instance
        result = await storage.get_constellation("test_constellation")

        assert result == mock_instance
        mock_collection.find_one.assert_called_once_with({"_id": "test_constellation"})


@pytest.mark.asyncio
async def test_list_constellations(storage):
    """Test listing all constellations."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "const1",
            "name": "Const 1",
            "description": "Test 1",
            "start": {"id": "start", "type": "start"},
            "end": {"id": "end", "type": "end"},
            "nodes": [],
            "edges": [],
            "metadata": {},
            "max_loop_iterations": 3,
            "max_retry_attempts": 3,
            "retry_delay_base": 2.0,
        }
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch(
        "astro_mongodb.orchestration_storage.Constellation"
    ) as mock_constellation_class:
        mock_instance = MagicMock(id="const1")
        mock_constellation_class.side_effect = [mock_instance]
        results = await storage.list_constellations()

        assert len(results) == 1
        mock_collection.find.assert_called_once_with({})


@pytest.mark.asyncio
async def test_delete_constellation_success(storage):
    """Test deleting a constellation that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_result = MagicMock()
    mock_result.deleted_count = 1
    mock_collection.delete_one = AsyncMock(return_value=mock_result)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.delete_constellation("test_constellation")
    assert result is True


@pytest.mark.asyncio
async def test_save_run(storage, mock_run):
    """Test saving a run."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.replace_one = AsyncMock()

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    result = await storage.save_run(mock_run)

    assert result == mock_run
    mock_collection.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_run_found(storage):
    """Test getting a run that exists."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    doc = {
        "_id": "test_run",
        "constellation_id": "test_constellation",
        "constellation_name": "Test",
        "status": "running",
        "variables": {},
        "started_at": datetime.utcnow(),
        "node_outputs": {},
    }
    mock_collection.find_one = AsyncMock(return_value=doc)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.orchestration.runner.run.Run") as mock_run_class:
        mock_instance = MagicMock()
        mock_run_class.return_value = mock_instance
        result = await storage.get_run("test_run")

        assert result == mock_instance
        mock_collection.find_one.assert_called_once_with({"_id": "test_run"})


@pytest.mark.asyncio
async def test_list_runs_no_filter(storage):
    """Test listing runs without constellation filter."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = [
        {
            "_id": "run1",
            "constellation_id": "const1",
            "constellation_name": "Const 1",
            "status": "completed",
            "variables": {},
            "started_at": datetime.utcnow(),
            "node_outputs": {},
        }
    ]

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    with patch("astro.orchestration.runner.run.Run") as mock_run_class:
        mock_instance = MagicMock(id="run1")
        mock_run_class.side_effect = [mock_instance]
        results = await storage.list_runs()

        assert len(results) == 1
        mock_collection.find.assert_called_once_with({})


@pytest.mark.asyncio
async def test_list_runs_with_constellation_filter(storage):
    """Test listing runs for specific constellation."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = []

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    results = await storage.list_runs(constellation_id="test_constellation")

    assert len(results) == 0
    mock_collection.find.assert_called_once_with(
        {"constellation_id": "test_constellation"}
    )


@pytest.mark.asyncio
async def test_list_runs_with_limit(storage):
    """Test listing runs with custom limit."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    docs = []

    mock_cursor.to_list = AsyncMock(return_value=docs)
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    storage._db = mock_db
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    results = await storage.list_runs(limit=50)

    mock_cursor.limit.assert_called_once_with(50)
