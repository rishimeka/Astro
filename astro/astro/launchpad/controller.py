"""Launchpad Controller for routing between execution modes.

The LaunchpadController is the main entry point for query execution. It routes
between two execution modes:

1. **Zero-shot mode (default)**: Fast, efficient execution with directive selection
2. **Constellation mode (research)**: Thorough, deep analysis with multi-agent workflows

The choice is made based on the research_mode flag, allowing users to opt-in to
deeper analysis when needed.
"""

from typing import Any

from pydantic import BaseModel, Field

from astro.launchpad.conversation import Conversation
from astro.launchpad.pipelines.constellation import (
    ConstellationPipeline,
    ConstellationPipelineOutput,
)
from astro.launchpad.pipelines.zero_shot import ZeroShotPipeline
from astro.launchpad.running_agent import AgentOutput


class Response(BaseModel):
    """Unified response from launchpad controller."""

    content: str = Field(..., description="Response content")
    mode: str = Field(..., description="Execution mode: 'zero_shot' or 'constellation'")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )


class LaunchpadController:
    """Routes between zero-shot and constellation execution modes.

    The controller provides a unified interface for query execution while
    allowing different execution strategies based on user preferences.

    Default: Zero-shot (fast)
    Research mode: Constellation (thorough)
    """

    def __init__(
        self,
        zero_shot_pipeline: ZeroShotPipeline,
        constellation_pipeline: ConstellationPipeline,
    ):
        """Initialize the launchpad controller.

        Args:
            zero_shot_pipeline: Pipeline for fast zero-shot execution.
            constellation_pipeline: Pipeline for thorough constellation execution.
        """
        self.zero_shot = zero_shot_pipeline
        self.constellation = constellation_pipeline

    async def handle_message(
        self,
        message: str,
        conversation: Conversation,
        research_mode: bool = False,
    ) -> Response:
        """Route to appropriate pipeline and handle message.

        Args:
            message: User's message/query.
            conversation: Current conversation state.
            research_mode: If True, use constellation pipeline for deeper analysis.
                If False (default), use zero-shot pipeline for fast execution.

        Returns:
            Response with content and execution metadata.
        """
        if research_mode:
            return await self._execute_constellation_mode(message, conversation)
        else:
            return await self._execute_zero_shot_mode(message, conversation)

    async def _execute_zero_shot_mode(
        self, message: str, conversation: Conversation
    ) -> Response:
        """Execute in zero-shot mode (fast, default).

        Zero-shot mode:
        - Uses lightweight LLM for directive selection
        - Uses powerful LLM for execution
        - Scopes tools to only what's needed
        - ReAct loop for reasoning and tool use
        - Fast: typically 2-5 seconds

        Args:
            message: User's message.
            conversation: Current conversation.

        Returns:
            Response with execution results.
        """
        try:
            output: AgentOutput = await self.zero_shot.execute(message, conversation)

            return Response(
                content=output.content,
                mode="zero_shot",
                metadata={
                    "iterations": output.iterations,
                    "tool_calls": len(output.tool_calls),
                    "reasoning": output.reasoning,
                },
            )

        except Exception as e:
            return Response(
                content=f"I encountered an error while processing your request: {str(e)}",
                mode="zero_shot",
                metadata={"error": str(e)},
            )

    async def _execute_constellation_mode(
        self, message: str, conversation: Conversation
    ) -> Response:
        """Execute in constellation mode (thorough, research).

        Constellation mode:
        - Matches query to predefined workflows
        - Extracts variables from query/conversation
        - Executes multi-agent constellation
        - Synthesizes results from multiple agents
        - Thorough: typically 15-60 seconds

        Args:
            message: User's message.
            conversation: Current conversation.

        Returns:
            Response with execution results.
        """
        try:
            output: ConstellationPipelineOutput = await self.constellation.execute(
                message, conversation
            )

            return Response(
                content=output.content,
                mode="constellation",
                metadata={
                    "run_id": output.run_id,
                    "constellation_id": output.constellation_id,
                    "constellation_name": output.constellation_name,
                    "reasoning": output.reasoning,
                },
            )

        except Exception as e:
            return Response(
                content=f"I encountered an error during research execution: {str(e)}",
                mode="constellation",
                metadata={"error": str(e)},
            )

    async def get_conversation_history(
        self, conversation_id: str
    ) -> Conversation | None:
        """Retrieve conversation history by ID.

        This is a convenience method for API routes that need to load
        conversation state before handling messages.

        Args:
            conversation_id: Conversation ID to retrieve.

        Returns:
            Conversation object or None if not found.
        """
        # TODO: Implement conversation persistence via Second Brain or separate storage
        # For now, this is a placeholder
        return None

    async def create_conversation(self, user_id: str | None = None) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: Optional user ID for the conversation.

        Returns:
            New Conversation object.
        """
        return Conversation(user_id=user_id)
