# Astrix Labs

Full-stack monorepo for AI-powered workflow automation. Combines a Next.js frontend with a modular Python backend designed for multi-agent orchestration.

## Project Structure

```
astrix-labs/
├── astro/                  # Main Python package (core infrastructure)
│   ├── astro/              # Source code (4-layer architecture)
│   ├── astro-api/          # FastAPI application
│   ├── astro-mongodb/      # MongoDB storage adapters
│   └── tests/              # Test suite
├── astro-ui/               # Next.js frontend
├── scripts/                # Utility scripts
└── requirements.txt        # Python dependencies
```

## Architecture Overview

### Frontend Stack
- **Framework**: Next.js 16 with App Router
- **React 19** with React Compiler enabled (automatic memoization)
- **Path alias**: `@/*` maps to `./src/*`
- **Design tokens**: CSS custom properties for colors and spacing

### Backend Stack (Python)
- **API**: FastAPI with Uvicorn (async/await, dependency injection)
- **AI/LLM**: Anthropic SDK, LangChain, LangGraph for agentic workflows
- **Database**: MongoDB with Motor (async driver)
- **Validation**: Pydantic v2

### 4-Layer Architecture

The backend is organized into four clean layers with strict dependency rules:

```
Layer 3: Launchpad (Chat Interface)
    ↓ imports from
Layer 2: Orchestration (Multi-Agent Workflows)
    ↓ imports from
Layer 1: Core (Foundation Components)
    ↓ imports from
Layer 0: Interfaces (Pure Protocols)
```

**Layer 0: Interfaces** (`astro/interfaces/`)
- Pure protocol definitions with no implementations
- Storage, LLM, embedding, memory backends
- Zero dependencies on other layers

**Layer 1: Core** (`astro/core/`)
- Foundational components: Directives, Probes, Registry, Memory
- Models, decorators, runtime context
- Imports only from Layer 0

**Layer 2: Orchestration** (`astro/orchestration/`)
- Multi-agent workflow execution
- Constellation models (workflow graphs)
- Star implementations (execution units)
- ConstellationRunner (orchestration engine)
- Imports from Layers 0-1

**Layer 3: Launchpad** (`astro/launchpad/`)
- Conversational chat interface
- Two execution modes: Zero-shot (fast) and Constellation (thorough)
- Interpreter, RunningAgent, synthesis
- Imports from Layers 0-2

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 6.0+ (required for vector search)

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
cd astro
pip install -r requirements.txt

# Install astro package in development mode
pip install -e .

# Install API and MongoDB adapters
cd astro-api && pip install -e . && cd ..
cd astro-mongodb && pip install -e . && cd ..

# Set environment variables
export MONGO_URI=mongodb://localhost:27017
export MONGO_DB=astro
export ANTHROPIC_API_KEY=your_key_here

# Start API server
cd astro-api
uvicorn astro_api.main:app --reload
```

The API will be available at http://localhost:8000

### Frontend Setup

```bash
cd astro-ui
npm install
npm run dev
```

The UI will be available at http://localhost:3000

### Quick Start Script

For the backend, there's a convenience script:

```bash
./start_v2_server.sh
```

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `astro` | Database name |
| `ANTHROPIC_API_KEY` | - | Anthropic API key (for Claude models) |
| `OPENAI_API_KEY` | - | OpenAI API key (alternative to Anthropic) |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_USE_MOCK` | `false` | Use mock data instead of API |

## Development

### Running Tests

```bash
# Backend tests
cd astro
pytest

# Frontend tests
cd astro-ui
npm test
```

### Code Quality

```bash
# Backend
cd astro
black .                  # Format code
ruff check .             # Lint
mypy .                   # Type check
isort .                  # Sort imports

# Frontend
cd astro-ui
npm run lint             # ESLint
npm run build            # Type check via build
```

### Import Linting

The backend uses `import-linter` to enforce layer boundaries:

```bash
cd astro
lint-imports
```

This ensures:
- Layer 3 (launchpad) can import from layers 0-2
- Layer 2 (orchestration) can import from layers 0-1
- Layer 1 (core) can import from layer 0 only
- Layer 0 (interfaces) has no internal imports

## API Documentation

When the backend is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Key Concepts

### Directives
Modular prompt units. Each directive contains:
- Natural language instructions (no `@probe:` syntax in content)
- List of probe IDs (tools to bind)
- Optional template variables
- Optional reference to other directives

### Probes
Tool wrappers decorated with `@probe`. Probes define:
- Tool name and description
- Input schema (Pydantic model)
- Synchronous or asynchronous function

### Stars
Execution units in a workflow. Types include:
- **Worker**: Executes a directive with tools
- **Synthesis**: Aggregates outputs from upstream stars
- **Planning**: Plans multi-step tasks
- **Eval**: Evaluates quality of outputs

### Constellations
Multi-agent workflow graphs. Constellations define:
- Start/end nodes
- Star nodes with positions
- Directed edges (dependencies)
- Template variables for user inputs

### Execution Modes

**Zero-Shot Mode** (default, fast):
1. Interpret: Select relevant directives based on user query
2. Retrieve: Fetch directive and probes from database
3. Execute: Run single-agent ReAct loop with tools
4. Persist: Save conversation to memory

**Constellation Mode** (research, thorough):
1. Match: Find constellation that matches user intent
2. Retrieve: Fetch constellation, stars, directives, probes
3. Execute: Run multi-agent workflow with parallel execution
4. Persist: Save run outputs and conversation

## Package-Specific Documentation

Each package has its own detailed README:

- **[astro/README.md](astro/README.md)** - Core package architecture
- **[astro/astro/README.md](astro/astro/README.md)** - Layer documentation
- **[astro-api/README.md](astro/astro-api/README.md)** - API endpoints and usage
- **[astro-mongodb/README.md](astro/astro-mongodb/README.md)** - Storage adapters
- **[astro-ui/CLAUDE.md](astro-ui/CLAUDE.md)** - Frontend development guide

## Production Deployment

### Using Docker Compose

```yaml
version: '3.8'
services:
  mongodb:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  api:
    build: ./astro
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://mongodb:27017
      - MONGO_DB=astro
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - mongodb

  ui:
    build: ./astro-ui
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api

volumes:
  mongo_data:
```

### Using Kubernetes

See `k8s/` directory for deployment manifests (if available).

## Troubleshooting

### MongoDB Connection Issues

**Problem**: `ServerSelectionTimeoutError`

**Solution**:
- Verify MongoDB is running: `mongosh`
- Check connection string in environment variables
- For Atlas, verify IP whitelist and credentials

### Tool Calls Not Working

**Problem**: Workers output `@probe:tool_name` as text instead of calling functions

**Solution**:
- Remove all `@probe:` references from directive `content` field
- Use natural language instead: "Use your available search tools"
- The `probe_ids` array is sufficient for binding tools
- Verify probes are registered in ProbeRegistry

### 413 Request Body Too Large

**Problem**: Synthesis stars exceed API gateway limits

**Solution**:
- Set `config.max_upstream_length: 1200` on synthesis stars
- This truncates each upstream output before aggregation

### Import Errors

**Problem**: `ImportError: cannot import name 'Directive'`

**Solution**:
- Ensure all packages are installed in editable mode: `pip install -e .`
- Activate virtual environment: `source .venv/bin/activate`
- Check Python path includes the packages

## Contributing

1. Follow the 4-layer architecture strictly
2. Use import linter before committing: `lint-imports`
3. Write tests for new features
4. Run code quality tools: `black`, `ruff`, `mypy`
5. Update relevant README files

## License

MIT
