"""FastAPI dependencies for dependency injection."""

import os
from typing import Optional

from cachetools import TTLCache

from astro_backend_service.foundry import Foundry
from astro_backend_service.executor import ConstellationRunner
from astro_backend_service.launchpad import TriggeringAgent, Conversation
from astro_backend_service.llm_utils import get_llm


# Global singletons
_foundry: Optional[Foundry] = None
_runner: Optional[ConstellationRunner] = None
_triggering_agent: Optional[TriggeringAgent] = None
# TTLCache prevents unbounded memory growth: max 1000 conversations, 1 hour TTL
_conversations: TTLCache[str, Conversation] = TTLCache(maxsize=1000, ttl=3600)


async def get_foundry() -> Foundry:
    """Get the Foundry singleton."""
    global _foundry
    if _foundry is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "astro")
        _foundry = Foundry(mongo_uri, db_name)
        await _foundry.startup()
    return _foundry


async def get_runner() -> ConstellationRunner:
    """Get the ConstellationRunner singleton."""
    global _runner
    if _runner is None:
        foundry = await get_foundry()
        _runner = ConstellationRunner(foundry)
    return _runner


async def get_triggering_agent() -> TriggeringAgent:
    """Get the TriggeringAgent singleton."""
    global _triggering_agent
    if _triggering_agent is None:
        foundry = await get_foundry()
        llm = get_llm()
        _triggering_agent = TriggeringAgent(foundry, llm_client=llm)
    return _triggering_agent


def get_conversation(conversation_id: str) -> Conversation:
    """Get or create a conversation by ID."""
    global _conversations
    if conversation_id not in _conversations:
        _conversations[conversation_id] = Conversation()
    return _conversations[conversation_id]


def create_conversation() -> tuple[str, Conversation]:
    """Create a new conversation and return its ID."""
    import uuid

    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    conversation = Conversation()
    _conversations[conversation_id] = conversation
    return conversation_id, conversation


async def cleanup() -> None:
    """Cleanup resources on shutdown."""
    global _foundry, _runner, _triggering_agent, _conversations
    if _foundry is not None:
        await _foundry.shutdown()
        _foundry = None
    _runner = None
    _triggering_agent = None
    _conversations.clear()
