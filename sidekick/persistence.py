"""Sidekick Persistence Layer for MongoDB.

Handles async writes to MongoDB with retry logic and fallback.
"""

from typing import Optional, List, Dict, Any
import logging

from sidekick.models.traces import ExecutionTrace
from sidekick.config import SidekickConfig, get_config

logger = logging.getLogger(__name__)


class SidekickPersistence:
    """Persistence layer for Sidekick traces.

    Uses MongoDB with async writes via motor.
    Gracefully handles connection failures.
    """

    def __init__(self, config: Optional[SidekickConfig] = None):
        self._config = config or get_config()
        self._client = None
        self._db = None
        self._traces_collection = None
        self._connected = False

    async def _ensure_connected(self) -> bool:
        """Lazy connection to MongoDB.

        Returns True if connected successfully, False otherwise.
        """
        if self._connected:
            return True

        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            self._client = AsyncIOMotorClient(
                self._config.mongodb_uri,
                serverSelectionTimeoutMS=5000,
            )
            self._db = self._client[self._config.database_name]
            self._traces_collection = self._db[self._config.traces_collection]

            # Create indexes
            await self._traces_collection.create_index("trace_id", unique=True)
            await self._traces_collection.create_index("timestamp")
            await self._traces_collection.create_index("status")
            await self._traces_collection.create_index("original_query")

            self._connected = True
            return True
        except ImportError:
            logger.error("motor not installed. Run: pip install motor")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    async def save_trace(self, trace: ExecutionTrace) -> bool:
        """Save an execution trace to MongoDB.

        Returns True if saved successfully, False otherwise.
        """
        if not await self._ensure_connected():
            return False

        try:
            # Use model_dump for Pydantic v2 compatibility
            trace_dict = trace.model_dump()
            await self._traces_collection.insert_one(trace_dict)
            return True
        except Exception as e:
            logger.error(f"Failed to save trace {trace.trace_id}: {e}")
            raise

    async def update_trace(self, trace: ExecutionTrace) -> bool:
        """Update an existing trace in MongoDB.

        Returns True if updated successfully, False otherwise.
        """
        if not await self._ensure_connected():
            return False

        try:
            trace_dict = trace.model_dump()
            await self._traces_collection.replace_one(
                {"trace_id": trace.trace_id},
                trace_dict,
                upsert=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update trace {trace.trace_id}: {e}")
            return False

    async def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a trace by ID."""
        if not await self._ensure_connected():
            return None

        try:
            doc = await self._traces_collection.find_one({"trace_id": trace_id})
            if doc:
                doc.pop("_id", None)  # Remove MongoDB _id
                return ExecutionTrace(**doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get trace {trace_id}: {e}")
            return None

    async def get_recent_traces(
        self,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> List[ExecutionTrace]:
        """Get recent traces, optionally filtered by status."""
        if not await self._ensure_connected():
            return []

        try:
            query: Dict[str, Any] = {}
            if status:
                query["status"] = status

            cursor = (
                self._traces_collection.find(query).sort("timestamp", -1).limit(limit)
            )
            traces = []
            async for doc in cursor:
                doc.pop("_id", None)
                traces.append(ExecutionTrace(**doc))
            return traces
        except Exception as e:
            logger.error(f"Failed to get recent traces: {e}")
            return []

    async def search_traces(
        self,
        query_text: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[ExecutionTrace]:
        """Search traces with various filters."""
        if not await self._ensure_connected():
            return []

        try:
            query: Dict[str, Any] = {}

            if query_text:
                query["original_query"] = {"$regex": query_text, "$options": "i"}

            if status:
                query["status"] = status

            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date
                if end_date:
                    query["timestamp"]["$lte"] = end_date

            cursor = (
                self._traces_collection.find(query)
                .sort("timestamp", -1)
                .skip(offset)
                .limit(limit)
            )

            traces = []
            async for doc in cursor:
                doc.pop("_id", None)
                traces.append(ExecutionTrace(**doc))
            return traces
        except Exception as e:
            logger.error(f"Failed to search traces: {e}")
            return []

    async def delete_trace(self, trace_id: str) -> bool:
        """Delete a trace by ID."""
        if not await self._ensure_connected():
            return False

        try:
            result = await self._traces_collection.delete_one({"trace_id": trace_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete trace {trace_id}: {e}")
            return False

    async def get_traces_for_nebula(
        self,
        trace_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a trace formatted for Nebula input.

        Returns the trace plus all Star content used.
        """
        trace = await self.get_trace(trace_id)
        if not trace:
            return None

        # Return trace in Nebula-compatible format
        return {
            "execution_trace": trace.model_dump(),
            "stars": trace.stars_used,
        }

    async def count_traces(
        self,
        status: Optional[str] = None,
    ) -> int:
        """Count total traces, optionally filtered by status."""
        if not await self._ensure_connected():
            return 0

        try:
            query: Dict[str, Any] = {}
            if status:
                query["status"] = status
            return await self._traces_collection.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count traces: {e}")
            return 0

    async def cleanup_old_traces(self) -> int:
        """Delete traces older than retention period.

        Returns number of deleted traces.
        """
        if not await self._ensure_connected():
            return 0

        try:
            from datetime import datetime, timedelta

            cutoff = datetime.utcnow() - timedelta(
                days=self._config.trace_retention_days
            )
            result = await self._traces_collection.delete_many(
                {"timestamp": {"$lt": cutoff}}
            )
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old traces: {e}")
            return 0

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._connected = False
