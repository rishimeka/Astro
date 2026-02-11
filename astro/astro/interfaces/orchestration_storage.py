"""Orchestration storage interface for Layer 2 primitives.

This module defines the storage protocol for Layer 2 (orchestration) primitives.
Layer 2 needs storage for Stars, Constellations, and Runs. This keeps Layer 0
interfaces clean - no awareness of Layer 2 in the core storage interface.
"""

from typing import Protocol, Optional, List


class OrchestrationStorageBackend(Protocol):
    """Storage backend for Layer 2 primitives (Stars, Constellations, Runs).

    This protocol defines the contract for storing and retrieving orchestration
    primitives. These are separate from CoreStorageBackend to maintain layer
    boundaries - Layer 0 interfaces should not be aware of Layer 2 concepts.

    Implementations typically use the same underlying database as CoreStorageBackend
    but with different collections/tables.

    Example usage:
        ```python
        from astro.interfaces.orchestration_storage import OrchestrationStorageBackend
        from astro.orchestration.runner import ConstellationRunner

        # Wire up with implementation
        orch_storage = MongoDBOrchestrationStorage(
            uri="mongodb://localhost",
            database="astro"
        )
        runner = ConstellationRunner(
            core_storage=core_storage,  # For directives
            orchestration_storage=orch_storage,  # For stars/constellations/runs
        )
        ```
    """

    async def startup(self) -> None:
        """Initialize storage backend.

        Called once during application startup. Use this to:
        - Establish database connections
        - Create collections/tables if needed
        - Set up indexes for runs queries
        - Validate configuration

        Raises:
            ConnectionError: If unable to connect to storage backend
        """
        ...

    async def shutdown(self) -> None:
        """Cleanup storage backend.

        Called once during application shutdown. Use this to:
        - Close database connections
        - Release resources
        - Flush pending writes

        Should be idempotent - calling multiple times should be safe.
        """
        ...

    # Stars (Layer 2)

    async def save_star(self, star: "BaseStar") -> "BaseStar":
        """Save or update a star.

        If star.id exists, updates it. Otherwise creates a new one.

        Args:
            star: Star to save (WorkerStar, PlanningStar, etc.)

        Returns:
            Saved star

        Raises:
            ValidationError: If star is invalid
            StorageError: If save fails

        Example:
            ```python
            star = WorkerStar(
                id="analyst_1",
                name="Financial Analyst",
                type=StarType.WORKER,
                directive_id="financial_analysis",
                probe_ids=["search_web"],
                config={"max_tokens": 2000},
            )
            saved = await storage.save_star(star)
            ```
        """
        ...

    async def get_star(self, star_id: str) -> Optional["BaseStar"]:
        """Retrieve star by ID.

        Args:
            star_id: Unique identifier for star

        Returns:
            Star if found, None otherwise

        Example:
            ```python
            star = await storage.get_star("analyst_1")
            if star:
                print(f"Found: {star.name}")
            ```
        """
        ...

    async def list_stars(
        self,
        filter_type: Optional[str] = None,
    ) -> List["BaseStar"]:
        """List all stars, optionally filtered by type.

        Args:
            filter_type: Optional star type filter (e.g., "worker", "planning")

        Returns:
            List of stars matching filter

        Example:
            ```python
            # Get all stars
            all_stars = await storage.list_stars()

            # Get only worker stars
            workers = await storage.list_stars(filter_type="worker")
            ```
        """
        ...

    async def delete_star(self, star_id: str) -> bool:
        """Delete a star.

        Args:
            star_id: ID of star to delete

        Returns:
            True if star was deleted, False if not found

        Note:
            Consider checking if star is used in any constellations before deleting.
        """
        ...

    # Constellations (Layer 2)

    async def save_constellation(
        self,
        constellation: "Constellation",
    ) -> "Constellation":
        """Save or update a constellation.

        If constellation.id exists, updates it. Otherwise creates a new one.

        Args:
            constellation: Constellation to save

        Returns:
            Saved constellation

        Raises:
            ValidationError: If constellation is invalid
            StorageError: If save fails

        Example:
            ```python
            constellation = Constellation(
                id="market_research",
                name="Market Research",
                description="Research market conditions",
                start=StartNode(id="start"),
                end=EndNode(id="end"),
                nodes=[...],
                edges=[...],
            )
            saved = await storage.save_constellation(constellation)
            ```
        """
        ...

    async def get_constellation(
        self,
        constellation_id: str,
    ) -> Optional["Constellation"]:
        """Retrieve constellation by ID.

        Args:
            constellation_id: Unique identifier for constellation

        Returns:
            Constellation if found, None otherwise

        Example:
            ```python
            constellation = await storage.get_constellation("market_research")
            if constellation:
                print(f"Found: {constellation.name}")
            ```
        """
        ...

    async def list_constellations(self) -> List["Constellation"]:
        """List all constellations.

        Returns:
            List of all constellations

        Example:
            ```python
            constellations = await storage.list_constellations()
            for c in constellations:
                print(f"{c.id}: {c.description}")
            ```
        """
        ...

    async def delete_constellation(self, constellation_id: str) -> bool:
        """Delete a constellation.

        Args:
            constellation_id: ID of constellation to delete

        Returns:
            True if constellation was deleted, False if not found

        Note:
            Consider archiving runs before deleting the constellation.
        """
        ...

    # Runs (execution history - Layer 2)

    async def save_run(self, run: "Run") -> "Run":
        """Save or update a run.

        Runs are execution records for constellation executions. They capture:
        - Status (pending, running, completed, failed)
        - Outputs from each node
        - Timestamps and duration
        - Error information if failed

        Args:
            run: Run to save

        Returns:
            Saved run

        Example:
            ```python
            run = Run(
                id="run_123",
                constellation_id="market_research",
                status="running",
                variables={"company": "Tesla"},
                created_at=datetime.utcnow(),
            )
            saved = await storage.save_run(run)
            ```
        """
        ...

    async def get_run(self, run_id: str) -> Optional["Run"]:
        """Retrieve run by ID.

        Args:
            run_id: Unique identifier for run

        Returns:
            Run if found, None otherwise

        Example:
            ```python
            run = await storage.get_run("run_123")
            if run:
                print(f"Status: {run.status}")
            ```
        """
        ...

    async def list_runs(
        self,
        constellation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List["Run"]:
        """List runs, optionally filtered by constellation.

        Args:
            constellation_id: Optional filter by constellation
            limit: Maximum number of runs to return (default 100)

        Returns:
            List of runs, most recent first

        Example:
            ```python
            # Get recent runs for a constellation
            runs = await storage.list_runs(
                constellation_id="market_research",
                limit=10
            )
            for run in runs:
                print(f"{run.id}: {run.status}")
            ```
        """
        ...
