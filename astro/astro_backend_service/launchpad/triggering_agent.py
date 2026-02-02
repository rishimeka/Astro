"""Triggering agent - the conversational router for Launchpad."""

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from astro_backend_service.launchpad.conversation import (
    Conversation,
)
from astro_backend_service.launchpad.matching import (
    ConstellationMatch,
    find_matching_constellation,
    get_all_constellation_summaries,
)
from astro_backend_service.launchpad.preferences import UserSynthesisPreferences
from astro_backend_service.launchpad.synthesis import SynthesisAgent
from astro_backend_service.launchpad.tools import analyze_constellation

if TYPE_CHECKING:
    from astro_backend_service.executor.stream import ExecutionStream


class TriggeringResponse(BaseModel):
    """Response from the triggering agent."""

    action: Literal[
        "direct_answer",
        "constellation_invoked",
        "generic_invoked",
        "follow_up",
        "clarification",
    ] = Field(..., description="What action was taken")

    response: str = Field(..., description="The response text")

    constellation_id: Optional[str] = Field(
        default=None, description="Constellation ID if invoked"
    )
    run_id: Optional[str] = Field(
        default=None, description="Run ID if execution was triggered"
    )
    missing_variables: List[str] = Field(
        default_factory=list, description="Missing variables if follow-up needed"
    )


class TriggeringAgent:
    """Conversational router that decides how to handle user queries.

    The triggering agent:
    1. Determines if a query is simple or complex
    2. For simple queries, provides direct answers
    3. For complex queries, finds matching constellations
    4. Handles missing variables with follow-up questions
    5. Falls back to generic constellation when no match
    """

    def __init__(
        self,
        foundry: Any,
        llm_client: Any = None,
        user_preferences: Optional[UserSynthesisPreferences] = None,
    ) -> None:
        """Initialize the triggering agent.

        Args:
            foundry: The Foundry instance for constellation lookups.
            llm_client: Optional LLM client (stub if None).
            user_preferences: Optional user preferences for synthesis.
        """
        self.foundry = foundry
        self.llm_client = llm_client
        self.user_preferences = user_preferences
        self._constellation_summaries: Optional[List[Dict[str, Any]]] = None

    def get_constellation_summaries(self) -> List[Dict[str, Any]]:
        """Get or cache constellation summaries."""
        if self._constellation_summaries is None:
            self._constellation_summaries = get_all_constellation_summaries(
                self.foundry
            )
        return self._constellation_summaries

    async def process_message(
        self,
        message: str,
        conversation: Conversation,
        stream: Optional["ExecutionStream"] = None,
    ) -> TriggeringResponse:
        """Process a user message and determine the appropriate action.

        Decision tree:
        0. PENDING CONSTELLATION → Try to extract next variable
           → If complete: invoke the constellation
           → If still missing: ask for next variable
        1. SIMPLE QUERY → Answer directly (no tools)
        2. COMPLEX + MATCHING CONSTELLATION EXISTS
           → Extract variables from conversation
           → If missing required: Store pending + ask follow-up
           → Otherwise: invoke_constellation
        3. COMPLEX + NO MATCHING CONSTELLATION (or fallback)
           → Ask clarifying questions to gather context
           → Once sufficient: invoke_generic_constellation

        Args:
            message: The user's message.
            conversation: The conversation context.
            stream: Optional execution stream for real-time events.

        Returns:
            TriggeringResponse with action and response.
        """
        # Add user message to conversation
        conversation.add_message("user", message)

        # Step 0: Check for pending constellation awaiting variables
        if conversation.has_pending_constellation():
            return await self._handle_pending_constellation(
                message, conversation, stream
            )

        # Step 1: Check if simple query
        if self._is_simple_query(message):
            response = await self._generate_direct_answer(message, conversation)
            return TriggeringResponse(
                action="direct_answer",
                response=response,
            )

        # Step 2: Try to find matching constellation
        summaries = self.get_constellation_summaries()
        match = find_matching_constellation(
            message,
            conversation.messages,
            summaries,
            self.llm_client,
        )

        if match is not None:
            # Check if variables are complete
            if match.is_complete():
                # Invoke the constellation
                result = await self._invoke_constellation(
                    match.constellation_id,
                    match.extracted_variables,
                    message,
                    stream,
                )
                return TriggeringResponse(
                    action="constellation_invoked",
                    response=result.get("output") or "",
                    constellation_id=match.constellation_id,
                    run_id=result.get("run_id"),
                )
            else:
                # Store pending constellation and ask for first missing variable
                return self._start_variable_collection(match, conversation)

        # Step 3: No matching constellation - gather clarifications or use generic
        # Check if we have enough context already
        if self._has_sufficient_context(message, conversation):
            result = await self._invoke_generic_constellation(
                message, conversation, stream
            )
            return TriggeringResponse(
                action="generic_invoked",
                response=result.get("output") or "",
                run_id=result.get("run_id"),
            )
        else:
            # Ask for clarifications
            clarification = self._gather_clarifications(
                message, conversation, summaries
            )
            return TriggeringResponse(
                action="clarification",
                response=clarification,
            )

    def _is_simple_query(self, message: str) -> bool:
        """Determine if a query is simple enough for a direct answer.

        Simple queries:
        - Conversational messages (greetings, thanks, questions about the assistant)
        - Factual questions with definitive answers
        - Short queries that don't require complex workflows

        Args:
            message: The user's message.

        Returns:
            True if the query is simple.
        """
        message_lower = message.lower().strip()

        # Check for greetings
        greetings = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        ]
        if message_lower in greetings or any(
            message_lower.startswith(g) for g in greetings
        ):
            return True

        # Questions about the assistant itself (must be short to avoid matching requests)
        assistant_questions = [
            "what is your name",
            "what's your name",
            "who are you",
            "what can you do",
            "how do you work",
            "what are you",
            "tell me about yourself",
        ]
        if any(q in message_lower for q in assistant_questions):
            return True

        # Short capability questions (not requests to do something)
        # "can you help" is simple, but "can you create a report" is not
        if len(message.split()) <= 6:
            capability_questions = ["are you", "can you", "do you", "will you"]
            if any(message_lower.startswith(q) for q in capability_questions):
                # But not if followed by action verbs
                action_verbs = [
                    "create",
                    "make",
                    "build",
                    "analyze",
                    "research",
                    "write",
                    "generate",
                    "find",
                    "search",
                    "compare",
                    "investigate",
                ]
                if not any(v in message_lower for v in action_verbs):
                    return True

        # Conversational phrases
        conversational = [
            "thank",
            "thanks",
            "please",
            "sorry",
            "ok",
            "okay",
            "yes",
            "no",
            "sure",
            "got it",
            "i see",
            "understood",
        ]
        if any(
            message_lower.startswith(c) or message_lower == c for c in conversational
        ):
            return True

        # Very short queries that are likely simple
        if len(message.split()) <= 5:
            # But not if they contain complex keywords
            complex_keywords = [
                "analyze",
                "compare",
                "research",
                "investigate",
                "plan",
                "create",
                "build",
                "implement",
                "design",
                "develop",
            ]
            if not any(kw in message_lower for kw in complex_keywords):
                return True

        # Questions about basic facts
        simple_patterns = [
            "what is the capital of",
            "what time is it",
            "what day is it",
            "who is the",
            "when was",
            "where is",
            "how many",
            "how much",
        ]
        if any(message_lower.startswith(p) for p in simple_patterns):
            return True

        return False

    async def _generate_direct_answer(
        self, message: str, conversation: Conversation
    ) -> str:
        """Generate a direct answer for a simple query using the LLM.

        Args:
            message: The user's message.
            conversation: The conversation context.

        Returns:
            The direct answer.
        """
        if self.llm_client is None:
            # Fallback for when no LLM is available
            message_lower = message.lower().strip()
            if any(g in message_lower for g in ["hello", "hi", "hey"]):
                return "Hello! How can I help you today?"
            return "I'd be happy to help with that, but I need more context."

        from langchain_core.messages import HumanMessage, SystemMessage

        # Build conversation history for context
        from langchain_core.messages import AIMessage, BaseMessage

        history_messages: List[BaseMessage] = []
        for msg in conversation.messages[-6:]:  # Last 6 messages for context
            if msg.role == "user":
                history_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history_messages.append(AIMessage(content=msg.content))

        system_prompt = """You are Astro, a helpful AI assistant for Astrix Labs. You help users with their questions and tasks.

For simple conversational queries:
- Be friendly and concise
- Answer directly without unnecessary elaboration
- If asked about yourself, explain you're Astro, an AI assistant that can help with various tasks including running specialized workflows called "constellations"

Keep responses brief and natural."""

        messages = [
            SystemMessage(content=system_prompt),
            *history_messages,
            HumanMessage(content=message),
        ]

        try:
            response = self.llm_client.invoke(messages)
            return response.content
        except Exception:
            # Fallback on error
            return "I'm having trouble processing that right now. Could you try again?"

    def _ask_follow_up(
        self,
        missing_variables: List[str],
        match: ConstellationMatch,
    ) -> str:
        """Generate follow-up questions for missing variables.

        Args:
            missing_variables: List of missing variable names.
            match: The constellation match.

        Returns:
            Follow-up question string.
        """
        if len(missing_variables) == 1:
            return f"To help with this, I need to know: What is the {missing_variables[0]}?"

        var_list = ", ".join(missing_variables[:-1]) + f" and {missing_variables[-1]}"
        return f"To help with this, I need a few more details: What are the {var_list}?"

    def _start_variable_collection(
        self,
        match: ConstellationMatch,
        conversation: Conversation,
    ) -> TriggeringResponse:
        """Start collecting variables for a matched constellation.

        Stores the pending constellation state and asks for the first variable.

        Args:
            match: The constellation match with missing variables.
            conversation: The conversation to store state in.

        Returns:
            TriggeringResponse asking for the first missing variable.
        """
        # Get constellation name for user-friendly messages
        constellation = self.foundry.get_constellation(match.constellation_id)
        constellation_name = (
            constellation.name if constellation else match.constellation_id
        )

        # Get variable descriptions from the constellation summary
        summaries = self.get_constellation_summaries()
        var_descriptions: Dict[str, str] = {}
        for summary in summaries:
            if summary["id"] == match.constellation_id:
                for var_info in summary.get("required_variables", []):
                    var_descriptions[var_info["name"]] = var_info.get(
                        "description", f"the {var_info['name']}"
                    )
                break

        # Store pending constellation state
        conversation.set_pending_constellation(
            constellation_id=match.constellation_id,
            constellation_name=constellation_name,
            collected_variables=match.extracted_variables,
            missing_variables=match.missing_variables,
            variable_descriptions=var_descriptions,
        )

        # Ask for the first missing variable
        first_missing = match.missing_variables[0]
        question = self._format_variable_question(
            first_missing,
            var_descriptions.get(first_missing, f"the {first_missing}"),
            constellation_name,
            is_first=True,
        )

        return TriggeringResponse(
            action="follow_up",
            response=question,
            constellation_id=match.constellation_id,
            missing_variables=match.missing_variables,
        )

    async def _handle_pending_constellation(
        self,
        message: str,
        conversation: Conversation,
        stream: Optional["ExecutionStream"] = None,
    ) -> TriggeringResponse:
        """Handle a message when there's a pending constellation awaiting variables.

        Args:
            message: The user's message (expected to contain the variable value).
            conversation: The conversation with pending constellation state.
            stream: Optional execution stream for real-time events.

        Returns:
            TriggeringResponse - either invoking the constellation or asking for more.
        """
        pending = conversation.pending_constellation
        if not pending:
            # Shouldn't happen, but handle gracefully
            conversation.clear_pending_constellation()
            return TriggeringResponse(
                action="direct_answer",
                response="I'm sorry, I lost track of our conversation. How can I help you?",
            )

        # The user's message should be the value for the next missing variable
        if pending.missing_variables:
            next_var = pending.missing_variables[0]

            # Use the message as the variable value
            # Clean up the value (strip whitespace, handle common patterns)
            value = self._extract_variable_value(message, next_var)

            # Add the collected variable (this also removes it from missing_variables)
            conversation.add_collected_variable(next_var, value)

        # Check if we now have all variables
        if conversation.is_pending_complete():
            # All variables collected - invoke the constellation
            constellation_id = pending.constellation_id
            variables = pending.collected_variables.copy()
            constellation_name = pending.constellation_name

            # Clear pending state before invoking
            conversation.clear_pending_constellation()

            # Build original query from conversation
            original_query = self._build_original_query(conversation)

            result = await self._invoke_constellation(
                constellation_id,
                variables,
                original_query,
                stream,
            )

            return TriggeringResponse(
                action="constellation_invoked",
                response=f"Running {constellation_name}...\n\n{result.get('output') or ''}",
                constellation_id=constellation_id,
                run_id=result.get("run_id"),
            )
        else:
            # Still have missing variables - ask for the next one
            next_var = pending.missing_variables[0]
            question = self._format_variable_question(
                next_var,
                pending.variable_descriptions.get(next_var, f"the {next_var}"),
                pending.constellation_name,
                is_first=False,
            )

            return TriggeringResponse(
                action="follow_up",
                response=question,
                constellation_id=pending.constellation_id,
                missing_variables=pending.missing_variables,
            )

    def _format_variable_question(
        self,
        var_name: str,
        var_description: str,
        constellation_name: str,
        is_first: bool,
    ) -> str:
        """Format a question asking for a specific variable.

        Args:
            var_name: The variable name.
            var_description: Human-readable description of the variable.
            constellation_name: The constellation being invoked.
            is_first: Whether this is the first variable being asked for.

        Returns:
            A conversational question for the user.
        """
        # Format variable name for display (replace underscores, capitalize)
        display_name = var_name.replace("_", " ")

        if is_first:
            return (
                f"I can help you with {constellation_name}. "
                f"What {display_name} would you like me to use?"
            )
        else:
            return f"Got it. And what {display_name} would you like?"

    def _extract_variable_value(self, message: str, var_name: str) -> str:
        """Extract the variable value from the user's message.

        For now, uses simple heuristics. With full LLM integration,
        this would use the LLM to extract the intended value.

        Args:
            message: The user's message.
            var_name: The variable name being collected.

        Returns:
            The extracted value.
        """
        # Clean up the message
        value = message.strip()

        # Remove common prefixes like "it's", "the", "I want", etc.
        prefixes_to_remove = [
            "it's ",
            "its ",
            "the ",
            "i want ",
            "i'd like ",
            "please use ",
            "use ",
            "let's go with ",
            "how about ",
        ]
        value_lower = value.lower()
        for prefix in prefixes_to_remove:
            if value_lower.startswith(prefix):
                value = value[len(prefix) :]
                break

        return value.strip()

    def _build_original_query(self, conversation: Conversation) -> str:
        """Build the original query from conversation context.

        Args:
            conversation: The conversation.

        Returns:
            The reconstructed query for the constellation.
        """
        # Find the first user message that triggered the constellation match
        user_messages = [m for m in conversation.messages if m.role == "user"]
        if user_messages:
            # The first message in this sequence is likely the original query
            # (before variable collection started)
            return user_messages[0].content
        return ""

    def _has_sufficient_context(self, message: str, conversation: Conversation) -> bool:
        """Check if we have enough context for generic execution.

        Args:
            message: The user's message.
            conversation: The conversation context.

        Returns:
            True if we have sufficient context.
        """
        # If there's been back-and-forth, we likely have enough
        user_messages = [m for m in conversation.messages if m.role == "user"]
        return len(user_messages) >= 2

    def _gather_clarifications(
        self,
        message: str,
        conversation: Conversation,
        summaries: List[Dict[str, Any]],
    ) -> str:
        """Gather clarifying questions for the user.

        Args:
            message: The user's message.
            conversation: The conversation context.
            summaries: Available constellation summaries.

        Returns:
            Clarification questions.
        """
        # Find similar constellation if any
        similar = self._find_similar_constellation(message, summaries)

        if similar:
            analyze_constellation(similar["id"], self.foundry)
            return (
                f"I found a similar capability ({similar['name']}), but I need "
                f"a bit more context to help you.\n\n"
                f"Could you tell me:\n"
                f"1. What specific outcome are you looking for?\n"
                f"2. Any constraints or preferences I should know about?\n"
            )

        return (
            "I'd like to help with this. To make sure I give you the best result:\n\n"
            "1. What specific outcome are you looking for?\n"
            "2. What scope or constraints should I consider?\n"
            "3. Any specific format you'd prefer for the output?"
        )

    def _find_similar_constellation(
        self, message: str, summaries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find a constellation similar to the query.

        Args:
            message: The user's message.
            summaries: Available constellation summaries.

        Returns:
            Similar constellation summary or None.
        """
        # Simple keyword matching for similarity
        message_words = set(message.lower().split())

        best_match = None
        best_score = 0

        for summary in summaries:
            desc_words = set(summary.get("description", "").lower().split())
            overlap = len(message_words & desc_words)
            if overlap > best_score:
                best_score = overlap
                best_match = summary

        return best_match if best_score >= 1 else None

    async def _invoke_constellation(
        self,
        constellation_id: str,
        variables: Dict[str, Any],
        original_query: str,
        stream: Optional["ExecutionStream"] = None,
    ) -> Dict[str, Optional[str]]:
        """Invoke a constellation with the given variables.

        Args:
            constellation_id: The constellation to invoke.
            variables: The extracted variables.
            original_query: The original user query.
            stream: Optional execution stream for real-time events.

        Returns:
            Dict with 'output' and 'run_id'.
        """
        from astro_backend_service.executor import ConstellationRunner

        runner = ConstellationRunner(self.foundry)

        try:
            run = await runner.run(
                constellation_id,
                variables,
                original_query,
                stream=stream,
            )

            # Apply synthesis if needed
            output = run.final_output or ""
            constellation = self.foundry.get_constellation(constellation_id)

            if SynthesisAgent.should_run(self.user_preferences, constellation):
                agent = SynthesisAgent(self.user_preferences, self.llm_client)
                output = agent.format_output(output)

            return {
                "output": output,
                "run_id": run.id,
            }
        except Exception as e:
            return {
                "output": f"Error executing constellation: {e}",
                "run_id": None,
            }

    async def _invoke_generic_constellation(
        self,
        message: str,
        conversation: Conversation,
        stream: Optional["ExecutionStream"] = None,
    ) -> Dict[str, Optional[str]]:
        """Invoke the generic constellation for unmatched queries.

        Args:
            message: The user's message.
            conversation: The conversation context.
            stream: Optional execution stream for real-time events.

        Returns:
            Dict with 'output' and 'run_id'.
        """
        from astro_backend_service.launchpad.generic_constellation import (
            get_or_create_generic_constellation,
        )

        # Get or create the generic constellation
        get_or_create_generic_constellation(self.foundry)

        # Build rich context
        clarifications = [
            m.content for m in conversation.messages if m.role == "assistant"
        ][-3:]

        context = {
            "original_query": message,
            "clarifications": clarifications,
            "conversation_length": len(conversation.messages),
        }

        # WAITING ON FULL IMPLEMENTATION
        # For now, return stub
        return {
            "output": f"[Generic constellation would handle: {message}]\n\nContext: {context}",
            "run_id": None,
        }
