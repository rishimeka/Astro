"""MongoDB implementation of CoreStorageBackend for Layer 1 primitives."""

from typing import Optional, List, Dict, Any
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure

logger = logging.getLogger(__name__)


class MongoDBCoreStorage:
    """MongoDB implementation of CoreStorageBackend.

    Stores Directive objects in MongoDB with full CRUD support.
    Automatically creates indexes for common query patterns.

    Args:
        uri: MongoDB connection URI
        database: Database name
        collection: Collection name for directives (default: "directives")

    Example:
        ```python
        storage = MongoDBCoreStorage(
            uri="mongodb://localhost:27017",
            database="astro",
            collection="directives"
        )
        await storage.startup()

        # Save directive
        directive = Directive(id="test", name="Test", description="...", content="...")
        saved = await storage.save_directive(directive)

        # Retrieve directive
        retrieved = await storage.get_directive("test")

        # List all directives
        all_directives = await storage.list_directives()

        # List with metadata filter
        finance_directives = await storage.list_directives(
            filter_metadata={"domain": "finance"}
        )

        # Delete directive
        deleted = await storage.delete_directive("test")

        await storage.shutdown()
        ```
    """

    def __init__(
        self,
        uri: str,
        database: str,
        collection: str = "directives",
    ) -> None:
        """Initialize MongoDB core storage.

        Args:
            uri: MongoDB connection URI
            database: Database name
            collection: Collection name for directives (default: "directives")
        """
        self.uri = uri
        self.database_name = database
        self.collection_name = collection
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    async def startup(self) -> None:
        """Initialize storage backend.

        Establishes connection, creates indexes for:
        - _id (automatic)
        - metadata.domain
        - metadata.author

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        try:
            self._client = AsyncIOMotorClient(self.uri)
            self._db = self._client[self.database_name]

            # Test connection
            await self._client.admin.command("ping")
            logger.info(f"Connected to MongoDB at {self.uri}")

            # Create indexes for common queries
            collection = self._db[self.collection_name]
            await collection.create_index(
                [("metadata.domain", ASCENDING)],
                background=True,
            )
            await collection.create_index(
                [("metadata.author", ASCENDING)],
                background=True,
            )
            logger.info(f"Created indexes on {self.collection_name}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionError(f"Unable to connect to MongoDB at {self.uri}") from e
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            raise

    async def shutdown(self) -> None:
        """Cleanup storage backend.

        Closes MongoDB connection. Safe to call multiple times.
        """
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Closed MongoDB connection")

    async def save_directive(self, directive: Any) -> Any:
        """Save or update a directive.

        If directive.id exists in database, updates it. Otherwise creates new.
        Uses upsert to handle both create and update cases.

        Args:
            directive: Directive object to save

        Returns:
            Saved directive (same object, no modifications)

        Raises:
            ValueError: If directive is invalid
            RuntimeError: If save fails

        Example:
            ```python
            directive = Directive(
                id="financial_analysis",
                name="Financial Analysis",
                description="Analyze financial data",
                content="You are a financial analyst...",
                probe_ids=["search_web", "analyze_data"],
            )
            saved = await storage.save_directive(directive)
            ```
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            # Convert Pydantic model to dict
            directive_dict = directive.model_dump()

            # Use _id instead of id for MongoDB
            directive_dict["_id"] = directive_dict.pop("id")

            collection = self._db[self.collection_name]

            # Upsert (insert or update)
            await collection.replace_one(
                {"_id": directive_dict["_id"]},
                directive_dict,
                upsert=True,
            )

            logger.debug(f"Saved directive: {directive.id}")
            return directive

        except Exception as e:
            logger.error(f"Failed to save directive {directive.id}: {e}")
            raise RuntimeError(f"Failed to save directive: {e}") from e

    async def get_directive(self, directive_id: str) -> Optional[Any]:
        """Retrieve directive by ID.

        Args:
            directive_id: Unique identifier for directive

        Returns:
            Directive object if found, None otherwise

        Example:
            ```python
            directive = await storage.get_directive("financial_analysis")
            if directive:
                print(f"Found: {directive.name}")
            else:
                print("Not found")
            ```
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.collection_name]
            doc = await collection.find_one({"_id": directive_id})

            if not doc:
                return None

            # Convert MongoDB doc to Directive
            # Import here to avoid circular dependency
            from astro.core.models.directive import Directive

            # Convert _id back to id
            doc["id"] = doc.pop("_id")

            return Directive(**doc)

        except Exception as e:
            logger.error(f"Failed to get directive {directive_id}: {e}")
            raise RuntimeError(f"Failed to get directive: {e}") from e

    async def list_directives(
        self,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """List all directives, optionally filtered by metadata.

        Args:
            filter_metadata: Optional metadata filters (e.g., {"domain": "finance"})
                           Supports simple equality matching on metadata fields

        Returns:
            List of directive objects matching filter

        Example:
            ```python
            # Get all directives
            all_directives = await storage.list_directives()

            # Get only finance directives
            finance = await storage.list_directives(
                filter_metadata={"domain": "finance"}
            )

            # Multiple filters
            specific = await storage.list_directives(
                filter_metadata={"domain": "finance", "author": "alice"}
            )
            ```
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.collection_name]

            # Build query
            query: Dict[str, Any] = {}
            if filter_metadata:
                # Add metadata filters with dot notation
                for key, value in filter_metadata.items():
                    query[f"metadata.{key}"] = value

            # Fetch documents
            cursor = collection.find(query)
            docs = await cursor.to_list(length=None)

            # Convert to Directive objects
            from astro.core.models.directive import Directive

            directives = []
            for doc in docs:
                doc["id"] = doc.pop("_id")
                directives.append(Directive(**doc))

            logger.debug(f"Listed {len(directives)} directives")
            return directives

        except Exception as e:
            logger.error(f"Failed to list directives: {e}")
            raise RuntimeError(f"Failed to list directives: {e}") from e

    async def delete_directive(self, directive_id: str) -> bool:
        """Delete a directive.

        Args:
            directive_id: ID of directive to delete

        Returns:
            True if directive was deleted, False if not found

        Example:
            ```python
            deleted = await storage.delete_directive("old_directive")
            if deleted:
                print("Deleted successfully")
            else:
                print("Directive not found")
            ```
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.collection_name]
            result = await collection.delete_one({"_id": directive_id})

            deleted = result.deleted_count > 0
            if deleted:
                logger.debug(f"Deleted directive: {directive_id}")
            else:
                logger.debug(f"Directive not found: {directive_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete directive {directive_id}: {e}")
            raise RuntimeError(f"Failed to delete directive: {e}") from e
