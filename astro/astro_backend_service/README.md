# Astro Backend Service

The backend service for Astro - an AI-powered workflow automation platform. Built with FastAPI and designed around a graph-based execution model using "Stars" and "Constellations".

## Architecture Overview

Astro uses a unique workflow paradigm where:
- **Directives** define agent behavior through prompts
- **Stars** are execution units that use Directives
- **Constellations** are DAGs (directed acyclic graphs) of Stars
- **Probes** are tools available to Stars during execution

```
User Query → Launchpad → Constellation → Stars → LLM + Probes → Result
```

## Folder Structure

```
astro_backend_service/
├── api/                    # FastAPI REST endpoints
│   ├── main.py            # App entry point, middleware
│   ├── routes/            # Route handlers
│   │   ├── chat.py        # Chat/conversation endpoints
│   │   ├── constellations.py
│   │   ├── directives.py
│   │   ├── probes.py
│   │   ├── runs.py        # Execution history, HITL
│   │   └── stars.py
│   ├── schemas.py         # Request/response models
│   └── dependencies.py    # Dependency injection
│
├── models/                 # Pydantic models (core primitives)
│   ├── directive.py       # Directive model
│   ├── constellation.py   # Constellation (workflow graph)
│   ├── nodes.py           # StartNode, EndNode, StarNode
│   ├── edge.py            # Graph edges with conditions
│   ├── template_variable.py
│   ├── star_types.py      # StarType enum
│   ├── outputs.py         # Execution output models
│   └── stars/             # Star type implementations
│       ├── base.py        # BaseStar, AtomicStar, OrchestratorStar
│       ├── worker.py      # WorkerStar - generic LLM executor
│       ├── planning.py    # PlanningStar - generates execution plans
│       ├── execution.py   # ExecutionStar - spawns workers from plans
│       ├── eval.py        # EvalStar - evaluates and routes
│       ├── synthesis.py   # SynthesisStar - aggregates outputs
│       └── docex.py       # DocExStar - document extraction
│
├── foundry/               # Registry and persistence layer
│   ├── foundry.py         # Main Foundry class
│   ├── persistence.py     # MongoDB operations
│   ├── validation.py      # Star/Directive validation
│   ├── extractor.py       # @ syntax extraction
│   └── indexes.py         # In-memory indexes
│
├── executor/              # Constellation execution engine
│   ├── runner.py          # ConstellationRunner
│   ├── context.py         # ExecutionContext, WorkerContext
│   ├── run.py             # Run model (execution state)
│   ├── stream.py          # SSE streaming handlers
│   ├── events.py          # Stream event types
│   └── exceptions.py      # Execution errors
│
├── probes/                # Tool system
│   ├── decorator.py       # @probe decorator
│   ├── registry.py        # ProbeRegistry singleton
│   ├── probe.py           # Probe model
│   ├── exceptions.py      # Probe errors
│   └── google_news.py     # Example probe implementation
│
├── launchpad/             # Chat interface & routing
│   ├── triggering_agent.py # Conversational router
│   ├── matching.py        # Constellation matching
│   ├── conversation.py    # Conversation state
│   ├── synthesis.py       # Output synthesis
│   └── tools.py           # Launchpad-specific tools
│
└── llm_utils.py           # LLM initialization helpers
```

## Core Primitives

### Directive

The fundamental unit of agent behavior. Defines what an agent does through progressive disclosure.

```python
from astro_backend_service.models import Directive

directive = Directive(
    id="financial_analysis",
    name="Financial Analysis",
    description="Analyzes company financials",  # Shown to planners
    content="""## Role
    You are a financial analyst...

    ## Tools
    - @probe:extract_metrics

    ## Variables
    - @variable:company_name
    """,  # Full prompt for workers
    probe_ids=["extract_metrics"],
    template_variables=[...]
)
```

**Location:** `models/directive.py`

### Star

Execution units that use Directives. Two categories:

**Atomic Stars** - Make direct LLM calls:
- `WorkerStar` - Generic flexible executor
- `PlanningStar` - Generates structured plans
- `EvalStar` - Evaluates results, decides routing
- `SynthesisStar` - Aggregates outputs

**Orchestrator Stars** - Spawn and manage workers:
- `ExecutionStar` - Executes plans from PlanningStar
- `DocExStar` - Parallel document extraction

```python
from astro_backend_service.models import WorkerStar, StarType

star = WorkerStar(
    id="analyst",
    name="Financial Analyst",
    directive_id="financial_analysis",
    probe_ids=["search_news"],  # Additional probes
    max_iterations=5
)
```

**Location:** `models/stars/`

### Constellation

A workflow graph connecting Stars. Defines execution flow with support for:
- Parallel execution (multiple edges from one node)
- Conditional routing (EvalStar with `condition` edges)
- Loop limits (prevent infinite cycles)
- Retry logic with exponential backoff

```python
from astro_backend_service.models import (
    Constellation, StartNode, EndNode, StarNode, Edge, Position
)

constellation = Constellation(
    id="market_research",
    name="Market Research",
    description="Analyzes company from bull and bear perspectives",
    start=StartNode(id="start", position=Position(x=0, y=0)),
    end=EndNode(id="end", position=Position(x=800, y=0)),
    nodes=[
        StarNode(id="planner", star_id="planning_star", ...),
        StarNode(id="bull", star_id="bull_analyst", ...),
        StarNode(id="bear", star_id="bear_analyst", ...),
    ],
    edges=[
        Edge(id="e1", source="start", target="planner"),
        Edge(id="e2", source="planner", target="bull"),
        Edge(id="e3", source="planner", target="bear"),  # Parallel
        Edge(id="e4", source="bull", target="end"),
        Edge(id="e5", source="bear", target="end"),
    ],
    max_loop_iterations=3
)
```

**Location:** `models/constellation.py`, `models/nodes.py`, `models/edge.py`

### Probe

Tools available to Stars during execution. Registered via decorator.

```python
from astro_backend_service.probes import probe

@probe
def search_news(query: str, days: int = 7) -> list[dict]:
    """Search recent news articles.

    Args:
        query: Search query
        days: Number of days to look back

    Returns:
        List of article objects with title, url, date
    """
    # Implementation
    return results
```

**Location:** `probes/`

## Key Components

### Foundry

Central registry and persistence layer. Handles:
- CRUD for Directives, Stars, Constellations
- Validation (referential integrity, @ syntax)
- MongoDB persistence
- In-memory indexing

```python
from astro_backend_service.foundry import Foundry

foundry = Foundry(mongo_uri, database_name)
await foundry.initialize()

directive, warnings = await foundry.create_directive(directive)
star = foundry.get_star("star_id")
```

**Location:** `foundry/`

### Executor

Runs Constellations. Features:
- Topological DAG traversal
- Parallel node execution
- EvalStar loop handling
- Human-in-the-loop (HITL) pause/resume
- SSE streaming for real-time updates

```python
from astro_backend_service.executor import ConstellationRunner

runner = ConstellationRunner(foundry)
run = await runner.run(
    constellation_id="market_research",
    variables={"company_name": "Tesla"},
    original_query="Analyze Tesla"
)
```

**Location:** `executor/`

### Launchpad

Conversational interface that:
- Matches user queries to Constellations
- Collects required variables through conversation
- Triggers execution
- Synthesizes results

**Location:** `launchpad/`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /chat` | Send message, get response (streaming) |
| `GET /constellations` | List all constellations |
| `GET /constellations/{id}` | Get constellation details |
| `POST /constellations/{id}/run` | Execute a constellation |
| `GET /runs/{id}` | Get run status/results |
| `POST /runs/{id}/confirm` | Resume HITL-paused run |
| `GET /stars` | List all stars |
| `GET /directives` | List all directives |
| `GET /probes` | List available probes |

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Set environment variables
export MONGO_URI=mongodb://localhost:27017
export MONGO_DB=astro
export OPENAI_API_KEY=your_key

# Start the server
uvicorn astro_backend_service.api.main:app --reload
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=astro_backend_service

# Run specific test file
pytest tests/models/test_constellation.py
```

## Type Checking

```bash
mypy .
```

## Linting

```bash
ruff check . --fix
```
