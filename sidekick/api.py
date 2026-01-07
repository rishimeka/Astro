"""Sidekick FastAPI endpoints for querying traces.

Provides REST API for viewing and managing execution traces.
"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Try to import FastAPI
try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FastAPI = None
    HTTPException = None
    Query = None
    JSONResponse = None
    FASTAPI_AVAILABLE = False

from sidekick.persistence import SidekickPersistence
from sidekick.config import get_config


def create_sidekick_router():
    """Create FastAPI router for Sidekick endpoints.

    Returns APIRouter if FastAPI is available, None otherwise.
    """
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not installed. Sidekick API not available.")
        return None

    from fastapi import APIRouter

    router = APIRouter(prefix="/sidekick", tags=["sidekick"])
    persistence = SidekickPersistence()

    @router.get("/traces/{trace_id}")
    async def get_trace(trace_id: str) -> Dict[str, Any]:
        """Get a single trace by ID."""
        trace = await persistence.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace.model_dump()

    @router.get("/traces")
    async def list_traces(
        limit: int = Query(default=10, le=100),
        status: Optional[str] = Query(default=None),
    ) -> List[Dict[str, Any]]:
        """List recent traces."""
        traces = await persistence.get_recent_traces(limit=limit, status=status)
        return [t.model_dump() for t in traces]

    @router.get("/traces/{trace_id}/for-nebula")
    async def get_trace_for_nebula(trace_id: str) -> Dict[str, Any]:
        """Get a trace formatted for Nebula input.

        Includes execution trace and all Star content used.
        """
        result = await persistence.get_traces_for_nebula(trace_id)
        if not result:
            raise HTTPException(status_code=404, detail="Trace not found")
        return result

    @router.get("/traces/{trace_id}/summary")
    async def get_trace_summary(trace_id: str) -> Dict[str, Any]:
        """Get a human-readable summary of a trace."""
        trace = await persistence.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace.to_summary()

    @router.get("/search")
    async def search_traces(
        query: Optional[str] = Query(default=None),
        status: Optional[str] = Query(default=None),
        start_date: Optional[str] = Query(default=None),
        end_date: Optional[str] = Query(default=None),
        limit: int = Query(default=10, le=100),
        offset: int = Query(default=0),
    ) -> List[Dict[str, Any]]:
        """Search traces with various filters."""
        traces = await persistence.search_traces(
            query_text=query,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return [t.model_dump() for t in traces]

    @router.delete("/traces/{trace_id}")
    async def delete_trace(trace_id: str) -> Dict[str, str]:
        """Delete a trace by ID."""
        success = await persistence.delete_trace(trace_id)
        if not success:
            raise HTTPException(
                status_code=404, detail="Trace not found or could not be deleted"
            )
        return {"status": "deleted", "trace_id": trace_id}

    @router.get("/stats")
    async def get_stats() -> Dict[str, Any]:
        """Get overall trace statistics."""
        total = await persistence.count_traces()
        completed = await persistence.count_traces(status="completed")
        failed = await persistence.count_traces(status="failed")
        running = await persistence.count_traces(status="running")

        return {
            "total_traces": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": completed / total if total > 0 else 0,
        }

    @router.post("/cleanup")
    async def cleanup_old_traces() -> Dict[str, Any]:
        """Delete traces older than retention period."""
        config = get_config()
        deleted = await persistence.cleanup_old_traces()
        return {
            "deleted_count": deleted,
            "retention_days": config.trace_retention_days,
        }

    return router


def create_sidekick_app() -> Optional["FastAPI"]:
    """Create a standalone FastAPI app for Sidekick.

    Returns FastAPI app if available, None otherwise.
    """
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not installed. Run: pip install fastapi uvicorn")
        return None

    app = FastAPI(
        title="Sidekick API",
        description="Execution Observability and Tracing System",
        version="0.1.0",
    )

    router = create_sidekick_router()
    if router:
        app.include_router(router)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "sidekick"}

    return app


# Standalone app for running with uvicorn
app = create_sidekick_app()
