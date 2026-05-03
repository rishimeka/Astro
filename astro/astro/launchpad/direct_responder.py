"""Direct responder for conversational messages.

Handles messages that don't need directive/tool execution — greetings,
follow-ups, general knowledge, meta-questions about capabilities, etc.
Skips the ReAct loop and tool binding for faster responses.
"""

import logging
from typing import Any

from astro.core.llm.utils import get_default_max_tokens
from astro.core.prompts.base_system_prompt import ASTRO_BASE_SYSTEM_PROMPT
from astro.launchpad.conversation import Conversation
from astro.launchpad.running_agent import AgentOutput, _extract_text_content

logger = logging.getLogger(__name__)


class DirectResponder:
    """Generates conversational responses without directive/tool overhead.

    Used when the Interpreter determines the query is conversational
    (greetings, follow-ups, meta-questions, general knowledge).
    Single LLM call with no tool binding or ReAct loop.
    """

    def __init__(self, llm_provider: Any):
        """Initialize DirectResponder.

        Args:
            llm_provider: LLM provider (powerful model, same as RunningAgent).
        """
        self.llm = llm_provider

    async def respond(
        self,
        conversation: Conversation,
        context: dict[str, Any],
        direct_response_context: str = "",
    ) -> AgentOutput:
        """Generate a direct conversational response.

        Args:
            conversation: Current conversation with messages.
            context: Retrieved context from SecondBrain (recent_messages, memories).
            direct_response_context: Optional context hints from the interpreter.

        Returns:
            AgentOutput with the response content.
        """
        system_prompt = ASTRO_BASE_SYSTEM_PROMPT
        if direct_response_context:
            system_prompt += f"\n\n## Additional Context\n\n{direct_response_context}"

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Add retrieved context
        context_text = self._format_context(context)
        if context_text:
            messages.append(
                {"role": "system", "content": f"Relevant context from memory:\n{context_text}"}
            )

        # Add conversation history
        for msg in conversation.get_context_messages(limit=10):
            messages.append({"role": msg.role, "content": msg.content})

        try:
            response = await self.llm.ainvoke(
                messages, temperature=0.7, max_tokens=get_default_max_tokens()
            )
            content = _extract_text_content(
                response.content if hasattr(response, "content") else str(response)
            )

            return AgentOutput(
                content=content,
                tool_calls=[],
                reasoning="Direct conversational response",
                iterations=1,
            )

        except Exception as e:
            logger.error(f"DirectResponder: Error generating response: {e}", exc_info=True)
            return AgentOutput(
                content=f"Error: {str(e)}",
                tool_calls=[],
                reasoning="Failed direct response",
                iterations=0,
            )

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context dict into a string for the prompt."""
        parts = []

        if context.get("recent_messages"):
            parts.append("Recent conversation:")
            for msg in context["recent_messages"][:5]:
                parts.append(f"- {msg}")

        if context.get("memories"):
            parts.append("\nRelevant information:")
            for memory in context["memories"][:3]:
                parts.append(f"- {memory}")

        return "\n".join(parts) if parts else ""
