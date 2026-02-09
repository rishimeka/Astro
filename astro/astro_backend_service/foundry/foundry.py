"""Main Foundry class - central registry for all Astro primitives."""

from typing import Any, Dict, List, Optional

from astro_backend_service.models import (
    Constellation,
    Directive,
    TemplateVariable,
)
from astro_backend_service.models.stars.base import BaseStar

from astro_backend_service.foundry.indexes import FoundryIndexes, Probe
from astro_backend_service.foundry.persistence import FoundryPersistence
from astro_backend_service.probes import ProbeRegistry
from astro_backend_service.foundry.extractor import (
    extract_references,
    create_template_variables,
)
from astro_backend_service.foundry.validation import (
    ValidationError,
    ValidationWarning,
    validate_directive,
    validate_star,
    validate_constellation,
)


class Foundry:
    """
    Central registry for all Astro primitives.

    Provides:
    - In-memory indexes for fast lookups
    - MongoDB persistence for durability
    - Validation of cross-references between primitives
    - @ syntax extraction from Directive content
    """

    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017",
        database_name: str = "astro",
    ):
        """
        Initialize Foundry.

        Args:
            mongo_uri: MongoDB connection URI
            database_name: Database name to use
        """
        self._persistence = FoundryPersistence(mongo_uri, database_name)
        self._indexes = FoundryIndexes()
        self._initialized = False

    async def startup(self) -> None:
        """
        Initialize Foundry by loading data from MongoDB.

        Must be called before using the Foundry.
        """
        await self._load_from_db()
        self._sync_probes_from_registry()
        self._initialized = True

    def _sync_probes_from_registry(self) -> None:
        """Sync probes from ProbeRegistry into Foundry indexes."""
        for probe in ProbeRegistry.all():
            self._indexes.probes[probe.name] = Probe(
                name=probe.name,
                description=probe.description,
                parameters=probe.input_schema or {},
                handler=probe._callable,
            )

    async def shutdown(self) -> None:
        """Close MongoDB connection."""
        await self._persistence.close()

    async def _load_from_db(self) -> None:
        """Load all primitives from MongoDB into memory."""
        # Load directives
        directives = await self._persistence.list_directives()
        for directive in directives:
            self._indexes.directives[directive.id] = directive

        # Load stars
        stars = await self._persistence.list_stars()
        for star in stars:
            self._indexes.stars[star.id] = star

        # Load constellations
        constellations = await self._persistence.list_constellations()
        for constellation in constellations:
            self._indexes.constellations[constellation.id] = constellation

    # =========================================================================
    # Probe Registry (for Worker 2 integration)
    # =========================================================================

    def probe_exists(self, name: str) -> bool:
        """Check if a probe is registered."""
        return self._indexes.probe_exists(name)

    def get_probe(self, name: str) -> Optional[Probe]:
        """Get probe by name."""
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
        """List all registered probes."""
        return list(self._indexes.probes.values())

    # =========================================================================
    # Directive CRUD
    # =========================================================================

    async def create_directive(
        self, directive: Directive
    ) -> tuple[Directive, List[ValidationWarning]]:
        """
        Create a new directive.

        - Extracts @ references from content
        - Validates references exist (warnings for missing)
        - Checks for cycles in reference_ids
        - Persists to MongoDB
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

        # Persist to MongoDB
        await self._persistence.create_directive(directive)

        # Update in-memory index
        self._indexes.directives[directive.id] = directive

        return directive, warnings

    def get_directive(self, id: str) -> Optional[Directive]:
        """Get directive by ID from in-memory index."""
        return self._indexes.get_directive(id)

    def list_directives(self) -> List[Directive]:
        """List all directives."""
        return list(self._indexes.directives.values())

    async def update_directive(
        self, id: str, updates: Dict[str, Any]
    ) -> tuple[Directive, List[ValidationWarning]]:
        """
        Update directive.

        - Re-extracts @ references if content changed
        - Re-validates references
        - Persists to MongoDB
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

        # Persist to MongoDB
        await self._persistence.replace_directive(updated)

        # Update in-memory index
        self._indexes.directives[id] = updated

        return updated, warnings

    async def delete_directive(self, id: str) -> bool:
        """
        Delete directive.

        - Checks if any Stars reference this directive
        - Fails if referenced
        - Removes from MongoDB and in-memory index

        Args:
            id: Directive ID to delete

        Returns:
            True if deleted

        Raises:
            ValidationError: If directive is referenced by stars
        """
        # Check for references
        referencing_stars = await self._persistence.directive_referenced_by_stars(id)
        if referencing_stars:
            raise ValidationError(
                f"Cannot delete Directive '{id}': referenced by Stars "
                f"{referencing_stars}"
            )

        # Delete from MongoDB
        deleted = await self._persistence.delete_directive(id)

        # Remove from in-memory index
        if id in self._indexes.directives:
            del self._indexes.directives[id]

        return deleted

    # =========================================================================
    # Star CRUD
    # =========================================================================

    async def create_star(
        self, star: BaseStar
    ) -> tuple[BaseStar, List[ValidationWarning]]:
        """
        Create a new star.

        - Validates directive_id exists
        - Validates probe_ids exist (for AtomicStar)
        - Persists to MongoDB
        - Updates in-memory index

        Args:
            star: The star to create

        Returns:
            Tuple of (created star, list of warnings)

        Raises:
            ValidationError: If validation fails
        """
        # Check for duplicate ID
        if star.id in self._indexes.stars:
            raise ValidationError(f"Star '{star.id}' already exists")

        # Validate
        warnings = validate_star(star, self._indexes)

        # Persist to MongoDB
        await self._persistence.create_star(star)

        # Update in-memory index
        self._indexes.stars[star.id] = star

        return star, warnings

    def get_star(self, id: str) -> Optional[BaseStar]:
        """Get star by ID from in-memory index."""
        return self._indexes.get_star(id)

    def list_stars(self) -> List[BaseStar]:
        """List all stars."""
        return list(self._indexes.stars.values())

    async def update_star(
        self, id: str, updates: Dict[str, Any]
    ) -> tuple[BaseStar, List[ValidationWarning]]:
        """
        Update star.

        Args:
            id: Star ID to update
            updates: Dictionary of fields to update

        Returns:
            Tuple of (updated star, list of warnings)

        Raises:
            ValidationError: If validation fails or star not found
        """
        existing = self._indexes.get_star(id)
        if not existing:
            raise ValidationError(f"Star '{id}' not found")

        # Apply updates
        updated_data = existing.model_dump()
        updated_data.update(updates)

        # Recreate as correct Star type
        from astro_backend_service.foundry.persistence import STAR_TYPE_MAP

        star_type = updated_data.get("type")
        if star_type and star_type in STAR_TYPE_MAP:
            updated = STAR_TYPE_MAP[star_type].model_validate(updated_data)
        else:
            raise ValidationError(f"Unknown star type: {star_type}")

        # Validate
        warnings = validate_star(updated, self._indexes)

        # Persist to MongoDB
        await self._persistence.replace_star(updated)

        # Update in-memory index
        self._indexes.stars[id] = updated

        return updated, warnings

    async def delete_star(self, id: str) -> bool:
        """
        Delete star.

        - Checks if any Constellations reference this star
        - Fails if referenced
        - Removes from MongoDB and in-memory index

        Args:
            id: Star ID to delete

        Returns:
            True if deleted

        Raises:
            ValidationError: If star is referenced by constellations
        """
        # Check for references
        referencing_constellations = (
            await self._persistence.star_referenced_by_constellations(id)
        )
        if referencing_constellations:
            raise ValidationError(
                f"Cannot delete Star '{id}': referenced by Constellations "
                f"{referencing_constellations}"
            )

        # Delete from MongoDB
        deleted = await self._persistence.delete_star(id)

        # Remove from in-memory index
        if id in self._indexes.stars:
            del self._indexes.stars[id]

        return deleted

    # =========================================================================
    # Constellation CRUD
    # =========================================================================

    async def create_constellation(
        self, constellation: Constellation
    ) -> tuple[Constellation, List[ValidationWarning]]:
        """
        Create a new constellation.

        - Validates all star_ids in nodes exist
        - Validates graph structure (DAG, start/end, etc.)
        - Validates Star type rules
        - Persists to MongoDB
        - Updates in-memory index

        Args:
            constellation: The constellation to create

        Returns:
            Tuple of (created constellation, list of warnings)

        Raises:
            ValidationError: If validation fails
        """
        # Check for duplicate ID
        if constellation.id in self._indexes.constellations:
            raise ValidationError(f"Constellation '{constellation.id}' already exists")

        # Validate
        warnings = validate_constellation(constellation, self._indexes)

        # Persist to MongoDB
        await self._persistence.create_constellation(constellation)

        # Update in-memory index
        self._indexes.constellations[constellation.id] = constellation

        return constellation, warnings

    def get_constellation(self, id: str) -> Optional[Constellation]:
        """Get constellation by ID from in-memory index."""
        return self._indexes.get_constellation(id)

    def list_constellations(self) -> List[Constellation]:
        """List all constellations."""
        return list(self._indexes.constellations.values())

    async def update_constellation(
        self, id: str, updates: Dict[str, Any]
    ) -> tuple[Constellation, List[ValidationWarning]]:
        """
        Update constellation.

        Args:
            id: Constellation ID to update
            updates: Dictionary of fields to update

        Returns:
            Tuple of (updated constellation, list of warnings)

        Raises:
            ValidationError: If validation fails or constellation not found
        """
        existing = self._indexes.get_constellation(id)
        if not existing:
            raise ValidationError(f"Constellation '{id}' not found")

        # Apply updates
        updated_data = existing.model_dump()
        updated_data.update(updates)
        updated = Constellation.model_validate(updated_data)

        # Validate
        warnings = validate_constellation(updated, self._indexes)

        # Persist to MongoDB
        await self._persistence.replace_constellation(updated)

        # Update in-memory index
        self._indexes.constellations[id] = updated

        return updated, warnings

    async def delete_constellation(self, id: str) -> bool:
        """
        Delete constellation.

        Args:
            id: Constellation ID to delete

        Returns:
            True if deleted
        """
        # Delete from MongoDB
        deleted = await self._persistence.delete_constellation(id)

        # Remove from in-memory index
        if id in self._indexes.constellations:
            del self._indexes.constellations[id]

        return deleted

    # =========================================================================
    # Variable Computation
    # =========================================================================

    def compute_constellation_variables(
        self, constellation_id: str
    ) -> List[TemplateVariable]:
        """
        Compute all required variables for a constellation.

        Walks nodes → stars → directives, aggregates template_variables.

        Args:
            constellation_id: ID of constellation

        Returns:
            List of all required TemplateVariables

        Raises:
            ValueError: If constellation not found
        """
        constellation = self.get_constellation(constellation_id)
        if not constellation:
            raise ValueError(f"Constellation '{constellation_id}' not found")

        return constellation.compute_required_variables(self)

    # =========================================================================
    # Run Operations (delegated to persistence)
    # =========================================================================

    async def create_run(self, run: Dict[str, Any]) -> None:
        """Create a new run record."""
        await self._persistence.create_run(run)

    async def get_run(self, id: str) -> Optional[Dict[str, Any]]:
        """Get run by ID."""
        return await self._persistence.get_run(id)

    async def list_runs(
        self, constellation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List runs, optionally filtered by constellation_id."""
        return await self._persistence.list_runs(constellation_id)

    async def update_run(self, id: str, updates: Dict[str, Any]) -> bool:
        """Update run."""
        return await self._persistence.update_run(id, updates)

    async def upsert_run(self, run: Dict[str, Any]) -> None:
        """Upsert run (insert or replace)."""
        await self._persistence.upsert_run(run)

    async def update_run_status(self, id: str, status: str) -> bool:
        """Update run status."""
        return await self._persistence.update_run(id, {"status": status})
