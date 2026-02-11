"""Execution context for constellation/star execution.

This module provides ConstellationContext, which contains all the runtime state
needed for executing stars within a constellation. It extends the base ExecutionContext
from core.runtime with constellation-specific fields.

Once Phase 1+2 are complete, this will import and extend ExecutionContext from
astro.core.runtime.context. For now, it includes all necessary fields.
"""

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

# Runtime event imports
from astro.core.runtime.events import (
    LogEvent,
    ProgressEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    truncate_output,
)

# Model imports for dynamic directive creation
from astro.core.models.directive import Directive
from astro.core.models.template_variable import TemplateVariable
from astro.orchestration.models.star_types import StarType
from astro.orchestration.stars.worker import WorkerStar

if TYPE_CHECKING:
    from astro.orchestration.models.constellation import Constellation
    from astro.orchestration.stars.base import BaseStar


# Type alias for star outputs - can be any output model
StarOutput = Any


class ConstellationContext(BaseModel):
    """Runtime context for Star execution within a constellation.

    This context provides stars with access to:
    - Run identity and constellation purpose
    - Variable bindings from the user
    - Outputs from upstream nodes
    - Methods to look up directives and navigate the constellation graph
    - Streaming capabilities for real-time event emission
    - Tool result caching for optimization

    Layer 2 concept - extends base ExecutionContext with constellation-specific fields.
    """

    # Run identity
    run_id: str
    constellation_id: str

    # Original input
    original_query: str = ""
    constellation_purpose: str = ""
    variables: Dict[str, Any] = Field(default_factory=dict)

    # Constellation-specific state
    node_outputs: Dict[str, StarOutput] = Field(default_factory=dict)
    loop_count: int = Field(default=0)

    # Current node context (set by runner during execution)
    current_node_id: Optional[str] = Field(
        default=None, description="ID of the currently executing node"
    )
    current_node_name: Optional[str] = Field(
        default=None, description="Display name of the currently executing node"
    )

    # Cache for tool/probe results across stars (keyed on tool_name + sorted args JSON)
    tool_result_cache: Dict[str, str] = Field(default_factory=dict)

    # Registry/Foundry reference for lookups (Any to avoid circular import)
    # In V2, this will be a Registry instance
    foundry: Any = Field(default=None)

    # Stream for real-time events (None = no streaming)
    stream: Optional[Any] = Field(default=None)  # ExecutionStream type

    model_config = {"arbitrary_types_allowed": True}

    # =========================================================================
    # Stream Event Emission Helpers
    # =========================================================================

    async def emit_thought(self, content: str, is_complete: bool = False) -> None:
        """Emit a thought/reasoning event from the current node.

        Use this to stream LLM reasoning tokens in real-time.

        Args:
            content: The thought content (may be partial token).
            is_complete: Whether this completes the thought.
        """
        if self.stream is None or self.current_node_id is None:
            return

        event = ThoughtEvent(
            run_id=self.run_id,
            node_id=self.current_node_id,
            content=content,
            is_complete=is_complete,
        )
        await self.stream.emit(event)

    async def emit_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> str:
        """Emit a tool/probe call event.

        Args:
            tool_name: Name of the tool being called.
            tool_input: Input parameters for the tool.
            call_id: Optional unique ID (generated if not provided).

        Returns:
            The call_id for matching with tool_result.
        """
        if call_id is None:
            call_id = f"call_{uuid.uuid4().hex[:8]}"

        if self.stream is None or self.current_node_id is None:
            return call_id

        event = ToolCallEvent(
            run_id=self.run_id,
            node_id=self.current_node_id,
            tool_name=tool_name,
            tool_input=tool_input,
            call_id=call_id,
        )
        await self.stream.emit(event)
        return call_id

    async def emit_tool_result(
        self,
        tool_name: str,
        call_id: str,
        success: bool,
        result_preview: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        """Emit a tool/probe result event.

        Args:
            tool_name: Name of the tool.
            call_id: Matching call_id from emit_tool_call.
            success: Whether the tool call succeeded.
            result_preview: Truncated result preview.
            error: Error message if failed.
            duration_ms: Execution time in milliseconds.
        """
        if self.stream is None or self.current_node_id is None:
            return

        event = ToolResultEvent(
            run_id=self.run_id,
            node_id=self.current_node_id,
            tool_name=tool_name,
            call_id=call_id,
            success=success,
            result_preview=truncate_output(result_preview),
            error=error,
            duration_ms=duration_ms,
        )
        await self.stream.emit(event)

    async def emit_progress(
        self,
        message: str,
        percent: Optional[int] = None,
    ) -> None:
        """Emit a progress update event.

        Args:
            message: Progress message.
            percent: Optional completion percentage (0-100).
        """
        if self.stream is None or self.current_node_id is None:
            return

        event = ProgressEvent(
            run_id=self.run_id,
            node_id=self.current_node_id,
            message=message,
            percent=percent,
        )
        await self.stream.emit(event)

    async def emit_log(
        self,
        message: str,
        level: str = "info",
    ) -> None:
        """Emit a log event.

        Args:
            message: Log message.
            level: Log level (debug, info, warning, error).
        """
        if self.stream is None:
            return

        event = LogEvent(
            run_id=self.run_id,
            level=level,  # type: ignore
            message=message,
            node_id=self.current_node_id,
        )
        await self.stream.emit(event)

    # =========================================================================
    # Directive and Constellation Lookups
    # =========================================================================

    def get_directive(self, directive_id: str) -> Any:
        """Get directive from Registry/Foundry.

        Args:
            directive_id: The directive ID to look up.

        Returns:
            The Directive instance.

        Raises:
            ValueError: If directive not found or foundry not set.
        """
        if self.foundry is None:
            raise ValueError("Foundry/Registry not set in execution context")

        directive = self.foundry.get_directive(directive_id)
        if not directive:
            raise ValueError(f"Directive '{directive_id}' not found")
        return directive

    def get_constellation(self) -> "Constellation":
        """Get the current constellation from Registry/Foundry.

        Returns:
            The Constellation instance.

        Raises:
            ValueError: If constellation not found or foundry not set.
        """
        if self.foundry is None:
            raise ValueError("Foundry/Registry not set in execution context")

        constellation = self.foundry.get_constellation(self.constellation_id)
        if not constellation:
            raise ValueError(f"Constellation '{self.constellation_id}' not found")
        return constellation

    # =========================================================================
    # Upstream Output Access
    # =========================================================================

    def get_upstream_outputs(self, node_id: str) -> List[StarOutput]:
        """Get outputs from all upstream nodes.

        Args:
            node_id: The node to get upstream outputs for.

        Returns:
            List of outputs from upstream nodes.
        """
        constellation = self.get_constellation()
        upstream_nodes = constellation.get_upstream_nodes(node_id)
        return [
            self.node_outputs[n.id] for n in upstream_nodes if n.id in self.node_outputs
        ]

    def get_direct_upstream_outputs(self) -> Dict[str, StarOutput]:
        """Get outputs from only direct upstream nodes of the current node.

        Uses the constellation graph to find direct predecessors.
        Falls back to all node_outputs if graph lookup fails.

        Returns:
            Dict of node_id to output for direct upstream nodes only.
        """
        if self.current_node_id is None:
            return dict(self.node_outputs)

        try:
            constellation = self.get_constellation()
            upstream_nodes = constellation.get_upstream_nodes(self.current_node_id)
            upstream_ids = {n.id for n in upstream_nodes}
            return {
                nid: output
                for nid, output in self.node_outputs.items()
                if nid in upstream_ids
            }
        except Exception:
            # Fallback to all outputs if graph lookup fails
            return dict(self.node_outputs)

    def get_upstream_output(self, output_type: Type[Any]) -> Optional[Any]:
        """Get first upstream output of given type (e.g., Plan).

        Args:
            output_type: The type to search for.

        Returns:
            First matching output or None.
        """
        for output in self.node_outputs.values():
            if isinstance(output, output_type):
                return output
        return None

    # =========================================================================
    # Dynamic Star Creation (for Planning Stars)
    # =========================================================================

    def find_star_for_task(self, task: Any) -> Optional["BaseStar"]:
        """Find existing Star matching task description.

        Searches Registry/Foundry's registered stars for one that matches the task.

        Args:
            task: The task to find a star for.

        Returns:
            Matching Star or None.
        """
        if self.foundry is None:
            return None

        # Search through all stars for one matching the task description
        task_keywords = set(task.description.lower().split())

        best_match: Optional["BaseStar"] = None
        best_score = 0

        for star in self.foundry.list_stars():
            # Skip hidden/internal stars
            if star.metadata and star.metadata.get("hidden"):
                continue

            # Get directive for description matching
            directive = self.foundry.get_directive(star.directive_id)
            if not directive:
                continue

            # Simple keyword matching
            star_keywords = set(star.name.lower().split())
            desc_keywords = set(directive.description.lower().split())
            all_star_keywords = star_keywords | desc_keywords

            overlap = len(task_keywords & all_star_keywords)
            if overlap > best_score:
                best_score = overlap
                best_match = star

        # Require at least 2 keyword matches
        return best_match if best_score >= 2 else None

    async def create_dynamic_star(self, task: Any) -> "WorkerStar":
        """Create Star + Directive dynamically for task.

        Creates a new directive and worker star for the given task,
        marking them as AI-generated.

        Args:
            task: The task to create a star for.

        Returns:
            Newly created WorkerStar with ai_generated=True.

        Raises:
            ValueError: If Foundry/Registry is not available.
        """
        if self.foundry is None:
            raise ValueError("Foundry/Registry not set in execution context")

        # Generate unique IDs
        task_id = uuid.uuid4().hex[:8]
        directive_id = f"_dynamic_directive_{task_id}"
        star_id = f"_dynamic_star_{task_id}"

        # Extract success_criteria and constraints from metadata if available
        success_criteria = task.metadata.get(
            "success_criteria", "Task completed successfully."
        )
        constraints = task.metadata.get("constraints", "None specified.")

        # Create directive for the task
        directive = Directive(
            id=directive_id,
            name=f"Dynamic: {task.description[:50]}",
            description=task.description,
            content=f"""Complete the following task:

{task.description}

Success criteria:
{success_criteria}

Constraints:
{constraints}
""",
            template_variables=[
                TemplateVariable(
                    name="task_context",
                    description="Context from upstream nodes",
                    required=False,
                )
            ],
            metadata={"ai_generated": True, "hidden": True},
        )

        # Create star
        star = WorkerStar(
            id=star_id,
            name=f"Worker: {task.description[:30]}",
            type=StarType.WORKER,
            directive_id=directive_id,
            metadata={"ai_generated": True},
        )

        # Persist via Foundry/Registry
        await self.foundry.create_directive(directive)
        await self.foundry.create_star(star)

        return star

    # =========================================================================
    # Document Access (for DocExStar)
    # =========================================================================

    def get_documents(self) -> List[Any]:
        """Get documents for DocExStar processing.

        Returns:
            List of documents from variables or upstream.
        """
        # Check variables for documents
        if "documents" in self.variables:
            docs: List[Any] = self.variables["documents"]
            return docs

        # Check upstream outputs for documents
        for output in self.node_outputs.values():
            if hasattr(output, "documents"):
                output_docs: List[Any] = output.documents
                return output_docs

        return []

    # =========================================================================
    # Tool Result Caching
    # =========================================================================

    def get_cached_tool_result(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Optional[str]:
        """Check if a tool call result is cached.

        Args:
            tool_name: Name of the tool.
            tool_args: Arguments to the tool.

        Returns:
            Cached result string or None.
        """
        import json

        cache_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True, default=str)}"
        return self.tool_result_cache.get(cache_key)

    def cache_tool_result(
        self, tool_name: str, tool_args: Dict[str, Any], result: str
    ) -> None:
        """Cache a tool call result.

        Args:
            tool_name: Name of the tool.
            tool_args: Arguments to the tool.
            result: The result string to cache.
        """
        import json

        cache_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True, default=str)}"
        self.tool_result_cache[cache_key] = result
