"""MongoDB implementation of MemoryBackend with vector search support."""

from typing import Optional, List, Dict, Any
import logging
import time

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)


class MongoDBMemory:
    """MongoDB implementation of MemoryBackend with vector search.

    Stores memory entries with vector embeddings for semantic search.
    Requires MongoDB 6.0+ with Atlas Search or vector search capabilities.

    For local development without Atlas, uses aggregation pipeline with
    cosine similarity (slower but functional).

    Args:
        uri: MongoDB connection URI
        database: Database name
        collection: Collection name for memories (default: "memories")
        use_atlas_search: Whether to use Atlas vector search (default: False)
        atlas_index_name: Name of Atlas search index (default: "memory_vector_index")

    Example:
        ```python
        # Setup
        memory = MongoDBMemory(
            uri="mongodb://localhost:27017",
            database="astro",
            collection="memories",
            use_atlas_search=False  # Use aggregation pipeline for local dev
        )
        await memory.startup()

        # Store memory
        embedding = [0.1, 0.2, 0.3, ...]  # 1536 dimensions from OpenAI
        await memory.store(
            id="memory_123",
            content="The capital of France is Paris",
            embedding=embedding,
            metadata={"domain": "geography", "importance": "high"}
        )

        # Search memories
        query_embedding = [0.15, 0.18, 0.25, ...]
        results = await memory.search(
            query_embedding=query_embedding,
            limit=5,
            filter_metadata={"domain": "geography"}
        )
        for result in results:
            print(f"{result.id}: {result.content}")

        # Retrieve specific memory
        memory_obj = await memory.retrieve("memory_123")

        # Delete memory
        deleted = await memory.delete("memory_123")

        await memory.shutdown()
        ```

    MongoDB Atlas Setup:
        For production use with Atlas vector search:
        1. Create cluster on MongoDB Atlas
        2. Create search index:
           - Index name: memory_vector_index
           - Type: Vector Search
           - Definition:
             ```json
             {
               "mappings": {
                 "dynamic": false,
                 "fields": {
                   "embedding": {
                     "type": "knnVector",
                     "dimensions": 1536,
                     "similarity": "cosine"
                   }
                 }
               }
             }
             ```
        3. Set use_atlas_search=True

    Local Development:
        For local MongoDB without Atlas:
        - Set use_atlas_search=False
        - Uses aggregation pipeline with cosine similarity
        - Slower but functional for development
    """

    def __init__(
        self,
        uri: str,
        database: str,
        collection: str = "memories",
        use_atlas_search: bool = False,
        atlas_index_name: str = "memory_vector_index",
    ) -> None:
        """Initialize MongoDB memory backend.

        Args:
            uri: MongoDB connection URI
            database: Database name
            collection: Collection name for memories (default: "memories")
            use_atlas_search: Whether to use Atlas vector search (default: False)
            atlas_index_name: Name of Atlas search index (default: "memory_vector_index")
        """
        self.uri = uri
        self.database_name = database
        self.collection_name = collection
        self.use_atlas_search = use_atlas_search
        self.atlas_index_name = atlas_index_name
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    async def startup(self) -> None:
        """Initialize storage backend.

        Establishes connection, creates indexes for:
        - _id (automatic)
        - timestamp (for time-based queries)
        - metadata fields (for filtering)

        Note: Vector search index must be created manually in Atlas UI.

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        try:
            self._client = AsyncIOMotorClient(self.uri)
            self._db = self._client[self.database_name]

            # Test connection
            await self._client.admin.command("ping")
            logger.info(f"Connected to MongoDB at {self.uri}")

            # Create indexes
            collection = self._db[self.collection_name]
            await collection.create_index(
                [("timestamp", ASCENDING)],
                background=True,
            )
            logger.info(f"Created indexes on {self.collection_name}")

            if self.use_atlas_search:
                logger.info(
                    f"Using Atlas vector search with index: {self.atlas_index_name}"
                )
            else:
                logger.info(
                    "Using aggregation pipeline for vector search (local mode)"
                )

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

    async def store(
        self,
        id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Store a memory entry with its vector embedding.

        Args:
            id: Unique memory ID
            content: Text content (may be compressed)
            embedding: Vector embedding of content
            metadata: Additional metadata (query, directives, timestamp, etc.)

        Raises:
            RuntimeError: If storage not initialized or store fails
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.collection_name]

            # Create document
            doc = {
                "_id": id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata,
                "timestamp": time.time(),
            }

            # Upsert (insert or update)
            await collection.replace_one(
                {"_id": id},
                doc,
                upsert=True,
            )

            logger.debug(f"Stored memory: {id}")

        except Exception as e:
            logger.error(f"Failed to store memory {id}: {e}")
            raise RuntimeError(f"Failed to store memory: {e}") from e

    async def retrieve(self, id: str) -> Optional[Any]:
        """Retrieve a specific memory by ID.

        Args:
            id: Unique memory identifier

        Returns:
            Memory object if found, None otherwise
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.collection_name]
            doc = await collection.find_one({"_id": id})

            if not doc:
                return None

            # Convert to Memory object
            from astro.interfaces.memory import Memory

            return Memory(
                id=doc["_id"],
                content=doc["content"],
                metadata=doc["metadata"],
                timestamp=doc["timestamp"],
            )

        except Exception as e:
            logger.error(f"Failed to retrieve memory {id}: {e}")
            raise RuntimeError(f"Failed to retrieve memory: {e}") from e

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Vector similarity search for relevant memories.

        Uses either Atlas vector search or aggregation pipeline based on
        use_atlas_search configuration.

        Args:
            query_embedding: Vector to search for
            limit: Maximum number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of memories sorted by relevance (cosine similarity)
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            if self.use_atlas_search:
                return await self._search_atlas(query_embedding, limit, filter_metadata)
            else:
                return await self._search_aggregation(
                    query_embedding, limit, filter_metadata
                )

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            raise RuntimeError(f"Failed to search memories: {e}") from e

    async def _search_atlas(
        self,
        query_embedding: List[float],
        limit: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[Any]:
        """Search using Atlas vector search ($vectorSearch).

        Requires MongoDB Atlas with vector search index created.

        Args:
            query_embedding: Vector to search for
            limit: Maximum number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of Memory objects sorted by similarity
        """
        collection = self._db[self.collection_name]

        # Build filter for metadata
        filters = {}
        if filter_metadata:
            for key, value in filter_metadata.items():
                filters[f"metadata.{key}"] = value

        # Atlas vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.atlas_index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,  # Over-fetch for better results
                    "limit": limit,
                    "filter": filters if filters else {},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "content": 1,
                    "metadata": 1,
                    "timestamp": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        cursor = collection.aggregate(pipeline)
        docs = await cursor.to_list(length=limit)

        # Convert to Memory objects
        from astro.interfaces.memory import Memory

        memories = []
        for doc in docs:
            memories.append(
                Memory(
                    id=doc["_id"],
                    content=doc["content"],
                    metadata=doc["metadata"],
                    timestamp=doc["timestamp"],
                )
            )

        logger.debug(f"Found {len(memories)} memories via Atlas search")
        return memories

    async def _search_aggregation(
        self,
        query_embedding: List[float],
        limit: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[Any]:
        """Search using Python-based cosine similarity.

        Fallback for local MongoDB without Atlas vector search.
        Fetches all documents matching filters and computes similarity in Python.

        This is not ideal for production with large datasets, but works well
        for development and small memory collections.

        Args:
            query_embedding: Vector to search for
            limit: Maximum number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of Memory objects sorted by similarity
        """
        collection = self._db[self.collection_name]

        # Build query for metadata filters
        query: Dict[str, Any] = {}
        if filter_metadata:
            for key, value in filter_metadata.items():
                query[f"metadata.{key}"] = value

        # Fetch all matching documents
        cursor = collection.find(query)
        docs = await cursor.to_list(length=None)

        if not docs:
            return []

        # Compute cosine similarity in Python
        import numpy as np

        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        # Calculate similarity scores
        scored_docs = []
        for doc in docs:
            doc_vec = np.array(doc["embedding"])
            doc_norm = np.linalg.norm(doc_vec)

            # Cosine similarity
            if query_norm > 0 and doc_norm > 0:
                similarity = np.dot(query_vec, doc_vec) / (query_norm * doc_norm)
            else:
                similarity = 0.0

            scored_docs.append((doc, float(similarity)))

        # Sort by similarity (highest first)
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        top_docs = scored_docs[:limit]

        # Convert to Memory objects
        from astro.interfaces.memory import Memory

        memories = []
        for doc, score in top_docs:
            memories.append(
                Memory(
                    id=doc["_id"],
                    content=doc["content"],
                    metadata=doc["metadata"],
                    timestamp=doc["timestamp"],
                )
            )

        logger.debug(
            f"Found {len(memories)} memories via Python cosine similarity "
            f"(top similarity: {top_docs[0][1]:.4f})"
            if top_docs
            else "Found 0 memories"
        )
        return memories

    async def delete(self, id: str) -> bool:
        """Delete a memory entry.

        Args:
            id: Unique memory identifier

        Returns:
            True if deleted, False if not found
        """
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call startup() first.")

        try:
            collection = self._db[self.collection_name]
            result = await collection.delete_one({"_id": id})

            deleted = result.deleted_count > 0
            if deleted:
                logger.debug(f"Deleted memory: {id}")
            else:
                logger.debug(f"Memory not found: {id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete memory {id}: {e}")
            raise RuntimeError(f"Failed to delete memory: {e}") from e
