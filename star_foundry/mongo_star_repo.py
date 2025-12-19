"""MongoDB repository implementation for Star entities.

This module provides a MongoDB-based repository for persisting and retrieving
Star objects, handling the conversion between Pydantic models and MongoDB documents.
"""

from pymongo import MongoClient
from pymongo.collection import Collection
from typing import List, Optional
from pydantic import ValidationError

from star_foundry import Star


class MongoStarRepository:
    """Repository for managing Star entities in MongoDB.

    This class provides CRUD operations for Star objects, handling the
    conversion between Pydantic models and MongoDB documents.

    Attributes:
        client: MongoDB client instance
        db: Database instance
        collection: Collection instance for stars
    """

    def __init__(self, uri: str, db_name: str, collection_name: str = "stars"):
        """Initialize the MongoDB repository.

        Args:
            uri: MongoDB connection URI
            db_name: Name of the database to use
            collection_name: Name of the collection (defaults to 'stars')
        """
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection: Collection = self.db[collection_name]
        self.collection.create_index("_id", unique=True)

    def _to_model(self, data) -> Star:
        """Convert a MongoDB document to a Star model.

        Args:
            data: MongoDB document dictionary

        Returns:
            Star instance
        """
        # Convert Mongo dict → Star Pydantic model
        data["id"] = data["_id"]
        del data["_id"]
        return Star(**data)

    def find_all(self) -> List[Star]:
        """Retrieve all stars from the database.

        Returns:
            List of all Star instances
        """
        docs = self.collection.find({})
        return [self._to_model(d) for d in docs]

    def find_by_id(self, star_id: str) -> Optional[Star]:
        """Find a star by its unique ID.

        Args:
            star_id: The unique identifier of the star

        Returns:
            Star instance if found, None otherwise
        """
        doc = self.collection.find_one({"_id": star_id})
        return self._to_model(doc) if doc else None

    def save(self, star: Star) -> None:
        """Save or update a star in the database.

        Args:
            star: Star instance to save

        Raises:
            ValueError: If the star data is invalid
        """
        # Validate model before writing to Mongo
        try:
            # Use Pydantic v2 `model_dump()` when available; fall back to `dict()` for v1 compatibility
            if hasattr(star, "model_dump"):
                star_dict = star.model_dump()
            else:
                star_dict = star.dict()

            star_dict["_id"] = star_dict["id"]
            del star_dict["id"]
        except ValidationError as e:
            raise ValueError(f"Invalid Star: {e}")

        self.collection.replace_one({"_id": star_dict["_id"]}, star_dict, upsert=True)

    def delete(self, star_id: str) -> None:
        """Delete a star from the database.

        Args:
            star_id: The unique identifier of the star to delete
        """
        self.collection.delete_one({"_id": star_id})
