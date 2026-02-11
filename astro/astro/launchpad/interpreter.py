"""Interpreter for zero-shot directive selection.

The Interpreter is Step 1 of the zero-shot pipeline. It selects which
directives are relevant for a given query by analyzing the query intent
and matching it against available directive descriptions.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from astro.launchpad.conversation import Conversation

logger = logging.getLogger(__name__)


class DirectiveSummary(BaseModel):
    """Lightweight directive info for selection."""

    id: str = Field(..., description="Directive ID")
    name: str = Field(..., description="Directive name")
    description: str = Field(..., description="What this directive does")
    probe_ids: List[str] = Field(
        default_factory=list, description="Required probe IDs"
    )
    tags: List[str] = Field(default_factory=list, description="Directive tags")


class InterpretationResult(BaseModel):
    """Result of directive selection."""

    directive_ids: List[str] = Field(..., description="Selected directive IDs")
    context_queries: List[str] = Field(
        ..., description="Queries for Second Brain retrieval"
    )
    reasoning: str = Field(..., description="Why these directives were selected")
    confidence: float = Field(default=1.0, description="Selection confidence 0-1")


INTERPRETER_SYSTEM_PROMPT = """You are a directive selection agent. Your job is to analyze user queries and select the most relevant directives (prompt modules) to help answer them.

## Your Task

Given:
1. A user query
2. Conversation history (optional)
3. A list of available directives

You must:
1. Understand the query intent
2. Select 1-3 relevant directives that will help answer the query
3. Generate context queries for memory retrieval
4. Explain your reasoning

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

Respond with valid JSON:
{
  "directive_ids": ["directive_id_1", "directive_id_2"],
  "context_queries": ["query for memory", "another query"],
  "reasoning": "Explanation of why these directives were chosen",
  "confidence": 0.9
}

## Examples

### Example 1: Single directive
Query: "What are the latest headlines for Apple?"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text

Response:
{
  "directive_ids": ["ns_001"],
  "context_queries": ["Apple news", "Apple headlines"],
  "reasoning": "User wants recent news. The news_search directive handles news retrieval. Financial analysis and sentiment are not needed for this straightforward request.",
  "confidence": 0.95
}

### Example 2: Multiple directives
Query: "Compare Apple and Microsoft's financial performance and market sentiment"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text

Response:
{
  "directive_ids": ["fa_001", "sa_001"],
  "context_queries": ["Apple financial performance", "Microsoft financial performance", "Apple Microsoft market sentiment"],
  "reasoning": "Query requires both financial analysis (metrics, performance) and sentiment analysis (market perception). News search alone won't provide the analytical depth needed. Need both perspectives for comprehensive comparison.",
  "confidence": 0.9
}

### Example 3: Conversational query
Query: "Hello! How are you?"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics

Response:
{
  "directive_ids": [],
  "context_queries": [],
  "reasoning": "This is a greeting/conversational query that doesn't require any specialized directives. Can respond directly without tool support.",
  "confidence": 1.0
}

### Example 4: Multiple directives for comprehensive analysis
Query: "Research Tesla: financial health, recent news, and market sentiment"
Available directives:
- news_search (id: ns_001): Search for recent news articles
- financial_analysis (id: fa_001): Analyze financial metrics
- sentiment_analysis (id: sa_001): Analyze sentiment from text

Response:
{
  "directive_ids": ["ns_001", "fa_001", "sa_001"],
  "context_queries": ["Tesla financial metrics", "Tesla recent news", "Tesla market sentiment"],
  "reasoning": "Query explicitly requests three dimensions: financial health, recent news, and market sentiment. Each maps to a specific directive. All three are needed for complete research.",
  "confidence": 0.95
}

## Important Guidelines

1. **Be conservative**: When in doubt, select fewer directives
2. **Consider overlap**: Don't select directives with redundant capabilities
3. **Match intent**: Select directives whose descriptions match query intent
4. **Generate specific context queries**: Extract entities and concepts from the query
5. **Explain reasoning**: Make it clear why each directive was (or wasn't) selected
6. **Set confidence appropriately**: Lower confidence for ambiguous queries
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

    async def select_directives(
        self,
        conversation: Conversation,
        available_directives: Optional[List[DirectiveSummary]] = None,
    ) -> InterpretationResult:
        """Select which directives are needed for this query.

        Args:
            conversation: Current conversation with user query.
            available_directives: Optional list of directive summaries.
                If None, will retrieve all from registry.

        Returns:
            InterpretationResult with selected directives and context queries.
        """
        # Get the current query (last user message)
        user_messages = [m for m in conversation.messages if m.role == "user"]
        if not user_messages:
            return InterpretationResult(
                directive_ids=[],
                context_queries=[],
                reasoning="No user query found",
                confidence=0.0,
            )

        current_query = user_messages[-1].content

        # Get available directives if not provided
        if available_directives is None:
            available_directives = await self._get_available_directives()

        logger.info(f"Interpreter: Retrieved {len(available_directives)} available directives")

        # Build the user prompt with directive list
        directives_text = self._format_directives(available_directives)
        logger.info(f"Interpreter: Formatted directives text length: {len(directives_text)} chars")

        # Build conversation context (last 5 messages)
        context_text = self._build_context(conversation)

        user_prompt = f"""Query: {current_query}

Conversation context:
{context_text if context_text else "(New conversation)"}

Available directives:
{directives_text}

Select the most relevant directives for this query."""

        # Call LLM
        messages = [
            {"role": "system", "content": INTERPRETER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.llm.ainvoke(messages, temperature=0.3, max_tokens=1000)
            content = response.content if hasattr(response, "content") else str(response).strip()

            logger.info(f"Interpreter: LLM response length: {len(content)} chars")
            logger.info(f"Interpreter: LLM response preview: {content[:200]}...")

            # Parse JSON response
            result = self._parse_response(content)
            logger.info(f"Interpreter: Selected {len(result.directive_ids)} directives: {result.directive_ids}")
            logger.info(f"Interpreter: Reasoning: {result.reasoning}")
            return result

        except Exception as e:
            # Fallback: return empty selection
            return InterpretationResult(
                directive_ids=[],
                context_queries=[current_query],
                reasoning=f"Error during selection: {str(e)}",
                confidence=0.0,
            )

    def should_offer_directive_generation(
        self, result: InterpretationResult
    ) -> bool:
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
        ]
        query_lower = result.context_queries[0].lower() if result.context_queries else ""
        if any(kw in query_lower for kw in conversational_keywords):
            return False

        # Don't offer for meta-questions about system capabilities
        if "what can you" in query_lower or "how do i" in query_lower:
            return False

        # Offer if no directives found and query seems substantive
        if not result.directive_ids and len(query_lower.split()) > 3:
            return True

        # Offer if confidence is very low
        if result.confidence < 0.3:
            return True

        return False

    async def _get_available_directives(self) -> List[DirectiveSummary]:
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
                        tags=directive.metadata.get("tags", [])
                        if directive.metadata
                        else [],
                    )
                )

            return summaries

        except Exception as e:
            logger.error(f"Interpreter: Error retrieving available directives: {str(e)}", exc_info=True)
            return []

    def _format_directives(self, directives: List[DirectiveSummary]) -> str:
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
        recent_messages = conversation.get_context_messages(limit=5)
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

            return InterpretationResult(
                directive_ids=data.get("directive_ids", []),
                context_queries=data.get("context_queries", []),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 1.0),
            )
        except json.JSONDecodeError:
            # Fallback: empty selection
            return InterpretationResult(
                directive_ids=[],
                context_queries=[],
                reasoning=f"Failed to parse response: {content[:100]}",
                confidence=0.0,
            )
