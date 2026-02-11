# astro-mongodb

MongoDB storage adapters for Astro V2.

## Overview

This package provides MongoDB implementations of Astro's storage protocols:

- **MongoDBCoreStorage**: Implements `CoreStorageBackend` for Layer 1 primitives (Directives)
- **MongoDBOrchestrationStorage**: Implements `OrchestrationStorageBackend` for Layer 2 primitives (Stars, Constellations, Runs)
- **MongoDBMemory**: Implements `MemoryBackend` for long-term memory with vector search

## Requirements

- **Python 3.10+**
- **MongoDB 6.0+** (required for vector search support)
- **Motor 3.0+** (async MongoDB driver)

### MongoDB Vector Search Setup

For the `MongoDBMemory` adapter to work properly, you need MongoDB 6.0+ with vector search capabilities:

#### MongoDB Atlas (Recommended)
1. Create a cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a search index for the memories collection:
   - Index name: `memory_vector_index`
   - Type: Vector Search
   - Field: `embedding`
   - Dimensions: Match your embedding model (e.g., 1536 for OpenAI text-embedding-3-small)
   - Similarity: cosine

#### Self-Hosted MongoDB 6.0+
If running MongoDB locally, you need:
- MongoDB 6.0 or later
- Atlas Search enabled (requires special build or Atlas)

**Note**: Vector search using `$vectorSearch` is only available in Atlas or Enterprise versions. For local development, the adapter will fall back to cosine similarity using aggregation pipelines, which is slower but functional.

## Installation

```bash
# Install from PyPI (when published)
pip install astro-mongodb

# Or install from source
cd astro-mongodb
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

## Usage

### Basic Setup

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

# Startup backends (creates indexes, etc.)
await core_storage.startup()
await orch_storage.startup()
await memory.startup()
```

### With Astro Core

```python
from astro.core.registry import Registry
from astro_mongodb import MongoDBCoreStorage

# Wire up storage
storage = MongoDBCoreStorage(
    uri="mongodb://localhost:27017",
    database="astro"
)
await storage.startup()

# Use with Registry
registry = Registry(storage=storage)

# Create and save a directive
from astro.core.models.directive import Directive

directive = Directive(
    id="financial_analysis",
    name="Financial Analysis",
    description="Analyze financial data and trends",
    content="You are a financial analyst...",
    probe_ids=["search_web", "analyze_data"],
)

saved_directive = await registry.create_directive(directive)
```

### With Orchestration

```python
from astro.orchestration.runner import ConstellationRunner
from astro_mongodb import MongoDBCoreStorage, MongoDBOrchestrationStorage

# Wire up storage
core_storage = MongoDBCoreStorage(
    uri="mongodb://localhost:27017",
    database="astro"
)
orch_storage = MongoDBOrchestrationStorage(
    uri="mongodb://localhost:27017",
    database="astro"
)

await core_storage.startup()
await orch_storage.startup()

# Use with ConstellationRunner
runner = ConstellationRunner(
    core_storage=core_storage,
    orchestration_storage=orch_storage,
)

# Execute constellation
run = await runner.execute(
    constellation_id="market_research",
    variables={"company": "Tesla"}
)
```

### With Memory (Second Brain)

```python
from astro.core.memory import LongTermMemory
from astro.interfaces.embedding import EmbeddingProvider
from astro_mongodb import MongoDBMemory

# Setup memory backend
memory_backend = MongoDBMemory(
    uri="mongodb://localhost:27017",
    database="astro",
    collection="memories"
)
await memory_backend.startup()

# Setup embedding provider (e.g., OpenAI)
embedding_provider = OpenAIEmbeddingProvider(
    model="text-embedding-3-small"
)

# Create long-term memory
long_term = LongTermMemory(
    backend=memory_backend,
    embedding_provider=embedding_provider,
)

# Store memory
embedding = await embedding_provider.embed("Important fact about France")
await memory_backend.store(
    id="memory_123",
    content="The capital of France is Paris",
    embedding=embedding,
    metadata={"domain": "geography", "importance": "high"}
)

# Search memories
query_embedding = await embedding_provider.embed("What is France's capital?")
results = await memory_backend.search(
    query_embedding=query_embedding,
    limit=5,
    filter_metadata={"domain": "geography"}
)
for memory in results:
    print(f"{memory.id}: {memory.content}")
```

## Configuration

### Connection URI

All adapters accept a MongoDB connection URI. Common formats:

```python
# Local MongoDB
uri = "mongodb://localhost:27017"

# MongoDB Atlas
uri = "mongodb+srv://username:password@cluster.mongodb.net/"

# Replica set
uri = "mongodb://host1:27017,host2:27017/?replicaSet=myReplicaSet"

# With authentication
uri = "mongodb://username:password@localhost:27017/"
```

### Database and Collections

By default, adapters use the following collections:

| Adapter | Collection(s) |
|---------|---------------|
| `MongoDBCoreStorage` | `directives` |
| `MongoDBOrchestrationStorage` | `stars`, `constellations`, `runs` |
| `MongoDBMemory` | `memories` (configurable) |

All collections are created automatically with appropriate indexes.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=astro_mongodb --cov-report=term-missing

# Run specific test file
pytest tests/test_core_storage.py -v
```

### Code Quality

```bash
# Format code
black astro_mongodb/ tests/

# Lint
ruff check astro_mongodb/ tests/

# Type check
mypy astro_mongodb/
```

## Architecture

### Collection Schemas

#### Directives Collection
```json
{
  "_id": "financial_analysis",
  "name": "Financial Analysis",
  "description": "Analyze financial data",
  "content": "You are a financial analyst...",
  "probe_ids": ["search_web", "analyze_data"],
  "reference_ids": [],
  "template_variables": [],
  "metadata": {"domain": "finance", "author": "astrix"}
}
```

#### Stars Collection
```json
{
  "_id": "analyst_1",
  "name": "Financial Analyst",
  "type": "worker",
  "directive_id": "financial_analysis",
  "probe_ids": ["search_web"],
  "config": {"max_tokens": 2000, "temperature": 0.7}
}
```

#### Constellations Collection
```json
{
  "_id": "market_research",
  "name": "Market Research",
  "description": "Research market conditions",
  "start": {"id": "start", "type": "start"},
  "end": {"id": "end", "type": "end"},
  "nodes": [...],
  "edges": [...]
}
```

#### Runs Collection
```json
{
  "_id": "run_abc123",
  "constellation_id": "market_research",
  "status": "completed",
  "variables": {"company": "Tesla"},
  "outputs": {...},
  "created_at": "2026-02-10T12:00:00Z",
  "completed_at": "2026-02-10T12:05:00Z",
  "duration_seconds": 300
}
```

#### Memories Collection
```json
{
  "_id": "memory_123",
  "content": "The capital of France is Paris",
  "embedding": [0.123, -0.456, 0.789, ...],
  "metadata": {"domain": "geography", "importance": "high"},
  "timestamp": 1707566400.0
}
```

## Performance Considerations

### Indexes

The adapters automatically create these indexes:

- **Directives**: `metadata.domain`, `metadata.author`
- **Stars**: `type`
- **Constellations**: None (small collections)
- **Runs**: `constellation_id`, `status`, `created_at`
- **Memories**: `timestamp`, vector search index on `embedding`

### Vector Search Performance

For best performance with `MongoDBMemory`:

1. Use MongoDB Atlas with proper vector search indexes
2. Keep embedding dimensions reasonable (1536 is optimal for OpenAI)
3. Use metadata filters to reduce search space
4. Limit result count to what you actually need (default: 5)

### Connection Pooling

Motor automatically manages connection pooling. For high-load scenarios:

```python
storage = MongoDBCoreStorage(
    uri="mongodb://localhost:27017/?maxPoolSize=50",
    database="astro"
)
```

## Troubleshooting

### Vector Search Not Working

**Error**: "Vector search index not found"

**Solution**: Create the search index in Atlas:
1. Go to Atlas UI -> Search -> Create Search Index
2. Use JSON editor with this configuration:
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

### Connection Timeout

**Error**: "ServerSelectionTimeoutError"

**Solutions**:
- Check MongoDB is running: `mongosh`
- Verify connection URI
- Check network/firewall settings
- For Atlas, verify IP whitelist

### Import Errors

**Error**: "cannot import name 'MongoDBCoreStorage'"

**Solutions**:
- Ensure astro-mongodb is installed: `pip install -e .`
- Ensure astro core is installed: `pip install astro`
- Check Python path includes the package

## License

MIT

## Contributing

See the main [Astro repository](https://github.com/astrix-labs/astro) for contribution guidelines.
