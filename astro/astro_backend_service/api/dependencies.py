"""FastAPI dependencies for dependency injection."""

import logging
import os
from typing import Optional

from cachetools import TTLCache

from astro_backend_service.foundry import Foundry
from astro_backend_service.executor import ConstellationRunner
from astro_backend_service.launchpad import TriggeringAgent, Conversation
from astro_backend_service.llm_utils import get_llm

logger = logging.getLogger(__name__)

# Configuration constants
CONVERSATION_CACHE_SIZE = 1000
CONVERSATION_TTL_SECONDS = 3600

# Global singletons
_foundry: Optional[Foundry] = None
_runner: Optional[ConstellationRunner] = None
_triggering_agent: Optional[TriggeringAgent] = None
# TTLCache prevents unbounded memory growth
_conversations: TTLCache[str, Conversation] = TTLCache(
    maxsize=CONVERSATION_CACHE_SIZE, ttl=CONVERSATION_TTL_SECONDS
)


async def get_foundry() -> Foundry:
    """Get the Foundry singleton."""
    global _foundry
    if _foundry is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "astro")
        logger.debug(f"Initializing Foundry with db={db_name}")
        _foundry = Foundry(mongo_uri, db_name)
        await _foundry.startup()
        logger.info(f"Foundry initialized: db={db_name}")
    return _foundry


async def get_runner() -> ConstellationRunner:
    """Get the ConstellationRunner singleton."""
    global _runner
    if _runner is None:
        logger.debug("Initializing ConstellationRunner...")
        foundry = await get_foundry()
        _runner = ConstellationRunner(foundry)
        logger.info("ConstellationRunner initialized")
    return _runner


async def get_triggering_agent() -> TriggeringAgent:
    """Get the TriggeringAgent singleton.

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set.
    """
    global _triggering_agent
    if _triggering_agent is None:
        foundry = await get_foundry()
        llm = get_llm()  # Raises ValueError if OPENAI_API_KEY not set
        _triggering_agent = TriggeringAgent(foundry, llm_client=llm)
        logger.info("TriggeringAgent initialized successfully")
    return _triggering_agent


def get_conversation(conversation_id: str) -> Conversation:
    """Get or create a conversation by ID."""
    global _conversations
    if conversation_id not in _conversations:
        logger.debug(f"Creating new conversation: {conversation_id}")
        _conversations[conversation_id] = Conversation()
    else:
        logger.debug(f"Retrieved existing conversation: {conversation_id}")
    return _conversations[conversation_id]


def create_conversation() -> tuple[str, Conversation]:
    """Create a new conversation and return its ID."""
    import uuid

    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    conversation = Conversation()
    _conversations[conversation_id] = conversation
    logger.info(f"Created new conversation: {conversation_id}")
    return conversation_id, conversation


async def cleanup() -> None:
    """Cleanup resources on shutdown."""
    global _foundry, _runner, _triggering_agent, _conversations
    logger.debug("Starting cleanup of global resources...")
    if _foundry is not None:
        await _foundry.shutdown()
        _foundry = None
        logger.debug("Foundry shutdown complete")
    _runner = None
    _triggering_agent = None
    conversation_count = len(_conversations)
    _conversations.clear()
    logger.info(f"Cleanup complete: cleared {conversation_count} conversations")
