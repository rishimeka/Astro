# Astro API

FastAPI application for Astro V2 - Modular AI Infrastructure & Multi-Agent Orchestration.

## Overview

This package provides a REST API for Astro V2, exposing:

- **Chat interface** via `/chat` - Conversational interface with zero-shot (fast) and constellation (thorough) modes
- **Directive management** via `/directives` - CRUD operations for prompt modules
- **Probe management** via `/probes` - Browse and manage tool wrappers
- **Star management** via `/stars` - CRUD operations for execution units
- **Constellation management** via `/constellations` - CRUD operations for multi-agent workflows
- **Run history** via `/runs` - View constellation execution history
- **File uploads** via `/files` - Upload and process files

## Installation

```bash
pip install astro-api
```

Or with development dependencies:

```bash
pip install astro-api[dev]
```

## Quick Start

### Environment Variables

```bash
# MongoDB connection
export MONGO_URI=mongodb://localhost:27017
export MONGO_DB=astro

# LLM provider (OpenAI or Anthropic)
export OPENAI_API_KEY=your_key_here
# OR
export ANTHROPIC_API_KEY=your_key_here

# CORS (optional)
export ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Run the API

```bash
cd astro-api
uvicorn astro_api.main:app --reload
```

The API will be available at `http://localhost:8000`.

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Architecture

The API uses dependency injection to wire up V2 components:

```
LaunchpadController
├── ZeroShotPipeline (fast)
│   ├── Interpreter (directive selection)
│   ├── RunningAgent (ReAct execution)
│   └── SecondBrain (memory)
└── ConstellationPipeline (thorough)
    ├── Matcher (constellation matching)
    ├── ConstellationRunner (orchestration)
    └── SecondBrain (memory)
```

## Usage Examples

### Zero-Shot Chat (Fast)

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in NYC?"}'
```

### Constellation Chat (Research Mode)

```bash
curl -X POST "http://localhost:8000/chat?research_mode=true" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze Tesla financial performance"}'
```

### List Directives

```bash
curl "http://localhost:8000/directives"
```

### Get Constellation Details

```bash
curl "http://localhost:8000/constellations/{constellation_id}"
```

## Development

### Run Tests

```bash
pytest
```

### Type Checking

```bash
mypy astro_api/
```

### Linting

```bash
ruff check astro_api/
```

### Formatting

```bash
black astro_api/
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY astro_api/ astro_api/

CMD ["uvicorn", "astro_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn + Uvicorn Workers

```bash
pip install gunicorn
gunicorn astro_api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## License

MIT
