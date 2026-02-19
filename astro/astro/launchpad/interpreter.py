"""Interpreter for zero-shot directive selection.

The Interpreter is Step 1 of the zero-shot pipeline. It selects which
directives are relevant for a given query by analyzing the query intent
and matching it against available directive descriptions.
"""

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from astro.core.llm.utils import get_default_max_tokens
from astro.launchpad.conversation import Conversation

logger = logging.getLogger(__name__)


class DirectiveSummary(BaseModel):
    """Lightweight directive info for selection."""

    id: str = Field(..., description="Directive ID")
    name: str = Field(..., description="Directive name")
    description: str = Field(..., description="What this directive does")
    probe_ids: list[str] = Field(default_factory=list, description="Required probe IDs")
    tags: list[str] = Field(default_factory=list, description="Directive tags")


class InterpretationResult(BaseModel):
    """Result of interpreter evaluation.

    The interpreter can now take three actions:
    - ask_user: Query is ambiguous, need clarification
    - select_directives: Ready to select directives (existing behavior)
    - generate_directive: No matching directive found, should create one
    """

    action: Literal["ask_user", "select_directives", "generate_directive"] = Field(
        ..., description="The action to take based on query analysis"
    )

    # For select_directives (now optional with defaults)
    directive_ids: list[str] = Field(
        default_factory=list, description="Selected directive IDs"
    )
    context_queries: list[str] = Field(
        default_factory=list, description="Queries for Second Brain retrieval"
    )
    reasoning: str = Field(default="", description="Explanation of the decision")
    confidence: float = Field(default=1.0, description="Decision confidence 0-1")

    # For ask_user (new)
    questions: list[str] = Field(
        default_factory=list,
        description="Clarification questions to ask the user (for ask_user action)",
    )


INTERPRETER_SYSTEM_PROMPT = """You are a directive selection agent. Your job is to analyze user queries and decide how to proceed: ask clarifying questions, select directives, or trigger directive generation.

## Your Task

Given:
1. A user query
2. Conversation history (optional)
3. A list of available directives

You must choose ONE of three actions:
1. **ask_user**: Query is ambiguous or lacks necessary context
2. **select_directives**: Ready to select 1-3 relevant directives
3. **generate_directive**: No matching directive exists for this query

## Clarification Strategy

**When to ASK for clarification (action: "ask_user"):**
- Query mentions entities without specifying which one (e.g., "analyze the company" - which company?)
- Query has multiple possible interpretations (e.g., "research Tesla" - financial, technical, news, all of it?)
- Query lacks necessary context that's NOT in conversation history
- Missing key parameters (time ranges, comparison criteria, specific metrics)

**When to SELECT directives (action: "select_directives"):**
- Query is clear and specific
- Necessary context is available in conversation history
- Query maps to available directives
- You have enough information to proceed

**When to GENERATE directive (action: "generate_directive"):**
- No existing directives match the query intent
- Query requires tools/capabilities not available in existing directives
- User explicitly asks for new functionality

**Important**: Check conversation history BEFORE asking for clarification. The user may have already provided the context in earlier messages.

## Directive Selection Strategy

**When to select multiple directives:**
- Query requires multiple perspectives (e.g., "analyze pros and cons")
- Query spans multiple domains (e.g., "technical and financial analysis")
- Query needs synthesis of different information sources

**When to select single directive:**
- Query is focused on a single task
- Query maps directly to one directive's purpose
- Additional directives would add noise

**When to select zero directives:**
- Query is purely conversational (greetings, small talk)
- Query is about system capabilities (meta-questions)
- Query requires no specialized instructions

## Context Queries

Generate 1-3 specific queries for Second Brain memory retrieval:
- Extract key entities (company names, tickers, dates)
- Identify core concepts to retrieve
- Keep queries focused and specific

## Output Format

Respond with valid JSON matching ONE of these patterns:

**For ask_user:**
{
  "action": "ask_user",
  "questions": ["Which company would you like to analyze?", "What time period are you interested in?"],
  "reasoning": "Query mentions 'the company' but doesn't specify which one",
  "confidence": 0.3
}

**For select_directives:**
{
  "action": "select_directives",
  "directive_ids": ["directive_id_1", "directive_id_2"],
  "context_queries": ["query for memory", "another query"],
  "reasoning": "Explanation of why these directives were chosen",
  "confidence": 0.9
}

**For generate_directive:**
{
  "action": "generate_directive",
  "reasoning": "No existing directives support blockchain analysis",
  "confidence": 0.8
}

## Examples

### Example 1: Ask for clarification (ambiguous entity)
Query: "Analyze the company's financial performance"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics

Response:
{
  "action": "ask_user",
  "questions": ["Which company would you like to analyze?"],
  "reasoning": "Query mentions 'the company' without specifying which one. Need to know the target company before selecting directives.",
  "confidence": 0.3
}

### Example 2: Select directives (clear query)
Query: "What are the latest headlines for Apple?"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text

Response:
{
  "action": "select_directives",
  "directive_ids": ["ns_001"],
  "context_queries": ["Apple news", "Apple headlines"],
  "reasoning": "User wants recent news for Apple. The news_search directive handles news retrieval. Financial analysis and sentiment are not needed for this straightforward request.",
  "confidence": 0.95
}

### Example 3: Multiple directives
Query: "Compare Apple and Microsoft's financial performance and market sentiment"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text

Response:
{
  "action": "select_directives",
  "directive_ids": ["fa_001", "sa_001"],
  "context_queries": ["Apple financial performance", "Microsoft financial performance", "Apple Microsoft market sentiment"],
  "reasoning": "Query requires both financial analysis (metrics, performance) and sentiment analysis (market perception). News search alone won't provide the analytical depth needed. Need both perspectives for comprehensive comparison.",
  "confidence": 0.9
}

### Example 4: Conversational query (no directives needed)
Query: "Hello! How are you?"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics

Response:
{
  "action": "select_directives",
  "directive_ids": [],
  "context_queries": [],
  "reasoning": "This is a greeting/conversational query that doesn't require any specialized directives. Can respond directly without tool support.",
  "confidence": 1.0
}

### Example 5: Multiple directives for comprehensive analysis
Query: "Research Tesla: financial health, recent news, and market sentiment"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text

Response:
{
  "action": "select_directives",
  "directive_ids": ["ns_001", "fa_001", "sa_001"],
  "context_queries": ["Tesla financial metrics", "Tesla recent news", "Tesla market sentiment"],
  "reasoning": "Query explicitly requests three dimensions: financial health, recent news, and market sentiment. Each maps to a specific directive. All three are needed for complete research.",
  "confidence": 0.95
}

### Example 6: Ask for clarification (vague scope)
Query: "Analyze Tesla"
Conversation history:
User: "I'm researching EV companies"
Assistant: "I can help with that. Which aspects would you like to explore?"
User: "Analyze Tesla"

Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text
- technical_analysis (id: ta_001): Analyze stock price patterns

Response:
{
  "action": "ask_user",
  "questions": ["What aspects of Tesla would you like me to analyze? (e.g., financial performance, recent news, stock technical analysis, market sentiment)"],
  "reasoning": "Query is too vague. 'Analyze' could mean financial, technical, sentiment, or news analysis. Need to narrow scope before selecting directives.",
  "confidence": 0.4
}

### Example 7: Context from history allows selection
Query: "What's the latest news?"
Conversation history:
User: "I want to track Apple stock"
Assistant: "I can help with that. What would you like to know?"
User: "What's the latest news?"

Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics

Response:
{
  "action": "select_directives",
  "directive_ids": ["ns_001"],
  "context_queries": ["Apple news", "Apple latest headlines"],
  "reasoning": "Query asks for 'latest news' which is vague, but conversation history establishes the context is Apple. Can proceed with news_search directive targeting Apple.",
  "confidence": 0.85
}

### Example 8: Generate new directive
Query: "Analyze on-chain metrics for Bitcoin"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics

Response:
{
  "action": "generate_directive",
  "reasoning": "No existing directives support blockchain/crypto on-chain analysis. Would need specialized tools for blockchain data (active addresses, transaction volume, hash rate, etc.). Should generate a new directive for crypto on-chain analysis.",
  "confidence": 0.8
}

## Important Guidelines

1. **Check conversation history FIRST**: Don't ask for context that was already provided earlier
2. **Ask when truly ambiguous**: If the query lacks critical information not in history, ask
3. **Be conservative with directives**: When in doubt, select fewer directives
4. **Consider overlap**: Don't select directives with redundant capabilities
5. **Match intent**: Select directives whose descriptions match query intent
6. **Generate specific context queries**: Extract entities and concepts from the query
7. **Explain reasoning**: Make it clear why you chose this action
8. **Set confidence appropriately**: Lower confidence for ambiguous queries or clarification needs
9. **Suggest generation sparingly**: Only when truly no existing directive fits
"""


class Interpreter:
    """Step 1 of zero-shot pipeline: select relevant directives.

    The Interpreter uses a lightweight LLM to analyze the query and select
    which directives should be used to answer it. This enables dynamic
    tool scoping without predefined workflows.
    """

    def __init__(self, registry: Any, llm_provider: Any):
        """Initialize the Interpreter.

        Args:
            registry: Registry for retrieving directives.
            llm_provider: LLM provider (should use lightweight model like Haiku).
        """
        self.registry = registry
        self.llm = llm_provider

    async def evaluate(
        self,
        conversation: Conversation,
        available_directives: list[DirectiveSummary] | None = None,
    ) -> InterpretationResult:
        """Evaluate query and decide action: ask_user, select_directives, or generate_directive.

        Args:
            conversation: Current conversation with user query.
            available_directives: Optional list of directive summaries.
                If None, will retrieve all from registry.

        Returns:
            InterpretationResult with action and relevant fields.
        """
        # Get the current query (last user message)
        user_messages = [m for m in conversation.messages if m.role == "user"]
        if not user_messages:
            return InterpretationResult(
                action="select_directives",
                directive_ids=[],
                context_queries=[],
                reasoning="No user query found",
                confidence=0.0,
            )

        current_query = user_messages[-1].content

        # Get available directives if not provided
        if available_directives is None:
            available_directives = await self._get_available_directives()

        logger.info(
            f"Interpreter: Retrieved {len(available_directives)} available directives"
        )

        # Build the user prompt with directive list
        directives_text = self._format_directives(available_directives)
        logger.info(
            f"Interpreter: Formatted directives text length: {len(directives_text)} chars"
        )

        # Build conversation context (last 5 messages)
        context_text = self._build_context(conversation)

        user_prompt = f"""Query: {current_query}

Conversation context:
{context_text if context_text else "(New conversation)"}

Available directives:
{directives_text}

Analyze the query and decide on the appropriate action."""

        # Check if we need to force a decision (max rounds reached)
        system_prompt = INTERPRETER_SYSTEM_PROMPT
        if conversation.should_force_decision():
            system_prompt += """

## CRITICAL: FORCE DECISION MODE

You have reached the maximum number of clarification rounds. You MUST now choose either:
- "select_directives" (even if context is imperfect, make your best guess)
- "generate_directive" (if truly no existing directive fits)

You CANNOT choose "ask_user" anymore. Make a decision with the information you have."""

        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.llm.ainvoke(
                messages, temperature=0.3, max_tokens=get_default_max_tokens()
            )
            content = (
                response.content
                if hasattr(response, "content")
                else str(response).strip()
            )

            logger.info(f"Interpreter: LLM response length: {len(content)} chars")
            logger.info(f"Interpreter: LLM response preview: {content[:200]}...")

            # Parse JSON response
            result = self._parse_response(content)
            logger.info(
                f"Interpreter: Selected {len(result.directive_ids)} directives: {result.directive_ids}"
            )
            logger.info(f"Interpreter: Reasoning: {result.reasoning}")
            return result

        except Exception as e:
            # Fallback: return empty selection
            return InterpretationResult(
                action="select_directives",
                directive_ids=[],
                context_queries=[current_query],
                reasoning=f"Error during selection: {str(e)}",
                confidence=0.0,
            )

    async def select_directives(
        self,
        conversation: Conversation,
        available_directives: list[DirectiveSummary] | None = None,
    ) -> InterpretationResult:
        """Backward compatibility alias for evaluate().

        Deprecated: Use evaluate() instead.

        Args:
            conversation: Current conversation with user query.
            available_directives: Optional list of directive summaries.

        Returns:
            InterpretationResult with action and relevant fields.
        """
        return await self.evaluate(conversation, available_directives)

    def should_offer_directive_generation(self, result: InterpretationResult) -> bool:
        """Determine if we should offer to generate a new directive.

        Offers generation when:
        - No directives were selected
        - Confidence is low (< 0.5)
        - Query is NOT purely conversational

        Args:
            result: InterpretationResult from selection

        Returns:
            True if we should offer directive generation
        """
        # Don't offer for purely conversational queries
        conversational_keywords = [
            "hello",
            "hi",
            "hey",
            "thanks",
            "thank you",
            "goodbye",
            "bye",
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "how's it going",
        ]
        query_lower = (
            result.context_queries[0].lower() if result.context_queries else ""
        )
        if any(kw in query_lower for kw in conversational_keywords):
            return False

        # Don't offer for identity/meta-questions
        identity_patterns = [
            "what can you",
            "how do i",
            "what is your name",
            "what's your name",
            "who are you",
            "what are you",
            "tell me about yourself",
            "introduce yourself",
            "what do you do",
            "what are you capable",
            "can you help me",
            "are you",
        ]
        if any(pattern in query_lower for pattern in identity_patterns):
            return False

        # Offer if no directives found and query seems substantive
        if not result.directive_ids and len(query_lower.split()) > 3:
            return True

        # Offer if confidence is very low
        if result.confidence < 0.3:
            return True

        return False

    async def _get_available_directives(self) -> list[DirectiveSummary]:
        """Retrieve all available directives from registry.

        Returns:
            List of DirectiveSummary objects.
        """
        try:
            # Get all directives from registry (synchronous call)
            directives = self.registry.list_directives()
            logger.info(f"Interpreter: Registry returned {len(directives)} directives")

            summaries = []
            for directive in directives:
                # Skip hidden or internal directives
                if directive.metadata and directive.metadata.get("hidden"):
                    continue

                summaries.append(
                    DirectiveSummary(
                        id=directive.id,
                        name=directive.name,
                        description=directive.description,
                        probe_ids=directive.probe_ids or [],
                        tags=(
                            directive.metadata.get("tags", [])
                            if directive.metadata
                            else []
                        ),
                    )
                )

            return summaries

        except Exception as e:
            logger.error(
                f"Interpreter: Error retrieving available directives: {str(e)}",
                exc_info=True,
            )
            return []

    def _format_directives(self, directives: list[DirectiveSummary]) -> str:
        """Format directives for prompt.

        Args:
            directives: List of directive summaries.

        Returns:
            Formatted string for prompt.
        """
        if not directives:
            return "(No directives available)"

        lines = []
        for i, d in enumerate(directives, 1):
            tags_str = f" [tags: {', '.join(d.tags)}]" if d.tags else ""
            tools_str = f" [tools: {len(d.probe_ids)}]" if d.probe_ids else ""
            lines.append(f"{i}. {d.name} (id: {d.id}){tags_str}{tools_str}")
            lines.append(f"   Description: {d.description}")
            lines.append("")

        return "\n".join(lines)

    def _build_context(self, conversation: Conversation) -> str:
        """Build conversation context string.

        Args:
            conversation: Current conversation.

        Returns:
            Formatted context string.
        """
        recent_messages = conversation.get_context_messages(limit=10)
        if not recent_messages:
            return ""

        lines = []
        for msg in recent_messages[:-1]:  # Exclude last message (current query)
            if msg.role == "user":
                lines.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                lines.append(f"Assistant: {msg.content}")

        return "\n".join(lines)

    def _parse_response(self, content: str) -> InterpretationResult:
        """Parse LLM response into InterpretationResult.

        Args:
            content: LLM response content.

        Returns:
            Parsed InterpretationResult.
        """
        # Handle markdown code blocks
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

        # Parse JSON
        try:
            data = json.loads(content)

            # Extract action (required field)
            action = data.get("action")
            if action not in ["ask_user", "select_directives", "generate_directive"]:
                # Fallback: if no valid action, default to select_directives
                logger.warning(
                    f"Invalid or missing action '{action}', defaulting to 'select_directives'"
                )
                action = "select_directives"

            return InterpretationResult(
                action=action,
                directive_ids=data.get("directive_ids", []),
                context_queries=data.get("context_queries", []),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 1.0),
                questions=data.get("questions", []),
            )
        except json.JSONDecodeError:
            # Fallback: select_directives with empty list
            return InterpretationResult(
                action="select_directives",
                directive_ids=[],
                context_queries=[],
                reasoning=f"Failed to parse response: {content[:100]}",
                confidence=0.0,
            )
