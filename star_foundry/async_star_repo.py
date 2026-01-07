"""Async MongoDB repository implementation for Star entities.

This module provides an async MongoDB-based repository for persisting and
retrieving Star objects using the motor async driver.
"""

from typing import List, Optional
from pydantic import ValidationError

from star_foundry.star import Star

try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    AsyncIOMotorClient = None
    AsyncIOMotorCollection = None


class AsyncMongoStarRepository:
    """Async repository for managing Star entities in MongoDB.

    This class provides async CRUD operations for Star objects, handling the
    conversion between Pydantic models and MongoDB documents.

    Requires the 'motor' package to be installed.
    """

    def __init__(self, uri: str, db_name: str, collection_name: str = "stars"):
        """Initialize the async MongoDB repository.

        Args:
            uri: MongoDB connection URI
            db_name: Name of the database to use
            collection_name: Name of the collection (defaults to 'stars')

        Raises:
            ImportError: If motor is not installed
        """
        if not MOTOR_AVAILABLE:
            raise ImportError(
                "motor package is required for async MongoDB operations. "
                "Install it with: pip install motor"
            )

        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection: AsyncIOMotorCollection = self.db[collection_name]
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize indexes and verify connection.

        Should be called once after creating the repository.
        """
        if self._initialized:
            return

        await self.collection.create_index("_id", unique=True)
        self._initialized = True

    def _to_model(self, data: dict) -> Star:
        """Convert a MongoDB document to a Star model.

        Args:
            data: MongoDB document dictionary

        Returns:
            Star instance
        """
        data = data.copy()
        data["id"] = data.pop("_id")
        return Star(**data)

    def _to_document(self, star: Star) -> dict:
        """Convert a Star model to a MongoDB document.

        Args:
            star: Star instance

        Returns:
            MongoDB document dictionary
        """
        if hasattr(star, "model_dump"):
            star_dict = star.model_dump()
        else:
            star_dict = star.dict()

        star_dict["_id"] = star_dict.pop("id")

        # Remove runtime-only fields that shouldn't be persisted
        runtime_fields = [
            "resolved_references",
            "resolved_probes",
            "missing_references",
            "missing_probes",
        ]
        for field in runtime_fields:
            star_dict.pop(field, None)

        return star_dict

    async def find_all(self) -> List[Star]:
        """Retrieve all stars from the database.

        Returns:
            List of all Star instances
        """
        stars = []
        async for doc in self.collection.find({}):
            stars.append(self._to_model(doc))
        return stars

    async def find_by_id(self, star_id: str) -> Optional[Star]:
        """Find a star by its unique ID.

        Args:
            star_id: The unique identifier of the star

        Returns:
            Star instance if found, None otherwise
        """
        doc = await self.collection.find_one({"_id": star_id})
        return self._to_model(doc) if doc else None

    async def find_by_ids(self, star_ids: List[str]) -> List[Star]:
        """Find multiple stars by their IDs.

        Args:
            star_ids: List of star IDs to retrieve

        Returns:
            List of Star instances found
        """
        stars = []
        async for doc in self.collection.find({"_id": {"$in": star_ids}}):
            stars.append(self._to_model(doc))
        return stars

    async def find_by_name(self, name: str) -> Optional[Star]:
        """Find a star by its name.

        Args:
            name: The name of the star

        Returns:
            Star instance if found, None otherwise
        """
        doc = await self.collection.find_one({"name": name})
        return self._to_model(doc) if doc else None

    async def save(self, star: Star) -> None:
        """Save or update a star in the database.

        Args:
            star: Star instance to save

        Raises:
            ValueError: If the star data is invalid
        """
        try:
            star_dict = self._to_document(star)
        except ValidationError as e:
            raise ValueError(f"Invalid Star: {e}")

        await self.collection.replace_one(
            {"_id": star_dict["_id"]}, star_dict, upsert=True
        )

    async def delete(self, star_id: str) -> bool:
        """Delete a star from the database.

        Args:
            star_id: The unique identifier of the star to delete

        Returns:
            True if a star was deleted, False otherwise
        """
        result = await self.collection.delete_one({"_id": star_id})
        return result.deleted_count > 0

    async def count(self) -> int:
        """Count the total number of stars.

        Returns:
            Total count of stars in the collection
        """
        return await self.collection.count_documents({})

    async def close(self) -> None:
        """Close the database connection."""
        self.client.close()
