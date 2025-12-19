"""Tests for star_foundry.mongo_star_repo module."""

from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from pymongo.collection import Collection
from star_foundry.star import Star
from star_foundry.mongo_star_repo import MongoStarRepository


class TestMongoStarRepository:
    """Test suite for the MongoStarRepository class."""

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_repository_initialization(self, mock_mongo_client):
        """Test MongoStarRepository initialization."""
        mock_db = MagicMock()
        mock_collection = Mock(spec=Collection)
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(
            uri="mongodb://localhost:27017",
            db_name="test_db",
            collection_name="test_stars",
        )

        assert repo.client == mock_client_instance
        assert repo.db == mock_db
        assert repo.collection == mock_collection
        mock_collection.create_index.assert_called_once_with("_id", unique=True)

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_repository_default_collection_name(self, mock_mongo_client):
        """Test that default collection name is 'stars'."""
        mock_db = MagicMock()
        mock_collection = Mock(spec=Collection)
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.return_value = mock_client_instance

        MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        # Verify the default collection name was used
        mock_db.__getitem__.assert_called_with("stars")

    def test_to_model_conversion(self):
        """Test converting MongoDB document to Star model."""
        with patch("star_foundry.mongo_star_repo.MongoClient"):
            repo = MongoStarRepository(
                uri="mongodb://localhost:27017", db_name="test_db"
            )

            now = datetime.now()
            mongo_doc = {
                "_id": "star1",
                "name": "Test Star",
                "description": "Test description",
                "content": "Test content",
                "references": ["star2"],
                "probes": ["probe1"],
                "created_on": now,
                "updated_on": now,
            }

            star = repo._to_model(mongo_doc)

            assert isinstance(star, Star)
            assert star.id == "star1"
            assert star.name == "Test Star"
            assert star.description == "Test description"
            assert star.content == "Test content"
            assert star.references == ["star2"]
            assert star.probes == ["probe1"]
            assert star.created_on == now
            assert star.updated_on == now

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_find_all_empty(self, mock_mongo_client):
        """Test finding all stars when database is empty."""
        mock_collection = Mock(spec=Collection)
        mock_collection.find.return_value = []

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        stars = repo.find_all()

        assert stars == []
        mock_collection.find.assert_called_once_with({})

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_find_all_with_stars(self, mock_mongo_client):
        """Test finding all stars when database has data."""
        now = datetime.now()
        mock_docs = [
            {
                "_id": "star1",
                "name": "Star 1",
                "description": "Test",
                "content": "Content",
                "references": [],
                "probes": [],
                "created_on": now,
                "updated_on": now,
            },
            {
                "_id": "star2",
                "name": "Star 2",
                "description": "Test",
                "content": "Content",
                "references": [],
                "probes": [],
                "created_on": now,
                "updated_on": now,
            },
        ]

        mock_collection = Mock(spec=Collection)
        mock_collection.find.return_value = mock_docs

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        stars = repo.find_all()

        assert len(stars) == 2
        assert all(isinstance(star, Star) for star in stars)
        assert stars[0].id == "star1"
        assert stars[1].id == "star2"

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_find_by_id_exists(self, mock_mongo_client):
        """Test finding a star by ID when it exists."""
        now = datetime.now()
        mock_doc = {
            "_id": "star1",
            "name": "Test Star",
            "description": "Test",
            "content": "Content",
            "references": [],
            "probes": [],
            "created_on": now,
            "updated_on": now,
        }

        mock_collection = Mock(spec=Collection)
        mock_collection.find_one.return_value = mock_doc

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        star = repo.find_by_id("star1")

        assert star is not None
        assert isinstance(star, Star)
        assert star.id == "star1"
        assert star.name == "Test Star"
        mock_collection.find_one.assert_called_once_with({"_id": "star1"})

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_find_by_id_not_exists(self, mock_mongo_client):
        """Test finding a star by ID when it doesn't exist."""
        mock_collection = Mock(spec=Collection)
        mock_collection.find_one.return_value = None

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        star = repo.find_by_id("nonexistent")

        assert star is None
        mock_collection.find_one.assert_called_once_with({"_id": "nonexistent"})

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_save_new_star(self, mock_mongo_client):
        """Test saving a new star to the database."""
        mock_collection = Mock(spec=Collection)
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        repo.save(star)

        mock_collection.replace_one.assert_called_once()
        call_args = mock_collection.replace_one.call_args

        assert call_args[0][0] == {"_id": "star1"}
        assert call_args[1]["upsert"] is True

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_save_updates_existing_star(self, mock_mongo_client):
        """Test that save updates an existing star (upsert behavior)."""
        mock_collection = Mock(spec=Collection)
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        now = datetime.now()
        star = Star(
            id="star1",
            name="Updated Star",
            description="Updated",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        repo.save(star)

        call_args = mock_collection.replace_one.call_args
        assert call_args[1]["upsert"] is True

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_delete_star(self, mock_mongo_client):
        """Test deleting a star from the database."""
        mock_collection = Mock(spec=Collection)
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        repo.delete("star1")

        mock_collection.delete_one.assert_called_once_with({"_id": "star1"})

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_save_preserves_references_and_probes(self, mock_mongo_client):
        """Test that save preserves references and probes."""
        mock_collection = Mock(spec=Collection)
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            references=["star2", "star3"],
            probes=["probe1", "probe2"],
            created_on=now,
            updated_on=now,
        )

        repo.save(star)

        call_args = mock_collection.replace_one.call_args
        saved_doc = call_args[0][1]

        assert saved_doc["references"] == ["star2", "star3"]
        assert saved_doc["probes"] == ["probe1", "probe2"]

    @patch("star_foundry.mongo_star_repo.MongoClient")
    def test_save_converts_id_to_mongo_id(self, mock_mongo_client):
        """Test that save converts 'id' field to '_id' for MongoDB."""
        mock_collection = Mock(spec=Collection)
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client_instance

        repo = MongoStarRepository(uri="mongodb://localhost:27017", db_name="test_db")

        now = datetime.now()
        star = Star(
            id="star1",
            name="Test Star",
            description="Test",
            content="Content",
            created_on=now,
            updated_on=now,
        )

        repo.save(star)

        call_args = mock_collection.replace_one.call_args
        saved_doc = call_args[0][1]

        assert "_id" in saved_doc
        assert "id" not in saved_doc
        assert saved_doc["_id"] == "star1"
