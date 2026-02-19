"""MongoDB implementation of OrchestrationStorageBackend for Layer 2 primitives."""

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)


class MongoDBOrchestrationStorage:
    """MongoDB implementation of OrchestrationStorageBackend.

    Stores Stars, Constellations, and Runs in MongoDB with full CRUD support.
    Automatically creates indexes for common query patterns.

    Args:
        uri: MongoDB connection URI
        database: Database name
        stars_collection: Collection name for stars (default: "stars")
        constellations_collection: Collection name for constellations (default: "constellations")
        runs_collection: Collection name for runs (default: "runs")

    Example:
        ```python
        storage = MongoDBOrchestrationStorage(
            uri="mongodb://localhost:27017",
            database="astro"
        )
        await storage.startup()

        # Save star
        star = WorkerStar(id="analyst_1", name="Analyst", ...)
        saved = await storage.save_star(star)

        # Save constellation
        constellation = Constellation(id="research", name="Research", ...)
        saved = await storage.save_constellation(constellation)

        # Save run
        run = Run(id="run_123", constellation_id="research", ...)
        saved = await storage.save_run(run)

        # Query runs
        runs = await storage.list_runs(constellation_id="research", limit=10)

        await storage.shutdown()
        ```
    """

    def __init__(
        self,
        uri: str,
        database: str,
        stars_collection: str = "stars",
        constellations_collection: str = "constellations",
        runs_collection: str = "runs",
    ) -> None:
        """Initialize MongoDB orchestration storage.

        Args:
            uri: MongoDB connection URI
            database: Database name
            stars_collection: Collection name for stars (default: "stars")
            constellations_collection: Collection name for constellations (default: "constellations")
            runs_collection: Collection name for runs (default: "runs")
        """
        self.uri = uri
        self.database_name = database
        self.stars_collection_name = stars_collection
        self.constellations_collection_name = constellations_collection
        self.runs_collection_name = runs_collection
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def startup(self) -> None:
        """Initialize storage backend.

        Establishes connection, creates indexes for:
        Stars:
        - _id (automatic)
        - type

        Constellations:
        - _id (automatic)

        Runs:
        - _id (automatic)
        - constellation_id
        - status
        - started_at (descending for recent-first queries)

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        try:
            self._client = AsyncIOMotorClient(self.uri)
            self._db = self._client[self.database_name]

            # Test connection
            await self._client.admin.command("ping")
            logger.info(f"Connected to MongoDB at {self.uri}")

            # Create indexes for stars
            stars_collection = self._db[self.stars_collection_name]
            await stars_collection.create_index(
                [("type", ASCENDING)],
                background=True,
            )

            # Create indexes for runs (most important for queries)
            runs_collection = self._db[self.runs_collection_name]
            await runs_collection.create_index(
                [("constellation_id", ASCENDING)],
                background=True,
            )
            await runs_collection.create_index(
                [("status", ASCENDING)],
                background=True,
            )
            await runs_collection.create_index(
                [("started_at", DESCENDING)],
                background=True,
            )

            logger.info("Created indexes on orchestration collections")

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

    # Stars (Layer 2)

    async def save_star(self, star: Any) -> Any:
        """Save or update a star.

        If star.id exists in database, updates it. Otherwise creates new.
        Uses upsert to handle both create and update cases.

        Args:
            star: Star object to save (WorkerStar, PlanningStar, etc.)

        Returns:
            Saved star (same object, no modifications)

        Raises:
            ValueError: If star is invalid
            RuntimeError: If save fails
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            # Convert Pydantic model to dict
            star_dict = star.model_dump()

            # Use _id instead of id for MongoDB
            star_dict["_id"] = star_dict.pop("id")

            collection = self._db[self.stars_collection_name]

            # Upsert (insert or update)
            await collection.replace_one(
                {"_id": star_dict["_id"]},
                star_dict,
                upsert=True,
            )

            logger.debug(f"Saved star: {star.id}")
            return star

        except Exception as e:
            logger.error(f"Failed to save star {star.id}: {e}")
            raise RuntimeError(f"Failed to save star: {e}") from e

    async def get_star(self, star_id: str) -> Any | None:
        """Retrieve star by ID.

        Args:
            star_id: Unique identifier for star

        Returns:
            Star object if found, None otherwise
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.stars_collection_name]
            doc = await collection.find_one({"_id": star_id})

            if not doc:
                return None

            # Convert _id back to id
            doc["id"] = doc.pop("_id")

            # Reconstruct the correct concrete star type based on the 'type' field
            star_type = doc.get("type", "worker")
            from astro.orchestration.stars import (
                DocExStar,
                EvalStar,
                ExecutionStar,
                PlanningStar,
                SynthesisStar,
                WorkerStar,
            )
            from astro.orchestration.stars.base import BaseStar

            type_map = {
                "worker": WorkerStar,
                "eval": EvalStar,
                "synthesis": SynthesisStar,
                "planning": PlanningStar,
                "execution": ExecutionStar,
                "docex": DocExStar,
            }
            star_cls = type_map.get(star_type, BaseStar)
            return star_cls(**doc)

        except Exception as e:
            logger.error(f"Failed to get star {star_id}: {e}")
            raise RuntimeError(f"Failed to get star: {e}") from e

    async def list_stars(
        self,
        filter_type: str | None = None,
    ) -> list[Any]:
        """List all stars, optionally filtered by type.

        Args:
            filter_type: Optional star type filter (e.g., "worker", "planning")

        Returns:
            List of star objects matching filter
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.stars_collection_name]

            # Build query
            query: dict = {}
            if filter_type:
                query["type"] = filter_type

            # Fetch documents
            cursor = collection.find(query)
            docs = await cursor.to_list(length=None)

            # Convert to concrete Star objects based on type field
            from astro.orchestration.stars import (
                DocExStar,
                EvalStar,
                ExecutionStar,
                PlanningStar,
                SynthesisStar,
                WorkerStar,
            )
            from astro.orchestration.stars.base import BaseStar

            type_map = {
                "worker": WorkerStar,
                "eval": EvalStar,
                "synthesis": SynthesisStar,
                "planning": PlanningStar,
                "execution": ExecutionStar,
                "docex": DocExStar,
            }

            stars = []
            for doc in docs:
                doc["id"] = doc.pop("_id")
                star_cls = type_map.get(doc.get("type", "worker"), BaseStar)
                stars.append(star_cls(**doc))

            logger.debug(f"Listed {len(stars)} stars")
            return stars

        except Exception as e:
            logger.error(f"Failed to list stars: {e}")
            raise RuntimeError(f"Failed to list stars: {e}") from e

    async def delete_star(self, star_id: str) -> bool:
        """Delete a star.

        Args:
            star_id: ID of star to delete

        Returns:
            True if star was deleted, False if not found
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.stars_collection_name]
            result = await collection.delete_one({"_id": star_id})

            deleted = result.deleted_count > 0
            if deleted:
                logger.debug(f"Deleted star: {star_id}")
            else:
                logger.debug(f"Star not found: {star_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete star {star_id}: {e}")
            raise RuntimeError(f"Failed to delete star: {e}") from e

    # Constellations (Layer 2)

    async def save_constellation(
        self,
        constellation: Any,
    ) -> Any:
        """Save or update a constellation.

        If constellation.id exists in database, updates it. Otherwise creates new.
        Uses upsert to handle both create and update cases.

        Args:
            constellation: Constellation object to save

        Returns:
            Saved constellation (same object, no modifications)

        Raises:
            ValueError: If constellation is invalid
            RuntimeError: If save fails
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            # Convert Pydantic model to dict
            constellation_dict = constellation.model_dump()

            # Use _id instead of id for MongoDB
            constellation_dict["_id"] = constellation_dict.pop("id")

            collection = self._db[self.constellations_collection_name]

            # Upsert (insert or update)
            await collection.replace_one(
                {"_id": constellation_dict["_id"]},
                constellation_dict,
                upsert=True,
            )

            logger.debug(f"Saved constellation: {constellation.id}")
            return constellation

        except Exception as e:
            logger.error(f"Failed to save constellation {constellation.id}: {e}")
            raise RuntimeError(f"Failed to save constellation: {e}") from e

    async def get_constellation(
        self,
        constellation_id: str,
    ) -> Any | None:
        """Retrieve constellation by ID.

        Args:
            constellation_id: Unique identifier for constellation

        Returns:
            Constellation object if found, None otherwise
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.constellations_collection_name]
            doc = await collection.find_one({"_id": constellation_id})

            if not doc:
                return None

            # Convert MongoDB doc to Constellation
            from astro.orchestration.models.constellation import Constellation

            # Convert _id back to id
            doc["id"] = doc.pop("_id")

            return Constellation(**doc)

        except Exception as e:
            logger.error(f"Failed to get constellation {constellation_id}: {e}")
            raise RuntimeError(f"Failed to get constellation: {e}") from e

    async def list_constellations(self) -> list[Any]:
        """List all constellations.

        Returns:
            List of all constellation objects
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.constellations_collection_name]

            # Fetch documents
            cursor = collection.find({})
            docs = await cursor.to_list(length=None)

            # Convert to Constellation objects
            from astro.orchestration.models.constellation import Constellation

            constellations = []
            for doc in docs:
                doc["id"] = doc.pop("_id")
                constellations.append(Constellation(**doc))

            logger.debug(f"Listed {len(constellations)} constellations")
            return constellations

        except Exception as e:
            logger.error(f"Failed to list constellations: {e}")
            raise RuntimeError(f"Failed to list constellations: {e}") from e

    async def delete_constellation(self, constellation_id: str) -> bool:
        """Delete a constellation.

        Args:
            constellation_id: ID of constellation to delete

        Returns:
            True if constellation was deleted, False if not found
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.constellations_collection_name]
            result = await collection.delete_one({"_id": constellation_id})

            deleted = result.deleted_count > 0
            if deleted:
                logger.debug(f"Deleted constellation: {constellation_id}")
            else:
                logger.debug(f"Constellation not found: {constellation_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete constellation {constellation_id}: {e}")
            raise RuntimeError(f"Failed to delete constellation: {e}") from e

    # Runs (execution history - Layer 2)

    async def save_run(self, run: Any) -> Any:
        """Save or update a run.

        Runs are execution records for constellation executions. They capture:
        - Status (running, awaiting_confirmation, completed, failed, cancelled)
        - Outputs from each node
        - Timestamps and duration
        - Error information if failed

        Args:
            run: Run object to save

        Returns:
            Saved run (same object, no modifications)

        Raises:
            ValueError: If run is invalid
            RuntimeError: If save fails
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            # Convert Pydantic model to dict
            run_dict = run.model_dump()

            # Use _id instead of id for MongoDB
            run_dict["_id"] = run_dict.pop("id")

            collection = self._db[self.runs_collection_name]

            # Upsert (insert or update)
            await collection.replace_one(
                {"_id": run_dict["_id"]},
                run_dict,
                upsert=True,
            )

            logger.debug(f"Saved run: {run.id}")
            return run

        except Exception as e:
            logger.error(f"Failed to save run {run.id}: {e}")
            raise RuntimeError(f"Failed to save run: {e}") from e

    async def get_run(self, run_id: str) -> Any | None:
        """Retrieve run by ID.

        Args:
            run_id: Unique identifier for run

        Returns:
            Run object if found, None otherwise
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.runs_collection_name]
            doc = await collection.find_one({"_id": run_id})

            if not doc:
                return None

            # Convert MongoDB doc to Run
            # Try V2 import first, fallback to V1
            try:
                from astro.orchestration.runner.run import Run
            except ImportError:
                from astro.orchestration.runner.run import Run

            # Convert _id back to id
            doc["id"] = doc.pop("_id")

            return Run(**doc)

        except Exception as e:
            logger.error(f"Failed to get run {run_id}: {e}")
            raise RuntimeError(f"Failed to get run: {e}") from e

    async def list_runs(
        self,
        constellation_id: str | None = None,
        limit: int = 100,
    ) -> list[Any]:
        """List runs, optionally filtered by constellation.

        Args:
            constellation_id: Optional filter by constellation
            limit: Maximum number of runs to return (default 100)

        Returns:
            List of runs, most recent first
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.runs_collection_name]

            # Build query
            query: dict = {}
            if constellation_id:
                query["constellation_id"] = constellation_id

            # Fetch documents (most recent first)
            cursor = collection.find(query).sort("started_at", DESCENDING).limit(limit)
            docs = await cursor.to_list(length=limit)

            # Convert to Run objects
            # Try V2 import first, fallback to V1
            try:
                from astro.orchestration.runner.run import Run
            except ImportError:
                from astro.orchestration.runner.run import Run

            runs = []
            for doc in docs:
                doc["id"] = doc.pop("_id")
                runs.append(Run(**doc))

            logger.debug(f"Listed {len(runs)} runs")
            return runs

        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            raise RuntimeError(f"Failed to list runs: {e}") from e
