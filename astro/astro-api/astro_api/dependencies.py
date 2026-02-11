"""FastAPI dependencies for V2 architecture.

This module wires up all V2 components with proper dependency injection.
It creates singletons for:
- Registry (core storage)
- SecondBrain (memory management)
- ConstellationRunner (orchestration)
- Interpreter (zero-shot directive selection)
- RunningAgent (zero-shot execution)
- ZeroShotPipeline
- ConstellationPipeline
- LaunchpadController (main entry point)
"""

import logging
import os
from typing import Any, Optional

from cachetools import TTLCache

# TODO: Once Agent 1 & 3 complete, uncomment these imports
# from astro.core.registry import Registry
# from astro.core.memory import SecondBrain, ContextWindow, LongTermMemory
# from astro.orchestration.runner import ConstellationRunner
# from astro_mongodb import MongoDBCoreStorage, MongoDBOrchestrationStorage, MongoDBMemory

# Launchpad components (Phase 4 - completed)
from astro.launchpad import (
    LaunchpadController,
    Conversation,
    Interpreter,
    RunningAgent,
    ZeroShotPipeline,
    ConstellationPipeline,
)

logger = logging.getLogger(__name__)

# Configuration constants
CONVERSATION_CACHE_SIZE = 1000
CONVERSATION_TTL_SECONDS = 3600

# Global singletons
_registry: Optional[Any] = None
_second_brain: Optional[Any] = None
_constellation_runner: Optional[Any] = None
_launchpad_controller: Optional[LaunchpadController] = None

# Conversation cache (TTLCache prevents unbounded memory growth)
_conversations: TTLCache[str, Conversation] = TTLCache(
    maxsize=CONVERSATION_CACHE_SIZE, ttl=CONVERSATION_TTL_SECONDS
)


async def get_registry() -> Any:
    """Get the Registry singleton.

    The Registry provides access to directives, probes, stars, and constellations
    from the configured storage backend.

    Returns:
        Registry instance.
    """
    global _registry
    if _registry is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "astro")

        logger.debug(f"Initializing Registry with db={db_name}")

        # V2: Use MongoDBCoreStorage with Registry
        from astro_mongodb import MongoDBCoreStorage
        from astro.core.registry import Registry

        core_storage = MongoDBCoreStorage(mongo_uri, db_name)
        _registry = Registry(storage=core_storage)
        await _registry.startup()

        logger.info(f"Registry initialized: db={db_name}")

    return _registry


async def get_second_brain() -> Any:
    """Get the SecondBrain singleton.

    The Second Brain manages two memory partitions:
    - Context Window: Recent conversation messages
    - Long-Term Memory: Vector search over historical memories

    Returns:
        SecondBrain instance.
    """
    global _second_brain
    if _second_brain is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "astro")

        logger.debug("Initializing SecondBrain...")

        # TODO: Uncomment once Agent 1 completes
        # from astro_mongodb import MongoDBMemory
        # from astro.core.memory import SecondBrain, ContextWindow, LongTermMemory
        # from astro.core.llm.utils import get_embedding_provider
        #
        # memory_backend = MongoDBMemory(mongo_uri, db_name)
        # await memory_backend.startup()
        #
        # context_window = ContextWindow(max_chars=50000)
        # embedding_provider = get_embedding_provider()
        # long_term = LongTermMemory(
        #     backend=memory_backend,
        #     embedding_provider=embedding_provider,
        # )
        #
        # _second_brain = SecondBrain(context_window, long_term)

        # Temporary: Use placeholder
        class PlaceholderSecondBrain:
            async def retrieve(self, queries, conversation):
                return {"recent_messages": [], "memories": []}

            async def store(self, content, metadata):
                pass

        _second_brain = PlaceholderSecondBrain()

        logger.info("SecondBrain initialized (placeholder)")

    return _second_brain


async def get_constellation_runner() -> Any:
    """Get the ConstellationRunner singleton.

    The ConstellationRunner executes multi-agent constellation workflows
    with topological ordering and parallel execution.

    Returns:
        ConstellationRunner instance.
    """
    global _constellation_runner
    if _constellation_runner is None:
        logger.debug("Initializing ConstellationRunner...")

        registry = await get_registry()

        # Use V1 runner (takes Registry as "foundry" parameter)
        from astro.orchestration.runner import ConstellationRunner
        _constellation_runner = ConstellationRunner(registry)

        logger.info("ConstellationRunner initialized")

    return _constellation_runner


# Orchestration Storage (Layer 2)
_orchestration_storage = None


async def get_orchestration_storage():
    """Get OrchestrationStorage singleton for Stars, Constellations, and Runs.

    Returns:
        MongoDBOrchestrationStorage instance.
    """
    global _orchestration_storage
    if _orchestration_storage is None:
        logger.debug("Initializing OrchestrationStorage...")

        from astro_mongodb import MongoDBOrchestrationStorage

        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "astro")

        _orchestration_storage = MongoDBOrchestrationStorage(mongo_uri, db_name)
        await _orchestration_storage.startup()

        logger.info("OrchestrationStorage initialized")

    return _orchestration_storage


async def get_lightweight_llm() -> Any:
    """Get lightweight LLM for Interpreter (e.g., Haiku).

    Returns:
        LLM provider for directive selection.
    """
    # Use existing V1 LLM utilities
    from astro.core.llm.utils import get_langchain_llm

    # TODO: Consider adding model parameter to use Haiku specifically
    return get_langchain_llm()


async def get_powerful_llm() -> Any:
    """Get powerful LLM for RunningAgent (e.g., Sonnet).

    Returns:
        LLM provider for execution.
    """
    # Use existing V1 LLM utilities
    from astro.core.llm.utils import get_langchain_llm

    return get_langchain_llm()


async def get_zero_shot_pipeline() -> Any:
    """Get the ZeroShotPipeline singleton.

    Returns:
        ZeroShotPipeline instance.
    """
    controller = await get_launchpad_controller()
    return controller.zero_shot


async def get_launchpad_controller() -> LaunchpadController:
    """Get the LaunchpadController singleton.

    The LaunchpadController routes between zero-shot (fast) and
    constellation (thorough) execution modes.

    Returns:
        LaunchpadController instance.
    """
    global _launchpad_controller
    if _launchpad_controller is None:
        logger.debug("Initializing LaunchpadController...")

        # Get dependencies
        registry = await get_registry()
        second_brain = await get_second_brain()
        constellation_runner = await get_constellation_runner()
        lightweight_llm = await get_lightweight_llm()
        powerful_llm = await get_powerful_llm()

        # Import ProbeRegistry (class-level singleton, not an instance)
        from astro.core.probes.registry import ProbeRegistry

        # Create Interpreter (uses lightweight LLM)
        interpreter = Interpreter(
            registry=registry,
            llm_provider=lightweight_llm,
        )

        # Create RunningAgent (uses powerful LLM)
        running_agent = RunningAgent(
            registry=registry,
            llm_provider=powerful_llm,
        )

        # Create DirectiveGenerator and ContextGatherer
        from astro.launchpad.directive_generator import DirectiveGenerator
        from astro.launchpad.context_gatherer import ContextGatherer

        directive_generator = DirectiveGenerator(
            directive_registry=registry,
            probe_registry=ProbeRegistry,  # Pass the class itself (singleton)
            llm=powerful_llm,  # Use powerful LLM for generation
        )

        context_gatherer = ContextGatherer(
            llm=lightweight_llm,  # Use lightweight LLM for analysis
        )

        # Create ZeroShotPipeline
        zero_shot_pipeline = ZeroShotPipeline(
            interpreter=interpreter,
            running_agent=running_agent,
            second_brain=second_brain,
            directive_generator=directive_generator,
            context_gatherer=context_gatherer,
        )

        # Create ConstellationPipeline
        constellation_pipeline = ConstellationPipeline(
            matcher=lightweight_llm,  # For constellation matching
            runner=constellation_runner,
            second_brain=second_brain,
            registry=registry,
        )

        # Create LaunchpadController
        _launchpad_controller = LaunchpadController(
            zero_shot_pipeline=zero_shot_pipeline,
            constellation_pipeline=constellation_pipeline,
        )

        logger.info("LaunchpadController initialized successfully")

    return _launchpad_controller


def get_conversation(conversation_id: str) -> Conversation:
    """Get or create a conversation by ID.

    Args:
        conversation_id: Conversation ID.

    Returns:
        Conversation instance.
    """
    global _conversations
    if conversation_id not in _conversations:
        logger.debug(f"Creating new conversation: {conversation_id}")
        _conversations[conversation_id] = Conversation(id=conversation_id)
    else:
        logger.debug(f"Retrieved existing conversation: {conversation_id}")
    return _conversations[conversation_id]


def create_conversation() -> tuple[str, Conversation]:
    """Create a new conversation and return its ID.

    Returns:
        Tuple of (conversation_id, Conversation).
    """
    import uuid

    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    conversation = Conversation(id=conversation_id)
    _conversations[conversation_id] = conversation
    logger.info(f"Created new conversation: {conversation_id}")
    return conversation_id, conversation


async def get_runner() -> Any:
    """Alias for get_constellation_runner for backward compatibility.

    Returns:
        ConstellationRunner instance.
    """
    return await get_constellation_runner()


async def cleanup() -> None:
    """Cleanup resources on shutdown."""
    global _registry, _second_brain, _constellation_runner, _launchpad_controller, _conversations

    logger.debug("Starting cleanup of global resources...")

    if _registry is not None:
        # Registry cleanup depends on storage backend
        if hasattr(_registry, 'shutdown'):
            await _registry.shutdown()
        _registry = None
        logger.debug("Registry shutdown complete")

    if _second_brain is not None:
        # SecondBrain cleanup
        if hasattr(_second_brain, 'shutdown'):
            await _second_brain.shutdown()
        _second_brain = None
        logger.debug("SecondBrain shutdown complete")

    _constellation_runner = None
    _launchpad_controller = None

    conversation_count = len(_conversations)
    _conversations.clear()
    logger.info(f"Cleanup complete: cleared {conversation_count} conversations")
