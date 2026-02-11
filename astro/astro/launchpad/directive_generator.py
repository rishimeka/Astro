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

import logging
from dataclasses import dataclass
from typing import Any

from astro.core.models.directive import Directive
from astro.core.probes.registry import ProbeRegistry
from astro.core.registry.registry import Registry

logger = logging.getLogger(__name__)


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
            f"DirectiveGenerator: Found {len(available_probes)} available probes"
        )

        # Step 2: Select relevant probes for this task
        selected_probes = await self._select_relevant_probes(context, available_probes)
        logger.info(
            f"DirectiveGenerator: Selected {len(selected_probes)} relevant probes"
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
        # Format probes for prompt
        probes_text = "\n".join(
            [f"- {p['id']}: {p['description']}" for p in available_probes]
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

            # Parse JSON response
            import json

            # Extract JSON array from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            selected = json.loads(content)

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
                messages, temperature=0.7, max_tokens=2000
            )
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse JSON response
            import json

            # Extract JSON from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)

            return (
                result.get("content", ""),
                result.get("name", "Generated Directive"),
                result.get("description", "Auto-generated directive"),
            )

        except Exception as e:
            logger.error(f"DirectiveGenerator: Error generating content: {str(e)}")
            # Fallback: basic directive
            return (
                f"You are helping with: {context.query}\n\nProvide a clear, helpful response.",
                "General Assistant",
                "General-purpose assistant for various tasks",
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

        logger.info(
            f"DirectiveGenerator: Saved directive '{generated.name}' with ID {directive_id}"
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
