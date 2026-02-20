"""Constellation pipeline for thorough research execution.

The constellation pipeline is the research mode execution path. It's optimized
for depth and thoroughness, using predefined multi-agent workflows for complex
analytical tasks.

## 4-Step Pipeline

1. **Match**: Find matching constellation and prepare variables
2. **Retrieve**: Get context from Second Brain (recent messages + relevant memories)
3. **Execute**: Run constellation workflow with ConstellationRunner
4. **Persist**: Store query, run, and response to Second Brain

This pipeline is slower but provides more comprehensive analysis through
coordinated multi-agent workflows.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from astro.launchpad.conversation import Conversation

logger = logging.getLogger(__name__)


class ConstellationPipelineOutput(BaseModel):
    """Output from constellation pipeline execution."""

    content: str = Field(..., description="Final response content")
    run_id: str = Field(..., description="Constellation run ID")
    constellation_id: str = Field(..., description="Executed constellation ID")
    constellation_name: str = Field(..., description="Constellation name")
    reasoning: str = Field(default="", description="Matching and execution reasoning")


class ConstellationPipeline:
    """Thorough execution mode: 4-step pipeline with constellation.

    Research mode pipeline for complex queries requiring coordinated
    multi-agent analysis. Uses predefined workflows for thoroughness.
    """

    def __init__(
        self,
        matcher: Any,
        runner: Any,
        second_brain: Any,
        registry: Any,
    ):
        """Initialize the constellation pipeline.

        Args:
            matcher: ConstellationMatcher for finding matching constellations.
            runner: ConstellationRunner for executing workflows.
            second_brain: Second Brain for memory management.
            registry: Registry for retrieving constellations.
        """
        self.matcher = matcher
        self.runner = runner
        self.second_brain = second_brain
        self.registry = registry

    async def execute(
        self,
        message: str,
        conversation: Conversation,
    ) -> ConstellationPipelineOutput:
        """Execute 4-step constellation pipeline.

        Args:
            message: User's message/query.
            conversation: Current conversation state.

        Returns:
            ConstellationPipelineOutput with response and execution metadata.
        """
        # Step 1: Match constellation and prepare variables
        constellation, variables, reasoning = await self._match_and_prepare(
            message, conversation
        )

        if not constellation:
            # Fallback: return error message
            return ConstellationPipelineOutput(
                content="I couldn't find a suitable workflow for this query. Try rephrasing or use standard mode.",
                run_id="",
                constellation_id="",
                constellation_name="",
                reasoning=reasoning or "No matching constellation found",
            )

        # Step 2: Retrieve context from Second Brain
        context = await self._retrieve_context(message, conversation)

        # Step 3: Execute constellation
        run = await self._execute_constellation(constellation, variables, context)

        if not run:
            return ConstellationPipelineOutput(
                content="Constellation execution failed. Please try again.",
                run_id="",
                constellation_id=constellation.id,
                constellation_name=constellation.name,
                reasoning="Execution error",
            )

        # Step 4: Persist to Second Brain
        await self._persist_to_memory(message, run, conversation)

        # Format response
        return self._format_response(run, constellation, reasoning)

    async def _match_and_prepare(
        self, message: str, conversation: Conversation
    ) -> tuple[Any | None, dict[str, Any], str]:
        """Step 1: Match constellation and prepare variables.

        Uses constellation matcher to:
        - Find constellation matching query intent
        - Extract variable values from query/conversation
        - Identify missing required variables

        Args:
            message: User's message.
            conversation: Current conversation.

        Returns:
            Tuple of (constellation, variables, reasoning).
        """
        try:
            from astro.launchpad.matching import (
                find_matching_constellation,
                get_all_constellation_summaries,
            )

            # Get available constellations
            summaries = get_all_constellation_summaries(self.registry)

            # Find match
            match = find_matching_constellation(
                query=message,
                conversation_history=conversation.messages,
                constellation_summaries=summaries,
                llm_client=self.matcher,  # LLM for matching
            )

            if not match or not match.constellation_id:
                return None, {}, "No matching constellation found"

            # Check if all required variables are present
            if not match.is_complete():
                missing_str = ", ".join(match.missing_variables)
                reasoning = f"Missing required variables: {missing_str}"
                return None, {}, reasoning

            # Get constellation object
            constellation = await self.registry.get_constellation(
                match.constellation_id
            )

            if not constellation:
                return None, {}, f"Constellation {match.constellation_id} not found"

            reasoning = f"Matched constellation '{constellation.name}' with confidence {match.confidence}"
            return constellation, match.extracted_variables, reasoning

        except Exception as e:
            return None, {}, f"Matching error: {str(e)}"

    async def _retrieve_context(
        self, message: str, conversation: Conversation
    ) -> dict[str, Any]:
        """Step 2: Retrieve context from Second Brain.

        The Second Brain has two partitions:
        - Context Window: Recent conversation messages (fast access)
        - Long-Term Memory: Vector search over historical memories

        Args:
            message: User's message.
            conversation: Current conversation.

        Returns:
            Dict with retrieved context from both memory partitions.
        """
        try:
            raw: dict[str, Any] = await self.second_brain.retrieve(
                queries=[message], conversation=conversation
            )

            # Map SecondBrain output to RunningAgent expected format
            recent = raw.get("recent", [])
            long_term = raw.get("long_term", [])

            return {
                "recent_messages": [
                    getattr(m, "content", str(m)) for m in recent
                ],
                "memories": [
                    getattr(m, "content", str(m)) for m in long_term
                ],
            }

        except Exception as e:
            logger.warning(f"SecondBrain retrieval failed, continuing without memory: {e}")
            return {
                "recent_messages": [],
                "memories": [],
            }

    async def _execute_constellation(
        self,
        constellation: Any,
        variables: dict[str, Any],
        context: dict[str, Any],
    ) -> Any | None:
        """Step 3: Execute constellation workflow.

        Uses ConstellationRunner to execute the multi-agent workflow:
        - Topological execution of constellation graph
        - Variable substitution
        - Context injection
        - Parallel execution where possible

        Args:
            constellation: Constellation to execute.
            variables: Extracted variables.
            context: Retrieved context from Second Brain.

        Returns:
            Run object with execution results, or None on failure.
        """
        try:
            # Add context to variables (available to all stars)
            execution_context = {
                **variables,
                "second_brain_context": context,
                "original_query": variables.get("original_query", ""),
            }

            # Execute constellation
            run = await self.runner.execute(
                constellation=constellation,
                variables=execution_context,
            )

            return run

        except Exception as e:
            # Log error and return None
            print(f"Constellation execution error: {e}")
            return None

    async def _persist_to_memory(
        self,
        message: str,
        run: Any,
        conversation: Conversation,
    ) -> None:
        """Step 4: Persist to Second Brain.

        Store query, run details, and response to Second Brain:
        - Context Window: Add as recent messages
        - Long-Term Memory: Store with embeddings for future retrieval

        This ensures future queries can benefit from this interaction.

        Args:
            message: User's message.
            run: Constellation run object.
            conversation: Current conversation.
        """
        try:
            # Get final output from run
            final_output = run.output if hasattr(run, "output") else ""

            # Add messages to conversation (in-memory)
            conversation.add_message(
                role="user",
                content=message,
                run_id=run.id,
                constellation_id=run.constellation_id,
            )
            conversation.add_message(
                role="assistant", content=final_output, run_id=run.id
            )

            now = datetime.now(UTC).isoformat()
            run_id = run.id if hasattr(run, "id") else ""
            constellation_id = run.constellation_id if hasattr(run, "constellation_id") else ""

            # Store combined exchange to Second Brain
            await self.second_brain.store(
                content=f"User: {message}\n\nConstellation Response: {final_output}",
                metadata={
                    "type": "constellation_exchange",
                    "user_query": message,
                    "conversation_id": conversation.id,
                    "run_id": run_id,
                    "constellation_id": constellation_id,
                    "timestamp": now,
                    "status": run.status if hasattr(run, "status") else "completed",
                },
            )

        except Exception as e:
            logger.warning(f"SecondBrain persistence failed, continuing: {e}")

    def _format_response(
        self, run: Any, constellation: Any, reasoning: str
    ) -> ConstellationPipelineOutput:
        """Format run results into pipeline output.

        Args:
            run: Constellation run object.
            constellation: Executed constellation.
            reasoning: Matching reasoning.

        Returns:
            Formatted ConstellationPipelineOutput.
        """
        # Get final output
        content = run.output if hasattr(run, "output") else ""

        if not content:
            content = "Constellation executed successfully but produced no output."

        return ConstellationPipelineOutput(
            content=content,
            run_id=run.id,
            constellation_id=constellation.id,
            constellation_name=constellation.name,
            reasoning=reasoning,
        )
