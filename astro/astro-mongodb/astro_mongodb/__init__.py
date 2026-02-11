"""MongoDB storage adapters for Astro.

This package provides MongoDB implementations of Astro's storage protocols:
- MongoDBCoreStorage: CoreStorageBackend implementation for directives
- MongoDBOrchestrationStorage: OrchestrationStorageBackend implementation for stars/constellations/runs
- MongoDBMemory: MemoryBackend implementation with vector search

Requirements:
- MongoDB 6.0+ for vector search support
- Motor (async MongoDB driver)

Example usage:
    ```python
    from astro_mongodb import MongoDBCoreStorage, MongoDBOrchestrationStorage, MongoDBMemory

    # Initialize storage backends
    core_storage = MongoDBCoreStorage(
        uri="mongodb://localhost:27017",
        database="astro"
    )
    orch_storage = MongoDBOrchestrationStorage(
        uri="mongodb://localhost:27017",
        database="astro"
    )
    memory = MongoDBMemory(
        uri="mongodb://localhost:27017",
        database="astro",
        collection="memories"
    )

    # Start backends
    await core_storage.startup()
    await orch_storage.startup()
    await memory.startup()

    # Use with Astro
    registry = Registry(storage=core_storage)
    runner = ConstellationRunner(
        core_storage=core_storage,
        orchestration_storage=orch_storage
    )
    ```
"""

from astro_mongodb.core_storage import MongoDBCoreStorage
from astro_mongodb.memory import MongoDBMemory
from astro_mongodb.orchestration_storage import MongoDBOrchestrationStorage

__version__ = "2.0.0"

__all__ = [
    "MongoDBCoreStorage",
    "MongoDBOrchestrationStorage",
    "MongoDBMemory",
]
