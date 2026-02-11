"""Core storage interface for Layer 1 primitives.

This module defines the storage protocol for Layer 1 (core) primitives.
Layer 1 only needs directive storage. Stars, Constellations, and Runs
are Layer 2 concepts and belong in orchestration_storage.py.
"""

from typing import TYPE_CHECKING, Any, Optional, Protocol

if TYPE_CHECKING:
    from astro.core.models import Directive


class CoreStorageBackend(Protocol):
    """Storage backend for Layer 1 primitives (Directives only).

    This protocol defines the contract for storing and retrieving directives.
    Layer 1 (core) only needs directive storage - Stars, Constellations, and
    Runs are Layer 2 concepts handled by OrchestrationStorageBackend.

    Implementations can be:
    - MongoDB (astro-mongodb)
    - PostgreSQL (astro-postgres)
    - SQLite (astro-sqlite)
    - In-memory (for testing)

    Example usage:
        ```python
        from astro.interfaces.storage import CoreStorageBackend
        from astro.core.registry import Registry

        # Wire up with implementation
        storage = MongoDBCoreStorage(uri="mongodb://localhost", database="astro")
        registry = Registry(storage=storage)

        # Use registry
        await registry.startup()
        directive = Directive(id="test", name="Test", description="...", content="...")
        saved, warnings = await registry.create_directive(directive)
        ```
    """

    async def startup(self) -> None:
        """Initialize storage backend.

        Called once during application startup. Use this to:
        - Establish database connections
        - Create collections/tables if needed
        - Set up indexes
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

    async def save_directive(self, directive: "Directive") -> "Directive":
        """Save or update a directive.

        If directive.id exists, updates it. Otherwise creates a new one.

        Args:
            directive: Directive to save

        Returns:
            Saved directive (may have additional fields set by backend)

        Raises:
            ValidationError: If directive is invalid
            StorageError: If save fails

        Example:
            ```python
            directive = Directive(
                id="financial_analysis",
                name="Financial Analysis",
                description="Analyze financial data",
                content="You are a financial analyst...",
                probe_ids=["search_web", "analyze_data"],
            )
            saved = await storage.save_directive(directive)
            ```
        """
        ...

    async def get_directive(self, directive_id: str) -> Optional["Directive"]:
        """Retrieve directive by ID.

        Args:
            directive_id: Unique identifier for directive

        Returns:
            Directive if found, None otherwise

        Example:
            ```python
            directive = await storage.get_directive("financial_analysis")
            if directive:
                print(f"Found: {directive.name}")
            ```
        """
        ...

    async def list_directives(
        self,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list["Directive"]:
        """List all directives, optionally filtered by metadata.

        Args:
            filter_metadata: Optional metadata filters (e.g., {"domain": "finance"})
                           Backend should support simple equality matching

        Returns:
            List of directives matching filter

        Example:
            ```python
            # Get all directives
            all_directives = await storage.list_directives()

            # Get only finance directives
            finance = await storage.list_directives(
                filter_metadata={"domain": "finance"}
            )
            ```
        """
        ...

    async def delete_directive(self, directive_id: str) -> bool:
        """Delete a directive.

        Args:
            directive_id: ID of directive to delete

        Returns:
            True if directive was deleted, False if not found

        Example:
            ```python
            deleted = await storage.delete_directive("old_directive")
            if deleted:
                print("Deleted successfully")
            ```
        """
        ...
