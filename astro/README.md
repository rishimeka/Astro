# Astro

AI-powered workflow automation platform by Astrix Labs.

## Project Structure

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
