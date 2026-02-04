# Astro

A modular AI agent orchestration framework built to answer a practical question: does structured multi-agent orchestration actually produce better results than simpler approaches?

## Why I Built This

I spent the past year building a production multi-agent research system at Goldman Sachs. That work taught me a lot about what breaks when you scale agent workflows — tool contamination across workers, prompt maintenance nightmares, no visibility into why agents made specific decisions. Astro is my attempt to generalize those lessons into a framework with three core ideas:

- **Stars**: Modular prompt components with metadata, versioning, and directed relationships — replacing monolithic prompt blocks with composable, maintainable units
- **Probes**: Capability-scoped tool access that enforces principle-of-least-privilege per workflow step, preventing cross-contamination between agents
- **Constellations**: Directed workflow graphs that define execution paths, branching conditions, and parallel operations across Stars
- **Sidekick**: An execution observability system that captures structured traces — LLM calls, tool invocations, latency, quality signals — for debugging and performance analysis

## What I Found

After building the framework, I benchmarked it honestly against simpler approaches: orchestrated multi-agent (Astro) vs. naive multi-agent vs. zero-shot, using LLM-as-judge evaluation with multiple runs for statistical validity.

The results were more nuanced than I expected:

- **Tool-level scoping works.** Probes effectively prevent cross-contamination between workflow steps.
- **Analysis-level contamination persists.** Even with scoped tools, contamination leaks through at the synthesis layer when agents share context.
- **Orchestration improves independence, not necessarily quality.** Multi-agent orchestration produces more analytically independent outputs, but doesn't consistently justify its cost premium on output quality alone.
- **The value is in the platform, not the architecture.** The real benefit is maintainability, observability, and team workflow — not raw output superiority.

These aren't the findings I wanted, but they're the findings I trust. I've written about these tradeoffs in more detail on [LinkedIn](https://linkedin.com/in/rishimeka).

## Architecture

```
astro/
├── astro_backend_service/  # Python backend (FastAPI)
│   ├── api/                # REST API routes
│   ├── foundry/            # MongoDB persistence layer
│   ├── models/             # Pydantic models
│   ├── probes/             # Tool definitions
│   ├── executor/           # Constellation runner
│   └── launchpad/          # Chat interface & triggering agent
├── astro-ui/               # Next.js frontend
├── scripts/                # Utility scripts
└── requirements.txt        # Python dependencies
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB (running locally on port 27017)

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install astro_backend_service package in development mode
pip install -e .

# Seed the database with sample data
python scripts/seed_db.py

# Start the API server
uvicorn astro_backend_service.api.main:app --reload
```

The API will be available at http://localhost:8000

### Frontend Setup

```bash
cd astro-ui
npm install
npm run dev
```

The UI will be available at http://localhost:3000

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `astro` | Database name |
| `ANTHROPIC_API_KEY` | - | Anthropic API key for Claude |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_USE_MOCK` | `false` | Use mock data instead of API |

## Development

### Running Tests

```bash
# Backend tests
pytest

# Frontend tests
cd astro-ui && npm test
```

### Code Quality

```bash
# Backend
black .          # Format code
ruff check .     # Lint
mypy .           # Type check

# Frontend
cd astro-ui
npm run lint     # ESLint
npm run build    # Type check via build
```

## API Documentation

When the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
