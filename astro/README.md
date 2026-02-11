# Astro

Modular Python package for AI infrastructure and multi-agent orchestration.

## Overview

Astro provides a clean, layered architecture for building AI-powered applications with multi-agent workflows. The package is organized into four layers with strict dependency rules enforced via import linting.

## Package Structure

```
astro/
├── astro/                      # Main source package
│   ├── interfaces/             # Layer 0: Pure protocols
│   ├── core/                   # Layer 1: Foundation components
│   ├── orchestration/          # Layer 2: Multi-agent workflows
│   └── launchpad/              # Layer 3: Chat interface
├── astro-api/                  # FastAPI application
├── astro-mongodb/              # MongoDB storage adapters
├── tests/                      # Test suite
├── scripts/                    # Utility scripts
├── pyproject.toml              # Package metadata
└── requirements.txt            # Dependencies
```

## Installation

### From Source (Development)

```bash
# Clone and navigate to astro directory
cd astro

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install core package
pip install -e .

# Install API server
cd astro-api && pip install -e . && cd ..

# Install MongoDB adapters
cd astro-mongodb && pip install -e . && cd ..

# Install all dependencies
pip install -r requirements.txt
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs: pytest, pytest-asyncio, black, ruff, mypy, import-linter

## Architecture

Astro uses a 4-layer architecture with strict import rules:

```
Layer 3: Launchpad (Conversational Interface)
    ↓
Layer 2: Orchestration (Multi-Agent Workflows)
    ↓
Layer 1: Core (Foundation Components)
    ↓
Layer 0: Interfaces (Pure Protocols)
```

### Layer 0: Interfaces (`astro/interfaces/`)

Pure protocol definitions with no implementations. Enables pluggable infrastructure.

**Exports**:
- `CoreStorageBackend` - Protocol for storing directives
- `OrchestrationStorageBackend` - Protocol for storing stars, constellations, runs
- `LLMProvider` - Protocol for LLM inference
- `EmbeddingProvider` - Protocol for generating embeddings
- `MemoryBackend` - Protocol for long-term memory storage

**Dependencies**: None

**Example**:
```python
from astro.interfaces import CoreStorageBackend, LLMProvider

# Implement custom storage
class MyStorage(CoreStorageBackend):
    async def get_directive(self, directive_id: str) -> Directive:
        ...
```

### Layer 1: Core (`astro/core/`)

Foundation components for prompts, tools, and memory.

**Modules**:
- `models/` - Pydantic models (Directive, TemplateVariable, ToolCall, WorkerOutput)
- `probes/` - Tool decorator and registry
- `registry/` - Directive registry with validation
- `runtime/` - Execution context and events
- `memory/` - Context window, long-term memory, Second Brain
- `llm/` - LLM utilities

**Exports**:
```python
from astro.core import (
    # Models
    Directive, TemplateVariable, ToolCall, WorkerOutput,
    # Probes
    Probe, ProbeRegistry, probe, DuplicateProbeError,
    # Runtime
    ExecutionContext,
    # Memory
    ContextWindow, LongTermMemory, SecondBrain, Message,
)
```

**Dependencies**: Layer 0 (interfaces)

**Example**:
```python
from astro.core import probe, Probe
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query")

@probe(
    name="search_web",
    description="Search the web for information",
)
async def search_web(query: str) -> str:
    # Implementation
    return results
```

### Layer 2: Orchestration (`astro/orchestration/`)

Multi-agent workflow execution with parallel coordination.

**Modules**:
- `models/` - Constellation, Star, Node, Edge models
- `stars/` - Star implementations (Worker, Synthesis, Planning, Eval)
- `runner/` - ConstellationRunner (orchestration engine)
- `context.py` - Runtime execution context
- `validation.py` - Workflow validation

**Exports**:
```python
from astro.orchestration import (
    # Models
    Constellation, StarNode, Edge, StartNode, EndNode, StarType,
    # Stars
    BaseStar, WorkerStar, SynthesisStar, PlanningStar, EvalStar,
    # Runner
    ConstellationRunner, Run, NodeOutput,
    # Context
    ConstellationContext,
)
```

**Dependencies**: Layers 0-1

**Example**:
```python
from astro.orchestration import ConstellationRunner

runner = ConstellationRunner(
    core_storage=core_storage,
    orchestration_storage=orch_storage,
)

run = await runner.execute(
    constellation_id="market_research",
    variables={"company": "Tesla"}
)
```

### Layer 3: Launchpad (`astro/launchpad/`)

Conversational interface that routes between zero-shot (fast) and constellation (thorough) execution modes.

**Modules**:
- `controller.py` - LaunchpadController (mode routing)
- `conversation.py` - Conversation and message models
- `interpreter.py` - Directive selection for zero-shot
- `running_agent.py` - Single-agent ReAct executor
- `matching.py` - Constellation matching
- `synthesis.py` - Response synthesis
- `pipelines/` - Zero-shot and constellation pipelines

**Exports**:
```python
from astro.launchpad import (
    LaunchpadController, Response,
    Conversation, Message,
    ZeroShotPipeline, ConstellationPipeline,
    Interpreter, RunningAgent,
)
```

**Dependencies**: Layers 0-2

**Example**:
```python
from astro.launchpad import LaunchpadController, Conversation

controller = LaunchpadController(
    zero_shot_pipeline=zero_shot_pipeline,
    constellation_pipeline=constellation_pipeline,
)

conversation = Conversation()

# Default: zero-shot mode (fast)
response = await controller.handle_message(
    "What is Tesla's stock price?",
    conversation
)

# Research mode: constellation (thorough)
response = await controller.handle_message(
    "Analyze Tesla's financial performance",
    conversation,
    research_mode=True,
)
```

## Key Concepts

### Directives

Modular prompt units that contain instructions and tool bindings.

**Structure**:
```python
from astro.core import Directive

directive = Directive(
    id="financial_analysis",
    name="Financial Analysis",
    description="Analyze financial data and trends",
    content="You are a financial analyst. Use your tools to research...",
    probe_ids=["search_web", "analyze_data"],
    reference_ids=[],  # Other directives to include
    template_variables=[],  # Variables for substitution
)
```

**Important**: Never use `@probe:` syntax in the `content` field. Use natural language instead. The `probe_ids` array is sufficient for tool binding.

### Probes

Function decorators that convert Python functions into LLM-callable tools.

**Definition**:
```python
from astro.core import probe
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="What to search for")
    limit: int = Field(default=10, description="Max results")

@probe(
    name="search_web",
    description="Search the web for current information",
)
async def search_web(query: str, limit: int = 10) -> str:
    # Tool implementation
    return search_results

# Register probe
from astro.core import ProbeRegistry
registry = ProbeRegistry()
registry.register(search_web)
```

**Access**:
```python
# Get probe object
probe_obj = registry.get("search_web")

# Convert to LangChain tool
langchain_tool = probe_obj.to_langchain_tool()
```

### Stars

Execution units in a constellation workflow.

**Types**:
- **Worker**: Executes a directive with tools (single-agent)
- **Synthesis**: Aggregates outputs from upstream stars
- **Planning**: Plans multi-step tasks
- **Execution**: Executes planned steps
- **Eval**: Evaluates quality of outputs
- **DocEx**: Document extraction and processing

**Example**:
```python
from astro.orchestration import WorkerStar

star = WorkerStar(
    id="analyst_1",
    name="Financial Analyst",
    directive_id="financial_analysis",
    probe_ids=["search_web", "analyze_data"],
    config={
        "max_tokens": 2000,
        "temperature": 0.7,
    }
)
```

### Constellations

Directed acyclic graphs (DAGs) that define multi-agent workflows.

**Structure**:
```python
from astro.orchestration import Constellation, StarNode, Edge

constellation = Constellation(
    id="market_research",
    name="Market Research",
    description="Research market conditions and trends",
    start=StartNode(id="start", type="start"),
    end=EndNode(id="end", type="end"),
    nodes=[
        StarNode(id="analyst_1", star_id="analyst_1"),
        StarNode(id="analyst_2", star_id="analyst_2"),
        StarNode(id="synthesis", star_id="synthesis_1"),
    ],
    edges=[
        Edge(source="start", target="analyst_1"),
        Edge(source="start", target="analyst_2"),
        Edge(source="analyst_1", target="synthesis"),
        Edge(source="analyst_2", target="synthesis"),
        Edge(source="synthesis", target="end"),
    ],
    template_variables=[
        TemplateVariable(name="company", description="Company to research")
    ],
)
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `MONGO_URI` | MongoDB connection string (default: `mongodb://localhost:27017`) |
| `MONGO_DB` | Database name (default: `astro`) |

### LLM Providers (at least one required)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models |
| `OPENAI_API_KEY` | OpenAI API key for GPT models |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |

## Development

### Running Tests

```bash
# All tests
pytest

# Specific layer
pytest tests/core/
pytest tests/orchestration/
pytest tests/launchpad/

# With coverage
pytest --cov=astro --cov-report=term-missing

# Async tests (auto mode)
pytest --asyncio-mode=auto
```

### Code Quality

```bash
# Format code
black astro/ tests/

# Lint
ruff check astro/ tests/

# Type check
mypy astro/

# Sort imports
isort astro/ tests/
```

### Import Linting

Enforce layer boundaries:

```bash
lint-imports
```

This verifies:
- Layer 3 only imports from layers 0-2
- Layer 2 only imports from layers 0-1
- Layer 1 only imports from layer 0
- Layer 0 has no internal imports

Configuration in `.importlinter`:
```ini
[importlinter]
root_package = astro
include_external_packages = True

[importlinter:contract:1]
name = Layer 0 (interfaces) is independent
type = independence
modules =
    astro.interfaces

[importlinter:contract:2]
name = Layer 1 (core) can only import from Layer 0
type = layers
layers =
    astro.core
    astro.interfaces

# ... etc
```

## Usage Examples

### Example 1: Zero-Shot Execution (Fast)

```python
from astro.launchpad import ZeroShotPipeline, Conversation
from astro.core import SecondBrain
from astro_mongodb import MongoDBCoreStorage

# Setup storage
storage = MongoDBCoreStorage(
    uri="mongodb://localhost:27017",
    database="astro"
)
await storage.startup()

# Setup memory
memory = SecondBrain(
    context_window_size=10,
    long_term_memory=None,  # Optional
)

# Create pipeline
pipeline = ZeroShotPipeline(
    storage=storage,
    probe_registry=probe_registry,
    memory=memory,
)

# Execute
conversation = Conversation()
result = await pipeline.execute(
    query="What is Tesla's current stock price?",
    conversation=conversation,
)

print(result.response)
```

### Example 2: Constellation Execution (Thorough)

```python
from astro.launchpad import ConstellationPipeline
from astro.orchestration import ConstellationRunner

# Setup runner
runner = ConstellationRunner(
    core_storage=core_storage,
    orchestration_storage=orch_storage,
)

# Create pipeline
pipeline = ConstellationPipeline(
    runner=runner,
    storage=orch_storage,
    memory=memory,
)

# Execute
result = await pipeline.execute(
    query="Analyze Tesla's financial performance over the last year",
    conversation=conversation,
)

print(result.response)
print(result.run_id)  # Access to full run details
```

### Example 3: Custom Probe Registration

```python
from astro.core import ProbeRegistry, probe

# Create registry
registry = ProbeRegistry()

# Define and register probes
@probe(name="custom_tool", description="My custom tool")
async def custom_tool(arg: str) -> str:
    return f"Processed: {arg}"

registry.register(custom_tool)

# Use in directive
directive = Directive(
    id="custom_workflow",
    content="Use your custom tool to process the input.",
    probe_ids=["custom_tool"],
)
```

## Troubleshooting

### Import Errors

**Problem**: `ImportError: cannot import name 'Directive'`

**Solution**:
```bash
# Ensure package is installed in editable mode
pip install -e .

# Verify installation
python -c "from astro.core import Directive; print('OK')"
```

### Layer Boundary Violations

**Problem**: `lint-imports` reports violations

**Solution**:
- Review the import in the error message
- Move code to appropriate layer
- Use dependency injection instead of direct imports across layers

### Tool Calls Not Working

**Problem**: LLM outputs `@probe:tool_name` as text instead of calling functions

**Solution**:
- Remove all `@probe:` references from directive `content`
- Use natural language: "Use your available tools to search"
- Verify `probe_ids` array is populated
- Check ProbeRegistry has the probe registered

### MongoDB Connection Issues

**Problem**: `ServerSelectionTimeoutError`

**Solution**:
```bash
# Verify MongoDB is running
mongosh

# Check environment variables
echo $MONGO_URI

# Test connection
python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    print(await client.server_info())

asyncio.run(test())
"
```

## Production Deployment

### Package Distribution

```bash
# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install packages
COPY astro/ astro/
RUN pip install -e ./astro

COPY astro-api/ astro-api/
RUN pip install -e ./astro-api

COPY astro-mongodb/ astro-mongodb/
RUN pip install -e ./astro-mongodb

# Start API server
CMD ["uvicorn", "astro_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

For production, use environment-specific configurations:

```bash
# .env.production
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DB=astro_prod
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_ORIGINS=https://app.example.com
```

## Contributing

1. Follow the 4-layer architecture
2. Write tests for new features (aim for 80%+ coverage)
3. Run import linter before committing
4. Use type hints for all function signatures
5. Document public APIs with docstrings
6. Update relevant README files

## License

MIT
