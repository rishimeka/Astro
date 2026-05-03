"""DirectiveGenerator: Creates directives on-the-fly when no match exists.

When the Interpreter finds no matching directive, it gathers context from the user
and passes it to the DirectiveGenerator. The generator:
1. Reads all available probes from ProbeRegistry
2. Selects relevant probes for the task using LLM
3. Generates expert-level directive content with @probe: references
4. Checks semantic similarity to avoid duplicates
5. Presents preview for human approval
6. Saves to Registry if approved

The generated directive follows this structure:
- Role: Domain expertise and perspective
- Approach: Step-by-step reasoning with @probe: references embedded
- Output Format: Concrete structure (JSON, markdown, etc.)
- Constraints: Hard boundaries
- Tone/Style: If relevant to use case
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from astro.core.llm.utils import get_default_max_tokens
from astro.core.models.directive import Directive
from astro.core.probes.registry import ProbeRegistry
from astro.core.registry.registry import Registry

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Any:
    """Extract and parse JSON from LLM output, handling code blocks and malformed output.

    Tries multiple strategies:
    1. Direct parse
    2. Extract from markdown code blocks
    3. Find first { or [ and match to closing bracket
    """
    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*([\[{].*?[\]}])\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find outermost JSON object or array
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find matching closing bracket by counting nesting
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break

    raise json.JSONDecodeError("Could not extract valid JSON from LLM output", text, 0)


def _truncate_description(description: str, max_length: int = 150) -> str:
    """Truncate a probe description to avoid bloating prompts."""
    if len(description) <= max_length:
        return description
    # Try to cut at first sentence
    dot_pos = description.find('. ')
    if 0 < dot_pos <= max_length:
        return description[:dot_pos + 1]
    # Otherwise truncate on word boundary
    truncated = description[:max_length].rsplit(' ', 1)[0]
    return truncated + "..."


@dataclass
class GatheredContext:
    """Context gathered from user for directive generation."""

    query: str
    conversation_history: list[dict[str, str]]
    role_expertise: str | None = None
    approach_steps: list[str] | None = None
    output_format: str | None = None
    constraints: list[str] | None = None
    tone_style: str | None = None
    user_answers: dict[str, str] | None = None


@dataclass
class GeneratedDirective:
    """Result of directive generation."""

    name: str
    description: str
    content: str  # Contains @probe: references
    probe_ids: list[str]  # Extracted from @probe: references (Registry does this)
    metadata: dict[str, Any]
    has_tools: bool = False
    similarity_score: float = 0.0
    similar_directive_id: str | None = None


class DirectiveGenerator:
    """Generates directives on-the-fly with human approval."""

    def __init__(
        self,
        directive_registry: Registry,
        probe_registry: type[ProbeRegistry],
        llm: Any,  # LangChain chat model
    ):
        """Initialize DirectiveGenerator.

        Args:
            directive_registry: Registry for saving directives
            probe_registry: ProbeRegistry class (class-level singleton)
            llm: LLM for generation (should be powerful model like Sonnet)
        """
        self.directive_registry = directive_registry
        self.probe_registry = probe_registry
        self.llm = llm

    async def generate_directive(self, context: GatheredContext) -> GeneratedDirective:
        """Generate a new directive from gathered context.

        Args:
            context: User query and gathered requirements

        Returns:
            GeneratedDirective with content and metadata
        """
        logger.info("DirectiveGenerator: Starting directive generation")

        # Step 1: Read all available probes
        available_probes = self._read_available_probes()
        logger.info(
            f"DirectiveGenerator: Found {len(available_probes)} available probes: "
            f"{[p['id'] for p in available_probes]}"
        )

        # Step 2: Select relevant probes for this task
        selected_probes = await self._select_relevant_probes(context, available_probes)
        if selected_probes:
            logger.info(
                f"DirectiveGenerator: Selected {len(selected_probes)} relevant probes: {selected_probes}"
            )
        else:
            logger.info(
                "DirectiveGenerator: No relevant probes selected — directive will be reasoning-only"
            )

        # Step 3: Generate directive content with @probe: references
        content, name, description = await self._generate_content(
            context, selected_probes
        )
        logger.info(f"DirectiveGenerator: Generated directive '{name}'")

        # Step 4: Check semantic similarity with existing directives
        similarity_score, similar_id = await self._check_similarity(
            name, description, content
        )
        logger.info(
            f"DirectiveGenerator: Similarity check - score={similarity_score:.2f}, similar_id={similar_id}"
        )

        # Create GeneratedDirective object
        generated = GeneratedDirective(
            name=name,
            description=description,
            content=content,
            probe_ids=[],  # Will be extracted by Registry from @probe: references
            metadata={
                "auto_generated": True,
                "source_query": context.query,
                "selected_probes": selected_probes,
            },
            has_tools=bool(selected_probes),
            similarity_score=similarity_score,
            similar_directive_id=similar_id,
        )

        return generated

    def _read_available_probes(self) -> list[dict[str, Any]]:
        """Read all available probes from ProbeRegistry.

        Returns:
            List of probe metadata dicts with name, description, parameters
        """
        probes = []
        # ProbeRegistry.all() returns all registered probes
        for probe in self.probe_registry.all():
            probes.append(
                {
                    "id": probe.name,
                    "name": probe.name,
                    "description": probe.description or "No description",
                    "parameters": getattr(probe, "parameters", {}),
                }
            )
        return probes

    async def _select_relevant_probes(
        self, context: GatheredContext, available_probes: list[dict[str, Any]]
    ) -> list[str]:
        """Use LLM to select relevant probes for this task.

        Args:
            context: Gathered context about the task
            available_probes: All available probes

        Returns:
            List of selected probe IDs
        """
        # Format probes for prompt (truncate descriptions to avoid 413 errors)
        probes_text = "\n".join(
            [f"- {p['id']}: {_truncate_description(p['description'])}" for p in available_probes]
        )

        prompt = f"""You are selecting which probes (tools) are needed for a task.

## Task Description
Query: {context.query}
Role needed: {context.role_expertise or 'To be determined'}
Approach: {', '.join(context.approach_steps) if context.approach_steps else 'To be determined'}

## Available Probes
{probes_text}

## Your Task
Select 0-5 probes that are DIRECTLY relevant to this task. Only select probes that will be actively used.

**Important:**
- Be conservative - only select probes that are clearly needed
- Don't select probes "just in case" - only if you're confident they'll be used
- If the task doesn't need any external data/tools, return an empty list

Return ONLY a JSON array of probe IDs, nothing else.

Example: ["search_google_news", "get_financial_data"]
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.ainvoke(messages, temperature=0.2, max_tokens=500)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            selected = _extract_json(content)

            # Validate that selected probes exist
            valid_ids = [p["id"] for p in available_probes]
            selected = [probe_id for probe_id in selected if probe_id in valid_ids]

            return selected

        except Exception as e:
            logger.error(f"DirectiveGenerator: Error selecting probes: {str(e)}")
            return []

    async def _generate_content(
        self, context: GatheredContext, selected_probes: list[str]
    ) -> tuple[str, str, str]:
        """Generate directive content with @probe: references embedded.

        Args:
            context: Gathered context
            selected_probes: Selected probe IDs

        Returns:
            Tuple of (content, name, description)
        """
        # Format probes with @probe: syntax
        probes_text = ""
        if selected_probes:
            probe_details = []
            for probe_id in selected_probes:
                probe = self.probe_registry.get(probe_id)
                if probe:
                    desc = getattr(probe, "description", "")
                    probe_details.append(f"@probe:{probe_id} — {desc}")

            probes_text = "\n".join(probe_details)

        # Build generation prompt
        prompt = f"""You are an expert at writing directives for AI agents. Your job is to create a specific, opinionated playbook that reads like expert instructions.

## Task Context
**User Query:** {context.query}

**Gathered Requirements:**
- Role/Expertise: {context.role_expertise or 'Not specified'}
- Approach: {', '.join(context.approach_steps) if context.approach_steps else 'Not specified'}
- Output Format: {context.output_format or 'Not specified'}
- Constraints: {', '.join(context.constraints) if context.constraints else 'Not specified'}
- Tone/Style: {context.tone_style or 'Professional'}

**Available Probes (embed these naturally in your approach):**
{probes_text if probes_text else 'No probes selected - this is a reasoning-only task'}

## Your Task
Write a directive that reads like a seasoned expert instructing a junior analyst. Make it specific and actionable.

**Structure your directive with these elements:**

1. **Role & Expertise** - Who is the agent? What domain knowledge do they have?
2. **Approach** - Step-by-step reasoning for the task. EMBED probe references naturally using @probe:name syntax.
   Example: "First, use @probe:search_financials to pull Q4 earnings data, then cross-reference with @probe:extract_metrics to validate P/E ratios."
3. **Output Format** - Concrete structure (JSON schema, markdown sections, bullet format)
4. **Constraints** - Hard boundaries for the task
5. **Tone/Style** - How should the output be written? (if relevant)

**CRITICAL:**
- Write as if you're an expert in this domain instructing someone
- Be specific and opinionated, not generic
- Embed @probe: references naturally in the Approach section
- The content should be a complete system prompt ready to use

**If this is a research directive with multiple tools, include these tactical instructions in the content:**
- For multi-entity tasks, specify the tool sequence: start with Wikipedia/comprehensive sources for historical data, then web search for supplemental sources, then news only for recent events
- Add a "Definitional Compliance" section telling the agent to strictly follow any category definitions the user provides and to avoid common misclassifications
- Add a "Completeness Priority" section: when a source contains a list or table, extract EVERY entry, not just highlights
- Tell the agent to cross-reference across sources and clearly label information by source

Also provide:
- A short name for this directive (2-5 words, use Title Case)
- A one-sentence description

Return your response as JSON:
{{
  "name": "Directive Name",
  "description": "One sentence description",
  "content": "The full directive content..."
}}
"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.ainvoke(
                messages, temperature=0.7, max_tokens=get_default_max_tokens()
            )
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            result = _extract_json(content)

            generated_content = result.get("content", "")

            # Append honesty clause or tool-usage instruction based on probe availability
            if selected_probes:
                generated_content += (
                    "\n\n## Tool Usage\n"
                    "You have access to external tools. Use them to verify facts and source information. Always cite tool-provided data.\n"
                    "If any tool returns an error or empty results, fall back to your training knowledge for that specific information. "
                    "Clearly label which information came from tools vs training knowledge. "
                    "Never return an empty or apologetic response when you have relevant training knowledge available."
                )
            else:
                generated_content += (
                    "\n\n## Important Limitation\n"
                    "You do not have access to external search tools, databases, or live data sources for this task.\n"
                    "Your response is based entirely on your training knowledge. Be transparent about this:\n"
                    "- Preface your response with a brief note that results are from training knowledge, not live research\n"
                    "- Flag any facts you are uncertain about\n"
                    "- Do not present training data as if it has been verified against external sources\n"
                    "- If the user's request would significantly benefit from external tool access, note this and suggest they could get better results with research tools"
                )

            return (
                generated_content,
                result.get("name", "Generated Directive"),
                result.get("description", "Auto-generated directive"),
            )

        except Exception as e:
            logger.error(f"DirectiveGenerator: Error generating content: {str(e)}")
            # Fallback: build a useful directive that preserves probe references
            fallback_content = f"You are an expert assistant helping with: {context.query}\n\n"
            if context.role_expertise:
                fallback_content += f"## Role\n{context.role_expertise}\n\n"
            if context.approach_steps:
                fallback_content += "## Approach\n" + "\n".join(
                    f"- {step}" for step in context.approach_steps
                ) + "\n\n"
            # Inject @probe: references so they survive into the saved directive
            if selected_probes:
                fallback_content += "## Available Tools\n"
                for probe_id in selected_probes:
                    fallback_content += f"Use @probe:{probe_id} to gather relevant information.\n"
                fallback_content += "\nUse these tools to verify facts and source information. Always cite tool-provided data.\n"
            else:
                fallback_content += "Provide a clear, helpful response based on your knowledge.\n"

            # Derive a name from the query instead of "General Assistant"
            name_words = context.query.split()[:5]
            fallback_name = " ".join(w.capitalize() for w in name_words) if name_words else "Generated Directive"

            logger.warning(
                f"DirectiveGenerator: Content generation failed, using fallback directive '{fallback_name}' "
                f"with {len(selected_probes)} probe references preserved"
            )
            return (
                fallback_content,
                fallback_name,
                f"Auto-generated directive for: {context.query[:80]}",
            )

    async def _check_similarity(
        self, name: str, description: str, content: str
    ) -> tuple[float, str | None]:
        """Check semantic similarity with existing directives.

        Args:
            name: Generated directive name
            description: Generated directive description
            content: Generated directive content

        Returns:
            Tuple of (similarity_score, similar_directive_id)
            Score is 0.0-1.0, where 1.0 is identical
        """
        # TODO: Implement vector similarity using embeddings
        # For now, use simple string matching
        existing = self.directive_registry.list_directives()

        best_score = 0.0
        best_id = None

        # Simple heuristic: check name similarity
        for directive in existing:
            # Skip hidden directives
            if directive.metadata and directive.metadata.get("hidden"):
                continue

            # Simple word overlap in name
            name_words = set(name.lower().split())
            directive_words = set(directive.name.lower().split())
            overlap = len(name_words & directive_words)
            total = len(name_words | directive_words)
            score = overlap / total if total > 0 else 0.0

            if score > best_score:
                best_score = score
                best_id = directive.id

        logger.info(
            f"DirectiveGenerator: Best similarity - {best_score:.2f} with {best_id}"
        )

        return best_score, best_id

    async def save_directive(self, generated: GeneratedDirective) -> str:
        """Save generated directive to Registry.

        Args:
            generated: GeneratedDirective to save

        Returns:
            Directive ID
        """
        # Generate unique ID
        import uuid

        directive_id = f"gen-{uuid.uuid4().hex[:8]}"

        # Create Directive object
        directive = Directive(
            id=directive_id,
            name=generated.name,
            description=generated.description,
            content=generated.content,
            probe_ids=[],  # Will be extracted from @probe: references by Registry
            reference_ids=[],
            template_variables=[],
            metadata=generated.metadata,
        )

        # Save to Registry (will auto-extract probe_ids from @probe: references)
        created, warnings = await self.directive_registry.create_directive(directive)

        if warnings:
            logger.warning(
                f"DirectiveGenerator: Directive saved with {len(warnings)} warnings: {[w.message for w in warnings]}"
            )

        # Verification logging
        logger.info(
            f"DirectiveGenerator: Saved directive '{generated.name}' with ID {directive_id}"
        )
        logger.info(
            f"DirectiveGenerator: Final directive content (preview): {generated.content[:500]!r}"
        )
        logger.info(
            f"DirectiveGenerator: Final directive probe_ids: {created.probe_ids if hasattr(created, 'probe_ids') else 'N/A'}"
        )
        selected_probes = generated.metadata.get("selected_probes", [])
        final_probe_ids = created.probe_ids if hasattr(created, "probe_ids") else []
        if selected_probes and not final_probe_ids:
            logger.error(
                f"DirectiveGenerator: Probe attachment failed: selected {len(selected_probes)} probes "
                f"{selected_probes} but directive has 0 probe_ids. "
                f"Check that @probe: references exist in content and Registry extracts them."
            )

        return directive_id

    def format_preview(self, generated: GeneratedDirective) -> str:
        """Format directive for user preview/approval.

        Args:
            generated: GeneratedDirective to format

        Returns:
            Human-readable preview string
        """
        preview = f"""# {generated.name}

**Description:** {generated.description}

**Auto-detected probes:** {', '.join(generated.metadata.get('selected_probes', [])) if generated.metadata.get('selected_probes') else 'None'}

## Directive Content:
{generated.content}

---
**Note:** This directive was auto-generated based on your query. You can approve it to save for future use.
"""
        return preview
