"""API entry point for the Astro Execution Engine.

This module provides the main entry point for running executions.
"""

import os
from typing import Any, Dict, List, Optional
import logging

from execution.models.input import ExecutionInput, ExecutionConfig, ExecutionMode
from execution.models.state import ExecutionState
from execution.star_foundry import ExecutionStarFoundry
from execution.probe_executor import ExecutionProbeExecutor
from execution.orchestrator import Orchestrator

from star_foundry import StarRegistry, MongoStarRepository, StarLoader, StarValidator
from probes import ProbeRegistry
from probes.registry import probe_registry as global_probe_registry

logger = logging.getLogger(__name__)


async def run_execution(
    query: str,
    constellation_id: Optional[str] = None,
    star_ids: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
    config: Optional[ExecutionConfig] = None,
    probe_registry: Optional[ProbeRegistry] = None,
    star_registry: Optional[StarRegistry] = None,
    mongodb_uri: Optional[str] = None,
    mongodb_db: Optional[str] = None,
) -> ExecutionState:
    """Run an Astro execution.

    This is the main entry point for executing AI workflows.

    Args:
        query: The user's query to process
        constellation_id: Optional predefined workflow to use
        star_ids: Optional list of Stars for dynamic planning
        context: Additional context to pass to workers
        config: Execution configuration
        probe_registry: ProbeRegistry instance (uses global if not provided)
        star_registry: StarRegistry instance (loads from MongoDB if not provided)
        mongodb_uri: MongoDB connection URI (from env if not provided)
        mongodb_db: MongoDB database name (from env if not provided)

    Returns:
        ExecutionState with results

    Example:
        ```python
        import asyncio
        from execution import run_execution, ExecutionConfig

        async def main():
            result = await run_execution(
                query="Research the impact of AI on healthcare",
                config=ExecutionConfig(
                    max_phases=5,
                    max_workers_per_phase=4,
                ),
            )
            print(f"Status: {result.status}")
            print(f"Output: {result.final_output}")

        asyncio.run(main())
        ```
    """
    # Use provided or global probe registry
    p_registry = probe_registry or global_probe_registry

    # Initialize star registry if not provided
    if star_registry is None:
        star_registry = await _initialize_star_registry(
            probe_registry=p_registry,
            mongodb_uri=mongodb_uri,
            mongodb_db=mongodb_db,
        )

    # Create execution components
    star_foundry = ExecutionStarFoundry(star_registry)
    probe_executor = ExecutionProbeExecutor(
        probe_registry=p_registry,
        default_timeout=config.tool_timeout if config else 30.0,
    )

    # Create orchestrator
    orchestrator = Orchestrator(
        star_foundry=star_foundry,
        probe_executor=probe_executor,
        config=config,
    )

    # Create execution input
    execution_input = ExecutionInput(
        query=query,
        constellation_id=constellation_id,
        star_ids=star_ids,
        context=context or {},
        config=config or ExecutionConfig(),
    )

    # Run execution
    return await orchestrator.run(execution_input)


async def _initialize_star_registry(
    probe_registry: ProbeRegistry,
    mongodb_uri: Optional[str] = None,
    mongodb_db: Optional[str] = None,
) -> StarRegistry:
    """Initialize the star registry from MongoDB.

    Args:
        probe_registry: The probe registry to use for validation
        mongodb_uri: MongoDB connection URI
        mongodb_db: MongoDB database name

    Returns:
        Initialized StarRegistry
    """
    uri = mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = mongodb_db or os.getenv("MONGODB_DB", "astro")

    # Create registry and validator
    star_registry = StarRegistry(probe_registry=probe_registry)
    validator = StarValidator(
        star_registry=star_registry, probe_registry=probe_registry
    )
    star_registry.validator = validator

    # Try to load from MongoDB
    try:
        repository = MongoStarRepository(uri=uri, db_name=db_name)
        loader = StarLoader(repository=repository, registry=star_registry)
        loader.load_all()
        logger.info(f"Loaded {len(star_registry.list_stars())} stars from MongoDB")
    except Exception as e:
        logger.warning(f"Failed to load stars from MongoDB: {e}")
        logger.info("Proceeding with empty star registry")

    return star_registry


def create_execution_input(
    query: str,
    constellation_id: Optional[str] = None,
    star_ids: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
    mode: ExecutionMode = ExecutionMode.DYNAMIC,
    max_phases: int = 10,
    max_workers_per_phase: int = 8,
    default_model: str = "gpt-4-turbo-preview",
    default_temperature: float = 0.0,
) -> ExecutionInput:
    """Create an ExecutionInput with common defaults.

    Helper function for creating execution inputs with commonly used settings.

    Args:
        query: The user's query
        constellation_id: Optional constellation to use
        star_ids: Optional list of star IDs
        context: Additional context
        mode: Execution mode
        max_phases: Maximum phases allowed
        max_workers_per_phase: Maximum workers per phase
        default_model: LLM model to use
        default_temperature: LLM temperature

    Returns:
        ExecutionInput ready for execution
    """
    config = ExecutionConfig(
        mode=mode,
        max_phases=max_phases,
        max_workers_per_phase=max_workers_per_phase,
        default_model=default_model,
        default_temperature=default_temperature,
    )

    return ExecutionInput(
        query=query,
        constellation_id=constellation_id,
        star_ids=star_ids,
        context=context or {},
        config=config,
    )


class ExecutionEngine:
    """High-level execution engine class for managing executions.

    Provides a stateful interface for running multiple executions
    with shared configuration.
    """

    def __init__(
        self,
        probe_registry: Optional[ProbeRegistry] = None,
        star_registry: Optional[StarRegistry] = None,
        config: Optional[ExecutionConfig] = None,
        mongodb_uri: Optional[str] = None,
        mongodb_db: Optional[str] = None,
    ):
        """Initialize the execution engine.

        Args:
            probe_registry: ProbeRegistry instance
            star_registry: StarRegistry instance
            config: Default execution configuration
            mongodb_uri: MongoDB connection URI
            mongodb_db: MongoDB database name
        """
        self._probe_registry = probe_registry or global_probe_registry
        self._star_registry = star_registry
        self._config = config or ExecutionConfig()
        self._mongodb_uri = mongodb_uri
        self._mongodb_db = mongodb_db
        self._initialized = False

        # Cached components
        self._star_foundry: Optional[ExecutionStarFoundry] = None
        self._probe_executor: Optional[ExecutionProbeExecutor] = None
        self._orchestrator: Optional[Orchestrator] = None

    async def initialize(self) -> None:
        """Initialize the execution engine.

        Loads stars from MongoDB and sets up components.
        """
        if self._initialized:
            return

        # Initialize star registry if not provided
        if self._star_registry is None:
            self._star_registry = await _initialize_star_registry(
                probe_registry=self._probe_registry,
                mongodb_uri=self._mongodb_uri,
                mongodb_db=self._mongodb_db,
            )

        # Create components
        self._star_foundry = ExecutionStarFoundry(self._star_registry)
        self._probe_executor = ExecutionProbeExecutor(
            probe_registry=self._probe_registry,
            default_timeout=self._config.tool_timeout,
        )
        self._orchestrator = Orchestrator(
            star_foundry=self._star_foundry,
            probe_executor=self._probe_executor,
            config=self._config,
        )

        self._initialized = True
        logger.info("Execution engine initialized")

    async def run(
        self,
        query: str,
        constellation_id: Optional[str] = None,
        star_ids: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionState:
        """Run an execution.

        Args:
            query: The user's query
            constellation_id: Optional constellation to use
            star_ids: Optional list of star IDs
            context: Additional context
            config: Config override for this execution

        Returns:
            ExecutionState with results
        """
        await self.initialize()

        execution_input = ExecutionInput(
            query=query,
            constellation_id=constellation_id,
            star_ids=star_ids,
            context=context or {},
            config=config or self._config,
        )

        return await self._orchestrator.run(execution_input)

    @property
    def star_foundry(self) -> Optional[ExecutionStarFoundry]:
        """Get the star foundry."""
        return self._star_foundry

    @property
    def probe_executor(self) -> Optional[ExecutionProbeExecutor]:
        """Get the probe executor."""
        return self._probe_executor

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the engine.

        Returns:
            Dictionary with stats
        """
        stats = {
            "initialized": self._initialized,
            "probes_registered": len(self._probe_registry.list_probes()),
        }

        if self._star_foundry:
            stats.update(self._star_foundry.get_stats())

        return stats
