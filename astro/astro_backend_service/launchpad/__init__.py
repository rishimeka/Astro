"""Launchpad module - conversational interface for Astro.

Launchpad is the orchestration layer on top of the Execution Engine.
It provides a conversational interface that can handle simple queries
directly or route complex queries through constellation execution.

Example:
    from astro_backend_service.launchpad import TriggeringAgent, Conversation

    agent = TriggeringAgent(foundry)
    conversation = Conversation()

    response = await agent.process_message(
        "Analyze Tesla's financials",
        conversation
    )

    print(f"Action: {response.action}")
    print(f"Response: {response.response}")
"""

from astro_backend_service.launchpad.conversation import (
    Conversation,
    Message,
    PendingConstellation,
)
from astro_backend_service.launchpad.generic_constellation import (
    clear_generic_constellation_cache,
    create_generic_constellation,
    get_or_create_generic_constellation,
)
from astro_backend_service.launchpad.matching import (
    ConstellationMatch,
    find_matching_constellation,
    get_all_constellation_summaries,
)
from astro_backend_service.launchpad.preferences import UserSynthesisPreferences
from astro_backend_service.launchpad.synthesis import SynthesisAgent
from astro_backend_service.launchpad.tools import (
    analyze_constellation,
    get_constellation_summary,
    invoke_constellation,
    invoke_generic_constellation,
)
from astro_backend_service.launchpad.triggering_agent import (
    TriggeringAgent,
    TriggeringResponse,
)

__all__ = [
    # Core agent
    "TriggeringAgent",
    "TriggeringResponse",
    # Conversation
    "Conversation",
    "Message",
    "PendingConstellation",
    # Preferences
    "UserSynthesisPreferences",
    # Synthesis
    "SynthesisAgent",
    # Matching
    "ConstellationMatch",
    "find_matching_constellation",
    "get_all_constellation_summaries",
    # Tools
    "invoke_constellation",
    "invoke_generic_constellation",
    "analyze_constellation",
    "get_constellation_summary",
    # Generic constellation
    "create_generic_constellation",
    "get_or_create_generic_constellation",
    "clear_generic_constellation_cache",
]
