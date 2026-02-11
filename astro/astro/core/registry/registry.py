"""Central Registry for Layer 1 primitives (Directives and Probes).

The Registry provides:
- In-memory indexes for fast lookups
- Persistence via CoreStorageBackend interface
- Validation of cross-references between primitives
- @ syntax extraction from Directive content

Layer 1 (core) only manages Directives and Probes.
Stars, Constellations, and Runs are Layer 2 concepts and are NOT managed here.
"""

from typing import Any, Dict, List, Optional, Tuple

from astro.interfaces.storage import CoreStorageBackend
from astro.core.models.directive import Directive
from astro.core.models.template_variable import TemplateVariable
from astro.core.probes.registry import ProbeRegistry
from astro.core.registry.indexes import RegistryIndexes, Probe
from astro.core.registry.extractor import (
    extract_references,
    create_template_variables,
)
from astro.core.registry.validation import (
    ValidationError,
    ValidationWarning,
    validate_directive,
)


class Registry:
    """
    Central registry for Layer 1 primitives (Directives and Probes).

    Provides:
    - In-memory indexes for fast lookups
    - Persistence via CoreStorageBackend interface
    - Validation of cross-references between directives
    - @ syntax extraction from Directive content
    - Probe registration and lookup

    Usage:
        ```python
        from astro.core.registry import Registry
        from astro_mongodb import MongoDBCoreStorage

        # Wire up with storage backend
        storage = MongoDBCoreStorage(uri="mongodb://localhost", database="astro")
        registry = Registry(storage=storage)

        # Initialize
        await registry.startup()

        # Create directive
        directive = Directive(
            id="test",
            name="Test",
            description="A test directive",
            content="You are a helpful assistant. Use @probe:search_web when needed."
        )
        created, warnings = await registry.create_directive(directive)

        # Get directive
        retrieved = registry.get_directive("test")

        # Cleanup
        await registry.shutdown()
        ```
    """

    def __init__(self, storage: CoreStorageBackend):
        """
        Initialize Registry.

        Args:
            storage: Storage backend implementing CoreStorageBackend protocol
        """
        self.storage = storage
        self._indexes = RegistryIndexes()
        self._initialized = False

    async def startup(self) -> None:
        """
        Initialize Registry by loading data from storage backend.

        Must be called before using the Registry. This method:
        1. Initializes the storage backend
        2. Loads all directives from storage into memory
        3. Syncs probes from ProbeRegistry

        Raises:
            ConnectionError: If storage backend fails to initialize
        """
        # Initialize storage backend
        await self.storage.startup()

        # Load directives from storage
        await self._load_directives_from_storage()

        # Sync probes from code-defined ProbeRegistry
        self._sync_probes_from_registry()

        self._initialized = True

    async def _load_directives_from_storage(self) -> None:
        """Load all directives from storage backend into memory."""
        directives = await self.storage.list_directives()
        for directive in directives:
            self._indexes.directives[directive.id] = directive

    def _sync_probes_from_registry(self) -> None:
        """Sync probes from ProbeRegistry into Registry indexes."""
        for probe in ProbeRegistry.all():
            self._indexes.probes[probe.name] = Probe(
                name=probe.name,
                description=probe.description,
                parameters=probe.input_schema or {},
                handler=probe._callable,
            )

    async def shutdown(self) -> None:
        """Close storage backend connection."""
        await self.storage.shutdown()

    # =========================================================================
    # Probe Registry
    # =========================================================================

    def probe_exists(self, name: str) -> bool:
        """Check if a probe is registered.

        Args:
            name: Probe name

        Returns:
            True if probe exists, False otherwise
        """
        return self._indexes.probe_exists(name)

    def get_probe(self, name: str) -> Optional[Probe]:
        """Get probe by name.

        Args:
            name: Probe name

        Returns:
            Probe if found, None otherwise
        """
        return self._indexes.get_probe(name)

    def register_probes(self, probes: List[Probe]) -> None:
        """
        Register multiple probes.

        Args:
            probes: List of Probe objects to register
        """
        for probe in probes:
            self._indexes.probes[probe.name] = probe

    def register_probe(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        handler: Optional[Any] = None,
    ) -> Probe:
        """
        Register a single probe.

        Args:
            name: Probe name
            description: Probe description
            parameters: Parameter schema
            handler: Callable handler

        Returns:
            The registered Probe
        """
        probe = Probe(
            name=name,
            description=description,
            parameters=parameters or {},
            handler=handler,
        )
        self._indexes.probes[name] = probe
        return probe

    def list_probes(self) -> List[Probe]:
        """List all registered probes.

        Returns:
            List of all Probe objects
        """
        return list(self._indexes.probes.values())

    # =========================================================================
    # Directive CRUD
    # =========================================================================

    async def create_directive(
        self, directive: Directive
    ) -> Tuple[Directive, List[ValidationWarning]]:
        """
        Create a new directive.

        This method:
        - Extracts @ references from content
        - Validates references exist (warnings for missing)
        - Checks for cycles in reference_ids
        - Persists to storage backend
        - Updates in-memory index

        Args:
            directive: The directive to create

        Returns:
            Tuple of (created directive, list of warnings)

        Raises:
            ValidationError: If validation fails
        """
        # Check for duplicate ID
        if directive.id in self._indexes.directives:
            raise ValidationError(f"Directive '{directive.id}' already exists")

        # Extract @ references from content
        probe_ids, reference_ids, variable_names = extract_references(directive.content)

        # Create template variables for extracted names
        template_vars = create_template_variables(
            variable_names, directive.template_variables
        )

        # Update directive with extracted references
        directive = directive.model_copy(
            update={
                "probe_ids": probe_ids,
                "reference_ids": reference_ids,
                "template_variables": template_vars,
            }
        )

        # Validate
        warnings = validate_directive(directive, self._indexes)

        # Persist to storage backend
        await self.storage.save_directive(directive)

        # Update in-memory index
        self._indexes.directives[directive.id] = directive

        return directive, warnings

    def get_directive(self, id: str) -> Optional[Directive]:
        """Get directive by ID from in-memory index.

        Args:
            id: Directive ID

        Returns:
            Directive if found, None otherwise
        """
        return self._indexes.get_directive(id)

    def list_directives(
        self,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Directive]:
        """List all directives, optionally filtered by metadata.

        Note: This returns directives from the in-memory index.
        For metadata filtering, use storage.list_directives() directly.

        Args:
            filter_metadata: Optional metadata filter (currently not implemented
                           in memory, returns all directives)

        Returns:
            List of directives
        """
        # TODO: Implement in-memory metadata filtering if needed
        # For now, return all directives from index
        return list(self._indexes.directives.values())

    async def update_directive(
        self, id: str, updates: Dict[str, Any]
    ) -> Tuple[Directive, List[ValidationWarning]]:
        """
        Update directive.

        This method:
        - Re-extracts @ references if content changed
        - Re-validates references
        - Persists to storage backend
        - Updates in-memory index

        Args:
            id: Directive ID to update
            updates: Dictionary of fields to update

        Returns:
            Tuple of (updated directive, list of warnings)

        Raises:
            ValidationError: If validation fails or directive not found
        """
        existing = self._indexes.get_directive(id)
        if not existing:
            raise ValidationError(f"Directive '{id}' not found")

        # Apply updates
        updated_data = existing.model_dump()
        updated_data.update(updates)

        # If content changed, re-extract references
        if "content" in updates:
            probe_ids, reference_ids, variable_names = extract_references(
                updates["content"]
            )
            template_vars = create_template_variables(
                variable_names,
                [
                    TemplateVariable.model_validate(v)
                    for v in updated_data.get("template_variables", [])
                ],
            )
            updated_data["probe_ids"] = probe_ids
            updated_data["reference_ids"] = reference_ids
            updated_data["template_variables"] = [v.model_dump() for v in template_vars]

        updated = Directive.model_validate(updated_data)

        # Validate
        warnings = validate_directive(updated, self._indexes, existing_id=id)

        # Persist to storage backend
        await self.storage.save_directive(updated)

        # Update in-memory index
        self._indexes.directives[id] = updated

        return updated, warnings

    async def delete_directive(self, id: str) -> bool:
        """
        Delete directive.

        Args:
            id: Directive ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValidationError: If directive is referenced by other directives
        """
        # Check if directive exists
        if id not in self._indexes.directives:
            return False

        # Check if any other directives reference this one
        referencing_directives = [
            d.id
            for d in self._indexes.directives.values()
            if id in d.reference_ids
        ]

        if referencing_directives:
            raise ValidationError(
                f"Cannot delete Directive '{id}': referenced by directives "
                f"{referencing_directives}"
            )

        # Delete from storage backend
        deleted = await self.storage.delete_directive(id)

        # Remove from in-memory index if deleted
        if deleted:
            del self._indexes.directives[id]

        return deleted
