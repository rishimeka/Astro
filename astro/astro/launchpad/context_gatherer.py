"""ContextGatherer: Intelligently gathers requirements for directive generation.

When no matching directive exists, the ContextGatherer acts as a requirements analyst.
It:
1. Analyzes the query to determine what can be inferred
2. Identifies what information is missing
3. Asks targeted clarifying questions (only what's needed)
4. Compiles gathered context for DirectiveGenerator

The goal is to gather enough context to create a high-quality directive while
minimizing user friction.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from astro.core.llm.utils import get_default_max_tokens
from astro.launchpad.conversation import Conversation
from astro.launchpad.directive_generator import GatheredContext

logger = logging.getLogger(__name__)


@dataclass
class InferredContext:
    """What can be inferred from the query without asking."""

    role_expertise: str | None = None
    approach_steps: list[str] = field(default_factory=list)
    output_format: str | None = None
    constraints: list[str] = field(default_factory=list)
    tone_style: str | None = None
    confidence: float = 0.0  # 0.0-1.0


@dataclass
class Question:
    """A clarifying question to ask the user."""

    question_id: str
    question_text: str
    purpose: str  # What we're gathering (role, output_format, etc.)
    required: bool = True


class ContextGatherer:
    """Gathers requirements for directive generation."""

    def __init__(self, llm: Any):
        """Initialize ContextGatherer.

        Args:
            llm: LLM for analyzing queries (lightweight model like Haiku is fine)
        """
        self.llm = llm

    async def gather_context(
        self, query: str, conversation: Conversation
    ) -> GatheredContext:
        """Gather context through intelligent questioning.

        Args:
            query: User's original query
            conversation: Current conversation

        Returns:
            GatheredContext ready for DirectiveGenerator
        """
        logger.info("ContextGatherer: Starting context gathering")

        # Step 1: Analyze query to infer what we can
        inferred = await self._analyze_query(query, conversation)
        logger.info(
            f"ContextGatherer: Inferred context with confidence {inferred.confidence:.2f}"
        )

        # Step 2: Generate questions for missing information
        questions = self._generate_questions(inferred, query)
        logger.info(f"ContextGatherer: Generated {len(questions)} questions")

        # Step 3: Collect answers from user
        # NOTE: This is a placeholder - actual implementation needs UI/API integration
        # For now, return what we inferred
        answers: dict[str, Any] = {}  # Would be populated from user responses

        # Step 4: Compile into GatheredContext
        context = GatheredContext(
            query=query,
            conversation_history=self._get_history(conversation),
            role_expertise=inferred.role_expertise,
            approach_steps=inferred.approach_steps,
            output_format=inferred.output_format,
            constraints=inferred.constraints,
            tone_style=inferred.tone_style,
            user_answers=answers,
        )

        return context

    async def _analyze_query(
        self, query: str, conversation: Conversation
    ) -> InferredContext:
        """Analyze query to infer context without asking.

        Args:
            query: User's query
            conversation: Conversation history

        Returns:
            InferredContext with what we can determine
        """
        # Build conversation context
        history_text = self._format_history(conversation)

        prompt = f"""You are analyzing a user query to determine what context you can infer for creating an AI directive.

## User Query
{query}

## Conversation History
{history_text if history_text else 'No prior history'}

## Your Task
Analyze the query and determine what you can confidently infer about:

1. **Role/Expertise Needed**: What domain expert should handle this? (e.g., "financial analyst", "market researcher", "data scientist")
2. **Approach Steps**: What are the logical steps to complete this task?
3. **Output Format**: What format is implied? (JSON, markdown report, bullet points, table, etc.)
4. **Constraints**: Any boundaries or limitations mentioned or implied?
5. **Tone/Style**: Professional? Technical? Executive summary? Casual?

**Examples:**
- Query: "Analyze Tesla's Q3 earnings"
  - Role: Financial analyst (HIGH confidence)
  - Approach: [Get earnings data, analyze revenue/profit, compare to prior quarters] (HIGH confidence)
  - Output: Structured report with key metrics (MEDIUM confidence)
  - Need to ask: Specific format (JSON vs markdown), any constraints

- Query: "Help me with this file"
  - Role: Unknown (LOW confidence)
  - Approach: Unknown (LOW confidence)
  - Output: Unknown (LOW confidence)
  - Need to ask: What kind of file? What help? What outcome?

Return JSON:
{{
  "role_expertise": "string or null",
  "approach_steps": ["step1", "step2"],
  "output_format": "string or null",
  "constraints": ["constraint1", "constraint2"],
  "tone_style": "string or null",
  "confidence": 0.0-1.0
}}

**Important:**
- Only include things you're CONFIDENT about
- If you're not sure, leave it null/empty
- Confidence is overall confidence in your inferences (0.0 = no clue, 1.0 = very clear)
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.ainvoke(
                messages, temperature=0.3, max_tokens=get_default_max_tokens()
            )
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse JSON response
            import json

            # Extract JSON from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)

            return InferredContext(
                role_expertise=result.get("role_expertise"),
                approach_steps=result.get("approach_steps", []),
                output_format=result.get("output_format"),
                constraints=result.get("constraints", []),
                tone_style=result.get("tone_style"),
                confidence=result.get("confidence", 0.0),
            )

        except Exception as e:
            logger.error(f"ContextGatherer: Error analyzing query: {str(e)}")
            # Return empty inferred context
            return InferredContext(confidence=0.0)

    def _generate_questions(
        self, inferred: InferredContext, query: str
    ) -> list[Question]:
        """Generate clarifying questions for missing information.

        Args:
            inferred: What we already know
            query: Original query

        Returns:
            List of Question objects
        """
        questions = []

        # Ask about role if not inferred with confidence
        if not inferred.role_expertise:
            questions.append(
                Question(
                    question_id="role",
                    question_text=f"To build the right workflow for '{query}', what type of expert should handle this? (e.g., financial analyst, market researcher, data scientist)",
                    purpose="role_expertise",
                    required=True,
                )
            )

        # Ask about output format if not clear
        if not inferred.output_format:
            questions.append(
                Question(
                    question_id="output_format",
                    question_text="What format should the output be in? (e.g., JSON data, markdown report, bullet points, structured table)",
                    purpose="output_format",
                    required=True,
                )
            )

        # Ask about constraints if none inferred
        if not inferred.constraints:
            questions.append(
                Question(
                    question_id="constraints",
                    question_text="Are there any constraints or boundaries I should know about? (e.g., data sources, time range, specific requirements)",
                    purpose="constraints",
                    required=False,
                )
            )

        # Ask about approach if very unclear (low confidence)
        if not inferred.approach_steps and inferred.confidence < 0.4:
            questions.append(
                Question(
                    question_id="approach",
                    question_text="Can you describe the steps or approach you'd like me to take for this task?",
                    purpose="approach_steps",
                    required=True,
                )
            )

        return questions

    def _get_history(self, conversation: Conversation) -> list[dict[str, str]]:
        """Extract conversation history as list of message dicts.

        Args:
            conversation: Conversation object

        Returns:
            List of {role, content} dicts
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.get_context_messages(limit=10)
        ]

    def _format_history(self, conversation: Conversation) -> str:
        """Format conversation history for prompt.

        Args:
            conversation: Conversation object

        Returns:
            Formatted string
        """
        messages = conversation.get_context_messages(limit=5)
        if not messages:
            return ""

        lines = []
        for msg in messages:
            role = msg.role.upper()
            lines.append(f"{role}: {msg.content}")

        return "\n".join(lines)

    def format_gathering_message(self, questions: list[Question]) -> str:
        """Format the initial message when starting context gathering.

        Args:
            questions: Questions we'll be asking

        Returns:
            Message to send to user
        """
        intro = "I don't have a specialized workflow for this yet. Let me ask a few questions so I can build one for you."

        if len(questions) == 0:
            return intro + " Actually, I think I have enough context to proceed!"

        question_preview = "\n".join(
            [f"{i+1}. {q.purpose}" for i, q in enumerate(questions)]
        )

        return f"""{intro}

I'll need to understand:
{question_preview}

This will help me create a custom directive that handles queries like this in the future.
"""

    def format_question(self, question: Question, index: int, total: int) -> str:
        """Format a single question for display.

        Args:
            question: Question to format
            index: Current question number (0-indexed)
            total: Total number of questions

        Returns:
            Formatted question string
        """
        progress = f"Question {index + 1} of {total}"
        required = (
            " (required)" if question.required else " (optional - press Enter to skip)"
        )

        return f"""**{progress}** — {question.purpose}{required}

{question.question_text}"""
