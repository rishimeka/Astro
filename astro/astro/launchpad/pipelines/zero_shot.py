"""Zero-shot pipeline for fast query execution.

The zero-shot pipeline is the default execution mode. It's optimized for
speed and handles most queries efficiently without requiring predefined
multi-agent workflows.

## 4-Step Pipeline

1. **Interpret**: Select relevant directives using lightweight LLM
2. **Retrieve**: Get context from Second Brain (recent messages + relevant memories)
3. **Execute**: Run with powerful LLM, scoped tools, ReAct loop
4. **Persist**: Store query and response to Second Brain

This pipeline was 16-19x faster than multi-agent approaches in benchmarks
while maintaining comparable accuracy for most queries.
"""

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from astro.launchpad.conversation import Conversation
from astro.launchpad.interpreter import Interpreter
from astro.launchpad.running_agent import AgentOutput, RunningAgent

logger = logging.getLogger(__name__)


class ZeroShotPipeline:
    """Fast execution mode: 4-step pipeline.

    Default pipeline for handling user queries. Optimized for speed while
    maintaining good quality through intelligent directive selection and
    tool scoping.
    """

    def __init__(
        self,
        interpreter: Interpreter,
        running_agent: RunningAgent,
        second_brain: Any,
        directive_generator: Any = None,
        context_gatherer: Any = None,
    ):
        """Initialize the zero-shot pipeline.

        Args:
            interpreter: Interpreter for directive selection (uses lightweight LLM).
            running_agent: Running agent for execution (uses powerful LLM).
            second_brain: Second Brain for memory management.
            directive_generator: Optional DirectiveGenerator for creating directives on-the-fly.
            context_gatherer: Optional ContextGatherer for gathering requirements.
        """
        self.interpreter = interpreter
        self.running_agent = running_agent
        self.second_brain = second_brain
        self.directive_generator = directive_generator
        self.context_gatherer = context_gatherer

    async def execute_with_events(
        self,
        message: str,
        conversation: Conversation,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute 4-step zero-shot pipeline with progress events.

        Yields SSE events at each step for UI display.

        Args:
            message: User's message/query.
            conversation: Current conversation state.

        Yields:
            Progress events and final AgentOutput.
        """
        # Add the user message to conversation BEFORE interpretation
        conversation.add_message(role="user", content=message)

        # Check for topic change and reset clarification if needed
        if self._should_reset_clarification(message, conversation):
            conversation.clear_clarification()

        # Start clarification session if not already in one
        if not conversation.is_in_clarification():
            conversation.start_clarification(message, max_rounds=3)

        # Step 1: Interpret (evaluate with clarification loop)
        yield {
            "type": "thinking",
            "message": "Analyzing query and selecting directives...",
        }

        interpretation = None
        attempts = 0
        max_attempts = 5  # Safety limit to prevent infinite loops

        while attempts < max_attempts:
            attempts += 1
            result = await self.interpreter.evaluate(conversation)
            conversation.increment_clarification_round(result.model_dump())

            if result.action == "ask_user":
                # Need clarification - save questions to conversation history
                questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(result.questions))
                assistant_message = f"I need more information to help you:\n\n{questions_text}"

                conversation.add_message(role="assistant", content=assistant_message)

                # Yield event for UI
                yield {
                    "type": "clarification_needed",
                    "questions": result.questions,
                    "reasoning": result.reasoning,
                    "round": conversation.clarification_state.rounds_completed,
                    "max_rounds": conversation.clarification_state.max_rounds,
                }
                # Early return - wait for user to provide answers
                return

            elif result.action == "generate_directive":
                # Trigger directive generation
                interpretation = result
                break

            elif result.action == "select_directives":
                # Ready to proceed with directive selection
                interpretation = result
                break

            # Should never reach here, but safety fallback
            logger.warning(
                f"ZeroShotPipeline: Unexpected action '{result.action}' in clarification loop"
            )
            interpretation = result
            break

        # Clear clarification state now that we have a decision
        conversation.clear_clarification()

        if interpretation is None:
            # Fallback if loop exits without interpretation
            from astro.launchpad.interpreter import InterpretationResult

            interpretation = InterpretationResult(
                action="select_directives",
                directive_ids=[],
                context_queries=[message],
                reasoning="Max attempts reached in clarification loop",
                confidence=0.0,
            )

        # Handle directive selection or generation
        if interpretation.directive_ids:
            directive_names = ", ".join(interpretation.directive_ids)
            yield {
                "type": "directive_selected",
                "directive_ids": interpretation.directive_ids,
                "reasoning": interpretation.reasoning,
                "message": f"Selected directives: {directive_names}",
            }
        else:
            # No directives found - try to generate one if possible
            generated_id = None
            async for event in self._try_generate_directive(
                message, conversation, interpretation
            ):
                if event.get("type") == "directive_id":
                    generated_id = event.get("id")
                else:
                    yield event

            if generated_id:
                interpretation.directive_ids = [generated_id]
            else:
                yield {
                    "type": "thinking",
                    "message": "No specialized directives needed - responding directly",
                }

        # Step 2: Retrieve context from Second Brain
        yield {"type": "thinking", "message": "Retrieving relevant context..."}

        context = await self._retrieve_context(
            interpretation.context_queries, conversation
        )

        # Step 3: Execute with running agent (will yield its own events)
        async for event in self._execute_agent_with_events(
            interpretation.directive_ids,
            context,
            conversation,
            message,
            interpreter_reasoning=interpretation.reasoning,
        ):
            yield event

        # Get the final output (last event should be the result)
        # We'll modify _execute_agent_with_events to yield the final output

    async def execute(
        self,
        message: str,
        conversation: Conversation,
    ) -> AgentOutput:
        """Execute 4-step zero-shot pipeline (blocking mode).

        In blocking mode, we cannot ask the user for clarification,
        so we force a decision immediately.

        Args:
            message: User's message/query.
            conversation: Current conversation state.

        Returns:
            AgentOutput with response and execution metadata.
        """
        # Add the user message to conversation BEFORE interpretation
        # The Interpreter needs to see this message to select directives
        conversation.add_message(role="user", content=message)

        # Check for topic change and reset clarification if needed
        if self._should_reset_clarification(message, conversation):
            conversation.clear_clarification()

        # Start clarification with max_rounds=0 to force decision
        # (cannot ask user in blocking mode)
        if not conversation.is_in_clarification():
            conversation.start_clarification(message, max_rounds=0)

        # Step 1: Interpret (force decision in blocking mode)
        interpretation = await self._interpret_with_clarification_blocking(
            message, conversation
        )

        # Clear clarification state
        conversation.clear_clarification()

        # Step 2: Retrieve context from Second Brain
        context = await self._retrieve_context(
            interpretation.context_queries, conversation
        )

        # Step 3: Execute with running agent
        output = await self._execute_agent(
            interpretation.directive_ids,
            context,
            conversation,
            interpreter_reasoning=interpretation.reasoning,
        )

        # Step 4: Persist to Second Brain
        await self._persist_to_memory(message, output, conversation)

        return output

    async def _execute_agent_with_events(
        self,
        directive_ids: list[str],
        context: dict[str, Any],
        conversation: Conversation,
        message: str = "",
        interpreter_reasoning: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute agent and yield progress events.

        Args:
            directive_ids: Selected directive IDs.
            context: Retrieved context.
            conversation: Current conversation.
            message: User message for persistence.
            interpreter_reasoning: Optional reasoning from interpreter.

        Yields:
            Progress events and final output.
        """
        try:
            # Get directives
            directives = await self.running_agent._get_directives(directive_ids)

            if not directives:
                yield {"type": "thinking", "message": "Generating direct response..."}
                output = await self.running_agent._direct_response(
                    conversation, context
                )
                yield {"type": "output", "output": output}
                await self._persist_to_memory(message, output, conversation)
                return

            # Get tools
            yield {"type": "thinking", "message": "Loading specialized tools..."}

            tools = await self.running_agent._get_scoped_tools(directives)

            if tools:
                tool_names = [t.name for t in tools]
                yield {
                    "type": "tools_bound",
                    "tools": tool_names,
                    "message": f"Bound {len(tools)} tools: {', '.join(tool_names[:3])}{'...' if len(tools) > 3 else ''}",
                }

            # Execute with ReAct loop - we'll need to modify RunningAgent to yield events
            yield {"type": "thinking", "message": "Executing query with tools..."}

            # For now, execute and yield result
            # TODO: Make RunningAgent yield events during execution
            output = await self.running_agent.execute(
                directive_ids=directive_ids,
                conversation=conversation,
                context=context,
                interpreter_reasoning=interpreter_reasoning,
            )

            yield {"type": "output", "output": output}

            # Persist to Second Brain
            await self._persist_to_memory(message, output, conversation)

        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}")
            output = AgentOutput(
                content=f"Error: {str(e)}",
                tool_calls=[],
                reasoning="Execution failed",
                iterations=0,
            )
            yield {"type": "output", "output": output}

    async def _interpret(self, message: str, conversation: Conversation) -> Any:
        """Step 1: Interpret query and select relevant directives.

        Uses lightweight LLM (e.g., Haiku) to:
        - Understand query intent
        - Select 0-3 relevant directives
        - Generate context queries for memory retrieval

        Args:
            message: User's message.
            conversation: Current conversation.

        Returns:
            InterpretationResult with selected directives and context queries.
        """
        logger.info("ZeroShotPipeline: Starting interpretation step")
        try:
            result = await self.interpreter.select_directives(conversation)
            logger.info(
                f"ZeroShotPipeline: Interpretation complete - selected {len(result.directive_ids)} directives"
            )
            return result
        except Exception as e:
            # Fallback: empty interpretation
            logger.error(
                f"ZeroShotPipeline: Interpretation failed with error: {str(e)}"
            )
            from astro.launchpad.interpreter import InterpretationResult

            return InterpretationResult(
                action="select_directives",
                directive_ids=[],
                context_queries=[message],
                reasoning=f"Interpretation failed: {str(e)}",
                confidence=0.0,
            )

    async def _interpret_with_clarification_blocking(
        self, message: str, conversation: Conversation
    ) -> Any:
        """Interpret query in blocking mode (force decision, cannot ask user).

        In blocking mode, the interpreter cannot ask for clarification since
        we can't wait for user response. Forces a decision immediately.

        Args:
            message: User's message.
            conversation: Current conversation.

        Returns:
            InterpretationResult with action=select_directives or generate_directive.
        """
        logger.info("ZeroShotPipeline: Starting interpretation (blocking mode)")
        try:
            result = await self.interpreter.evaluate(conversation)

            # If result is ask_user, force it to select_directives
            if result.action == "ask_user":
                logger.warning(
                    "ZeroShotPipeline: Blocking mode cannot ask user, forcing decision"
                )
                from astro.launchpad.interpreter import InterpretationResult

                return InterpretationResult(
                    action="select_directives",
                    directive_ids=[],
                    context_queries=[message],
                    reasoning=f"Blocking mode: {result.reasoning}. Proceeding without clarification.",
                    confidence=result.confidence * 0.5,  # Lower confidence
                )

            logger.info(
                f"ZeroShotPipeline: Interpretation complete (blocking) - action={result.action}"
            )
            return result

        except Exception as e:
            # Fallback: empty interpretation
            logger.error(
                f"ZeroShotPipeline: Interpretation failed with error: {str(e)}"
            )
            from astro.launchpad.interpreter import InterpretationResult

            return InterpretationResult(
                action="select_directives",
                directive_ids=[],
                context_queries=[message],
                reasoning=f"Interpretation failed: {str(e)}",
                confidence=0.0,
            )

    async def _retrieve_context(
        self, context_queries: list[str], conversation: Conversation
    ) -> dict[str, Any]:
        """Step 2: Retrieve context from Second Brain.

        The Second Brain has two partitions:
        - Context Window: Recent conversation messages (fast access)
        - Long-Term Memory: Vector search over historical memories

        Maps SecondBrain output keys to the format expected by RunningAgent:
        - long_term -> memories (as content strings)
        - recent -> recent_messages (as content strings)

        Args:
            context_queries: Queries for retrieval (from interpreter).
            conversation: Current conversation.

        Returns:
            Dict with retrieved context from both memory partitions.
        """
        try:
            raw: dict[str, Any] = await self.second_brain.retrieve(
                queries=context_queries, conversation=conversation
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

    async def _execute_agent(
        self,
        directive_ids: list[str],
        context: dict[str, Any],
        conversation: Conversation,
        interpreter_reasoning: str | None = None,
    ) -> AgentOutput:
        """Step 3: Execute with running agent.

        Uses powerful LLM (e.g., Sonnet) with:
        - Selected directives as system instructions
        - Scoped tools (only tools needed by directives)
        - ReAct loop for reasoning and tool use
        - Retrieved context for grounding

        Args:
            directive_ids: Selected directive IDs.
            context: Retrieved context from Second Brain.
            conversation: Current conversation.
            interpreter_reasoning: Optional reasoning from interpreter.

        Returns:
            AgentOutput with response and execution metadata.
        """
        try:
            output = await self.running_agent.execute(
                directive_ids=directive_ids,
                conversation=conversation,
                context=context,
                interpreter_reasoning=interpreter_reasoning,
            )
            return output

        except Exception as e:
            # Fallback: error message
            return AgentOutput(
                content=f"I encountered an error while processing your request: {str(e)}",
                tool_calls=[],
                reasoning=f"Execution failed: {str(e)}",
                iterations=0,
            )

    async def _persist_to_memory(
        self,
        message: str,
        output: AgentOutput,
        conversation: Conversation,
    ) -> None:
        """Step 4: Persist to Second Brain.

        Store both the user query and assistant response to Second Brain:
        - Context Window: Add as recent messages
        - Long-Term Memory: Store with embeddings for future retrieval

        This ensures future queries can benefit from this interaction.

        Args:
            message: User's message.
            output: Agent output.
            conversation: Current conversation.
        """
        try:
            # Add assistant response to conversation (user message already added in execute())
            conversation.add_message(role="assistant", content=output.content)

            now = datetime.now(UTC).isoformat()

            # Store to Second Brain - combined exchange for better retrieval
            await self.second_brain.store(
                content=f"User: {message}\n\nAssistant: {output.content}",
                metadata={
                    "type": "zero_shot_exchange",
                    "user_query": message,
                    "conversation_id": conversation.id,
                    "timestamp": now,
                    "directive_ids": getattr(output, "directive_ids", []),
                    "tool_calls_count": len(output.tool_calls),
                    "iterations": output.iterations,
                },
            )

        except Exception as e:
            logger.warning(f"SecondBrain persistence failed, continuing: {e}")

    async def _try_generate_directive(
        self,
        message: str,
        conversation: Conversation,
        interpretation: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Attempt to generate a new directive for queries with no matches.

        This method handles the complete generation flow including:
        - Checking if generation is appropriate
        - Context gathering (with user Q&A)
        - Directive generation
        - Human approval
        - Saving to registry

        Args:
            message: User's query
            conversation: Current conversation
            interpretation: InterpretationResult from selection

        Yields:
            SSE events for progress tracking, including final directive_id event
        """
        # Early exit if no generator available
        if not self.directive_generator or not self.context_gatherer:
            return

        # Check if we should offer generation
        should_generate = self.interpreter.should_offer_directive_generation(
            interpretation
        )
        if not should_generate:
            return

        try:
            logger.info("ZeroShotPipeline: Attempting directive generation")

            # Notify user we're creating a directive
            yield {
                "type": "directive_generation_offered",
                "message": "I don't have a specialized workflow for this yet. Let me create one for you.",
            }

            # Step 1: Gather context
            context = await self.context_gatherer.gather_context(message, conversation)

            # Step 2: Generate directive
            generated = await self.directive_generator.generate_directive(context)

            # Step 3: Check for similar directives
            if generated.similarity_score > 0.7 and generated.similar_directive_id:
                logger.info(
                    f"ZeroShotPipeline: Found similar directive {generated.similar_directive_id} "
                    f"with score {generated.similarity_score:.2f}"
                )
                yield {
                    "type": "directive_similar_found",
                    "directive_id": generated.similar_directive_id,
                    "similarity_score": generated.similarity_score,
                    "message": "Found similar directive - using existing one",
                }
                yield {"type": "directive_id", "id": generated.similar_directive_id}
                return

            # Step 4: Request human approval
            # For now, auto-approve (interactive approval will be added with UI)
            directive_id = await self.directive_generator.save_directive(generated)

            logger.info(
                f"ZeroShotPipeline: Saved generated directive with ID {directive_id}"
            )

            yield {
                "type": "directive_generated",
                "directive_id": directive_id,
                "message": "Created new directive for this task",
            }

            # Return the directive ID as a special event
            yield {"type": "directive_id", "id": directive_id}

        except Exception as e:
            logger.error(f"ZeroShotPipeline: Error generating directive: {str(e)}")
            return

    def _should_reset_clarification(
        self, message: str, conversation: Conversation
    ) -> bool:
        """Detect if user changed topic and should reset clarification.

        Detects topic changes by checking for explicit reset phrases
        or significant content mismatch with the original query.

        Args:
            message: Current user message.
            conversation: Current conversation.

        Returns:
            True if clarification should be reset, False otherwise.
        """
        if not conversation.is_in_clarification():
            return False

        # Explicit reset phrases
        reset_phrases = [
            "never mind",
            "nevermind",
            "forget it",
            "new question",
            "different question",
            "change topic",
            "actually",
            "instead",
        ]
        message_lower = message.lower()
        if any(phrase in message_lower for phrase in reset_phrases):
            logger.info(
                f"ZeroShotPipeline: Topic change detected (explicit phrase): {message[:50]}"
            )
            return True

        # Check word overlap with original query
        original = conversation.clarification_state.original_query.lower()
        original_words = set(original.split())
        message_words = set(message_lower.split())

        # Filter out common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "has",
            "have",
            "had",
            "do",
            "does",
            "did",
            "can",
            "could",
            "will",
            "would",
            "should",
            "may",
            "might",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
        }
        original_words = original_words - stop_words
        message_words = message_words - stop_words

        # If less than 30% word overlap, likely a topic change
        if original_words and message_words:
            overlap = len(original_words & message_words)
            overlap_ratio = overlap / max(len(original_words), len(message_words))

            if overlap_ratio < 0.3:
                logger.info(
                    f"ZeroShotPipeline: Topic change detected (low word overlap {overlap_ratio:.2f})"
                )
                return True

        return False
