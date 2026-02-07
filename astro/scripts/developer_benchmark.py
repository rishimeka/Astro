#!/usr/bin/env python3
"""
Developer Benchmark - LLM-as-Developer for building Astro Constellations.

This benchmark simulates a first-time developer using Astro to build constellations.
An LLM acts as the developer, making API calls to discover probes, create directives/stars,
and wire up complete constellations.

Usage:
    cd /Users/rishimeka/Documents/Code/astrix-labs/astro

    # Run full developer benchmark (5 use cases)
    PYTHONPATH=. python scripts/developer_benchmark.py

    # Run specific use cases
    PYTHONPATH=. python scripts/developer_benchmark.py --use-cases investment_dd competitive_intel

    # Run with different model
    PYTHONPATH=. python scripts/developer_benchmark.py --model gpt-4o

    # Enable verbose output
    PYTHONPATH=. python scripts/developer_benchmark.py --verbose

Metrics captured:
- Per-phase timing: Discovery, directive creation, star creation, constellation wiring
- Total time per constellation: End-to-end time to build each constellation
- LLM usage: Tokens and cost for the "developer thinking"
- Errors/retries: Count of validation errors (simulating learning curve)
- Average time: Mean across all constellations
"""

import argparse
import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# Import probes module to trigger probe registration
# This must happen before we try to list probes
import astro_backend_service.probes  # noqa: F401

# Pricing per 1M tokens
PRICING = {
    "gpt-5-nano": {"input": 0.10, "output": 0.40},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}


# =============================================================================
# Data Classes for Metrics
# =============================================================================


@dataclass
class TokenUsage:
    """Track token usage across LLM calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0

    def add(self, input_tokens: int, output_tokens: int):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens
        self.calls += 1

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "llm_calls": self.calls,
        }


@dataclass
class PhaseMetrics:
    """Timing metrics for each phase of constellation building."""
    discovery_ms: float = 0.0
    directive_creation_ms: float = 0.0
    star_creation_ms: float = 0.0
    constellation_wiring_ms: float = 0.0
    validation_ms: float = 0.0
    total_ms: float = 0.0
    errors_encountered: int = 0
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discovery_ms": round(self.discovery_ms, 2),
            "directive_creation_ms": round(self.directive_creation_ms, 2),
            "star_creation_ms": round(self.star_creation_ms, 2),
            "constellation_wiring_ms": round(self.constellation_wiring_ms, 2),
            "validation_ms": round(self.validation_ms, 2),
            "total_ms": round(self.total_ms, 2),
            "errors_encountered": self.errors_encountered,
            "retries": self.retries,
        }


@dataclass
class DeveloperBenchmarkResult:
    """Result from a single developer benchmark run."""
    use_case: str
    phases: PhaseMetrics
    llm_tokens: TokenUsage
    llm_cost: float
    constellation_id: str
    node_count: int
    edge_count: int
    directive_count: int
    star_count: int
    success: bool
    error_message: Optional[str] = None
    created_ids: Dict[str, List[str]] = field(default_factory=lambda: {
        "directives": [],
        "stars": [],
        "constellations": [],
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "use_case": self.use_case,
            "phases": self.phases.to_dict(),
            "llm_tokens": self.llm_tokens.to_dict(),
            "llm_cost": round(self.llm_cost, 4),
            "constellation_id": self.constellation_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "directive_count": self.directive_count,
            "star_count": self.star_count,
            "success": self.success,
            "error_message": self.error_message,
            "created_ids": self.created_ids,
        }


# =============================================================================
# Use Case Prompts
# =============================================================================

USE_CASES = {
    "investment_dd": """
Build a due diligence workflow for analyzing a company before investment.

Requirements:
- Financial analysis: revenue, earnings, balance sheet health
- Market sentiment analysis: news, social media, analyst ratings
- Regulatory/compliance analysis: SEC filings, legal cases
- Competitive landscape analysis: market position, competitors
- Risk scoring: aggregate risk assessment
- Final synthesis: comprehensive investment thesis with bull/bear cases

Architecture:
- 4 parallel analysts (financial, sentiment, regulatory, competitive)
- 1 risk scorer that waits for all analysts
- 1 final synthesis node
- ~10 nodes total with appropriate edges

The workflow should take a company_name variable and produce a final due diligence report.
    """,

    "competitive_intel": """
Build a competitive intelligence workflow for tracking competitors in a market.

Requirements:
- Market research: industry trends, market size, growth rates
- Competitor profiling: identify top 3-5 competitors, their positioning
- SWOT analysis: strengths, weaknesses, opportunities, threats
- Pricing analysis: competitor pricing strategies
- Channel analysis: distribution and go-to-market strategies
- Strategic synthesis: recommendations report

Architecture:
- Planning node to identify competitors
- Parallel analysis nodes (market, pricing, channel)
- SWOT analysis node
- Final strategic recommendations synthesis
- ~8-10 nodes total

The workflow should take an industry/market variable and produce competitive insights.
    """,

    "risk_assessment": """
Build a risk assessment pipeline for evaluating business risks.

Requirements:
- Legal risk analysis: litigation exposure, contract risks
- Regulatory risk: compliance status, pending regulations
- Reputational risk: media sentiment, brand perception
- Operational risk: supply chain, key person dependencies
- Risk aggregation: weighted risk scoring
- Mitigation synthesis: risk summary with recommendations

Architecture:
- 4 parallel risk analyzers (legal, regulatory, reputational, operational)
- 1 aggregation node that computes weighted scores
- 1 synthesis node for final report
- ~8-10 nodes total

The workflow should take an entity_name variable and produce a risk assessment report.
    """,

    "product_launch": """
Build a product launch analysis workflow.

Requirements:
- Market sizing: TAM/SAM/SOM analysis
- Competitor response prediction: how will competitors react
- Pricing strategy: optimal pricing based on market
- Channel strategy: best go-to-market approach
- Launch timeline: phased rollout recommendations
- Final synthesis: launch plan document

Architecture:
- Market sizing and competitor nodes can run in parallel
- Pricing depends on market sizing
- Channel strategy can run parallel to pricing
- Final synthesis combines all
- ~8-10 nodes total

The workflow should take product_name and target_market variables.
    """,

    "ma_screening": """
Build an M&A target screening workflow.

Requirements:
- Financial health: balance sheet, cash flow, profitability
- Strategic fit: synergy analysis, strategic rationale
- Cultural fit: organizational culture, integration challenges
- Integration planning: high-level integration approach
- Valuation: rough valuation range
- Final synthesis: M&A recommendation memo

Architecture:
- Financial and strategic fit can run in parallel
- Cultural fit depends on strategic fit
- Integration planning depends on cultural fit
- Valuation can run parallel to integration planning
- Final synthesis brings everything together
- ~8-10 nodes total

The workflow should take target_company and acquirer_company variables.
    """,
}


# =============================================================================
# AstroToolset - Tools for the LLM Developer
# =============================================================================

class AstroToolset:
    """
    Tools the LLM developer can use to interact with Astro.
    Uses FoundryPersistence directly for speed (bypassing HTTP).
    """

    def __init__(self, persistence):
        """
        Initialize the toolset.

        Args:
            persistence: FoundryPersistence instance for direct DB access.
        """
        from astro_backend_service.foundry.persistence import FoundryPersistence
        self.persistence: FoundryPersistence = persistence
        self.created_directives: List[str] = []
        self.created_stars: List[str] = []
        self.created_constellations: List[str] = []

    async def list_probes(self) -> List[Dict[str, Any]]:
        """
        List all available probes with their descriptions and schemas.

        Returns:
            List of probe information dicts with name, description, and schema.
        """
        from astro_backend_service.probes import ProbeRegistry

        probes = ProbeRegistry.all()
        return [
            {
                "name": p.name,
                "description": p.description,
                "input_schema": p.input_schema,
            }
            for p in probes
        ]

    async def list_existing_directives(self) -> List[Dict[str, Any]]:
        """
        List existing directives that can be referenced.

        Returns:
            List of directive summaries.
        """
        directives = await self.persistence.list_directives()
        return [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "probe_ids": d.probe_ids,
                "template_variables": [v.name for v in d.template_variables],
            }
            for d in directives
        ]

    async def list_existing_stars(self) -> List[Dict[str, Any]]:
        """
        List existing stars that can be referenced.

        Returns:
            List of star summaries.
        """
        stars = await self.persistence.list_stars()
        return [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type.value if hasattr(s.type, 'value') else str(s.type),
                "directive_id": s.directive_id,
            }
            for s in stars
        ]

    async def create_directive(
        self,
        id: str,
        name: str,
        description: str,
        content: str,
        probe_ids: Optional[List[str]] = None,
        reference_ids: Optional[List[str]] = None,
        template_variables: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new directive.

        Args:
            id: Unique identifier for the directive.
            name: Human-readable name.
            description: Short summary for planner discovery.
            content: Full system prompt for worker agents.
            probe_ids: List of probe names this directive can use.
            reference_ids: IDs of child directives for sub-delegation.
            template_variables: Variables to be filled at runtime.
            metadata: Additional metadata tags.

        Returns:
            Created directive info or error message.
        """
        from astro_backend_service.models import Directive, TemplateVariable

        try:
            # Convert template variables from dicts
            tvars = []
            if template_variables:
                for tv in template_variables:
                    tvars.append(TemplateVariable(
                        name=tv.get("name", ""),
                        description=tv.get("description", ""),
                        required=tv.get("required", True),
                        default=tv.get("default"),
                        ui_hint=tv.get("ui_hint", "text"),
                        ui_options=tv.get("ui_options"),
                        used_by=[],
                    ))

            directive = Directive(
                id=id,
                name=name,
                description=description,
                content=content,
                probe_ids=probe_ids or [],
                reference_ids=reference_ids or [],
                template_variables=tvars,
                metadata=metadata or {},
            )

            await self.persistence.create_directive(directive)
            self.created_directives.append(id)

            return {
                "status": "success",
                "id": id,
                "name": name,
                "message": f"Directive '{name}' created successfully.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create directive: {str(e)}",
            }

    async def create_star(
        self,
        id: str,
        name: str,
        star_type: str,
        directive_id: str,
        probe_ids: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new star.

        Args:
            id: Unique identifier for the star.
            name: Human-readable name.
            star_type: Type of star (worker, synthesis, planning, eval, execution, docex).
            directive_id: ID of the directive this star uses.
            probe_ids: Additional probes beyond the directive's probes.
            config: Star-specific configuration.
            metadata: Additional metadata.

        Returns:
            Created star info or error message.
        """
        from astro_backend_service.models.stars import (
            WorkerStar,
            PlanningStar,
            EvalStar,
            SynthesisStar,
            ExecutionStar,
            DocExStar,
        )

        try:
            star_classes = {
                "worker": WorkerStar,
                "planning": PlanningStar,
                "eval": EvalStar,
                "synthesis": SynthesisStar,
                "execution": ExecutionStar,
                "docex": DocExStar,
            }

            star_class = star_classes.get(star_type.lower())
            if not star_class:
                return {
                    "status": "error",
                    "error": f"Unknown star type: {star_type}",
                    "valid_types": list(star_classes.keys()),
                }

            # Build star kwargs
            star_kwargs = {
                "id": id,
                "name": name,
                "directive_id": directive_id,
                "config": config or {},
                "ai_generated": True,
                "metadata": metadata or {"benchmark_created": True},
            }

            # Add probe_ids for atomic stars
            if star_type.lower() in ["worker", "synthesis", "eval"]:
                star_kwargs["probe_ids"] = probe_ids or []

            # Add type-specific defaults
            if star_type.lower() == "worker":
                star_kwargs["max_iterations"] = config.get("max_iterations", 5) if config else 5

            star = star_class(**star_kwargs)
            await self.persistence.create_star(star)
            self.created_stars.append(id)

            return {
                "status": "success",
                "id": id,
                "name": name,
                "type": star_type,
                "message": f"Star '{name}' ({star_type}) created successfully.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create star: {str(e)}",
            }

    async def create_constellation(
        self,
        id: str,
        name: str,
        description: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a constellation with nodes and edges.

        Args:
            id: Unique identifier for the constellation.
            name: Human-readable name.
            description: Purpose of the constellation.
            nodes: List of node definitions. Each node needs:
                   - id: unique node id
                   - star_id: reference to a star
                   - position: {x, y} for UI layout
                   - display_name: optional display name
            edges: List of edge definitions. Each edge needs:
                   - id: unique edge id
                   - source: source node id
                   - target: target node id
                   - condition: optional condition string
            metadata: Additional metadata.

        Returns:
            Created constellation info or error message.
        """
        from astro_backend_service.models import (
            Constellation,
            StartNode,
            EndNode,
            StarNode,
            Edge,
            Position,
        )

        try:
            # Create start and end nodes
            start_node = StartNode(
                id="start",
                position=Position(x=0, y=300),
            )
            end_node = EndNode(
                id="end",
                position=Position(x=1400, y=300),
            )

            # Create star nodes
            star_nodes = []
            for node in nodes:
                star_node = StarNode(
                    id=node["id"],
                    star_id=node["star_id"],
                    position=Position(
                        x=node.get("position", {}).get("x", 200),
                        y=node.get("position", {}).get("y", 200),
                    ),
                    display_name=node.get("display_name"),
                )
                star_nodes.append(star_node)

            # Create edges
            edge_objects = []
            for edge in edges:
                edge_obj = Edge(
                    id=edge["id"],
                    source=edge["source"],
                    target=edge["target"],
                    condition=edge.get("condition"),
                )
                edge_objects.append(edge_obj)

            constellation = Constellation(
                id=id,
                name=name,
                description=description,
                start=start_node,
                end=end_node,
                nodes=star_nodes,
                edges=edge_objects,
                max_loop_iterations=3,
                max_retry_attempts=2,
                retry_delay_base=1.0,
                metadata=metadata or {"benchmark_created": True},
            )

            await self.persistence.create_constellation(constellation)
            self.created_constellations.append(id)

            return {
                "status": "success",
                "id": id,
                "name": name,
                "node_count": len(star_nodes),
                "edge_count": len(edge_objects),
                "message": f"Constellation '{name}' created with {len(star_nodes)} nodes and {len(edge_objects)} edges.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create constellation: {str(e)}",
            }

    async def validate_constellation(self, constellation_id: str) -> Dict[str, Any]:
        """
        Validate a constellation and return its required variables.

        Args:
            constellation_id: ID of the constellation to validate.

        Returns:
            Validation result with required variables or errors.
        """
        try:
            constellation = await self.persistence.get_constellation(constellation_id)
            if not constellation:
                return {
                    "status": "error",
                    "error": f"Constellation '{constellation_id}' not found.",
                }

            # Check all stars exist
            missing_stars = []
            for node in constellation.nodes:
                star = await self.persistence.get_star(node.star_id)
                if not star:
                    missing_stars.append(node.star_id)

            if missing_stars:
                return {
                    "status": "error",
                    "error": f"Missing stars: {missing_stars}",
                }

            # Check edges reference valid nodes
            all_node_ids = {"start", "end"} | {n.id for n in constellation.nodes}
            invalid_edges = []
            for edge in constellation.edges:
                if edge.source not in all_node_ids:
                    invalid_edges.append(f"source '{edge.source}' not found")
                if edge.target not in all_node_ids:
                    invalid_edges.append(f"target '{edge.target}' not found")

            if invalid_edges:
                return {
                    "status": "error",
                    "error": f"Invalid edges: {invalid_edges}",
                }

            # Gather required variables (simplified - would need Foundry for full implementation)
            required_variables = []
            for node in constellation.nodes:
                star = await self.persistence.get_star(node.star_id)
                if star:
                    directive = await self.persistence.get_directive(star.directive_id)
                    if directive:
                        for var in directive.template_variables:
                            if var.name not in [v["name"] for v in required_variables]:
                                required_variables.append({
                                    "name": var.name,
                                    "description": var.description,
                                    "required": var.required,
                                    "default": var.default,
                                })

            return {
                "status": "valid",
                "constellation_id": constellation_id,
                "node_count": len(constellation.nodes),
                "edge_count": len(constellation.edges),
                "required_variables": required_variables,
                "message": "Constellation is valid and ready to run.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_created_ids(self) -> Dict[str, List[str]]:
        """Get all IDs created during this session."""
        return {
            "directives": self.created_directives.copy(),
            "stars": self.created_stars.copy(),
            "constellations": self.created_constellations.copy(),
        }


# =============================================================================
# DeveloperAgent - LLM acting as developer
# =============================================================================

class DeveloperAgent:
    """
    An LLM agent that acts as a developer building Astro constellations.
    Uses LangChain's tool-calling pattern.
    """

    def __init__(
        self,
        toolset: AstroToolset,
        model: str = "gpt-5-nano",
        verbose: bool = False,
    ):
        """
        Initialize the developer agent.

        Args:
            toolset: AstroToolset instance for interacting with Astro.
            model: LLM model to use.
            verbose: Whether to print detailed progress.
        """
        self.toolset = toolset
        self.model = model
        self.verbose = verbose
        self.usage = TokenUsage()

    async def build_constellation(
        self,
        use_case_name: str,
        use_case_prompt: str,
    ) -> DeveloperBenchmarkResult:
        """
        Have the LLM build a constellation for the given use case.

        Args:
            use_case_name: Name of the use case (for identification).
            use_case_prompt: Detailed description of what to build.

        Returns:
            DeveloperBenchmarkResult with timing and metrics.
        """
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
        from langchain_core.tools import StructuredTool
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        phases = PhaseMetrics()
        total_start = time.perf_counter()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return DeveloperBenchmarkResult(
                use_case=use_case_name,
                phases=phases,
                llm_tokens=self.usage,
                llm_cost=0,
                constellation_id="",
                node_count=0,
                edge_count=0,
                directive_count=0,
                star_count=0,
                success=False,
                error_message="OPENAI_API_KEY not set",
            )

        llm = ChatOpenAI(
            model=self.model,
            temperature=0.2,
            api_key=SecretStr(api_key),
        )

        # Define tools for the LLM
        tools = [
            StructuredTool.from_function(
                coroutine=self.toolset.list_probes,
                name="list_probes",
                description="List all available probes (tools) with their descriptions and schemas. Use this first to understand what capabilities are available.",
            ),
            StructuredTool.from_function(
                coroutine=self.toolset.list_existing_directives,
                name="list_existing_directives",
                description="List existing directives that can be referenced or used as templates.",
            ),
            StructuredTool.from_function(
                coroutine=self.toolset.list_existing_stars,
                name="list_existing_stars",
                description="List existing stars that can be referenced.",
            ),
            StructuredTool.from_function(
                coroutine=self.toolset.create_directive,
                name="create_directive",
                description="""Create a new directive. Parameters:
- id: Unique identifier (use kebab-case, e.g., 'financial-analyst-v1')
- name: Human-readable name
- description: Short summary for discovery
- content: Full system prompt with instructions
- probe_ids: List of probe names this directive can use
- reference_ids: Optional IDs of child directives
- template_variables: List of {name, description, required, default} for runtime variables
- metadata: Optional tags""",
            ),
            StructuredTool.from_function(
                coroutine=self.toolset.create_star,
                name="create_star",
                description="""Create a new star. Parameters:
- id: Unique identifier (use kebab-case, e.g., 'star-financial-analyst')
- name: Human-readable name
- star_type: One of 'worker', 'synthesis', 'planning', 'eval', 'execution', 'docex'
- directive_id: ID of the directive this star uses
- probe_ids: Optional additional probes beyond directive's probes
- config: Optional configuration dict
- metadata: Optional metadata""",
            ),
            StructuredTool.from_function(
                coroutine=self.toolset.create_constellation,
                name="create_constellation",
                description="""Create a constellation with nodes and edges. Parameters:
- id: Unique identifier
- name: Human-readable name
- description: Purpose of the constellation
- nodes: List of {id, star_id, position: {x, y}, display_name}
- edges: List of {id, source, target, condition}. Source/target can be 'start' or 'end' for entry/exit points.
- metadata: Optional metadata""",
            ),
            StructuredTool.from_function(
                coroutine=self.toolset.validate_constellation,
                name="validate_constellation",
                description="Validate a constellation and get its required variables. Pass the constellation_id.",
            ),
        ]

        llm_with_tools = llm.bind_tools(tools)

        # System prompt for the developer agent
        system_prompt = """You are an expert developer building Astro constellation workflows.

Astro uses a DAG-based architecture with these components:
1. **Probes**: Atomic tools (search, data retrieval, etc.)
2. **Directives**: System prompts that define agent behavior, with probe scoping
3. **Stars**: Execution units that use directives. Types:
   - worker: Makes LLM calls with tools
   - synthesis: Aggregates outputs from upstream nodes
   - planning: Creates execution plans
   - eval: Makes go/no-go decisions
   - execution: Orchestrates parallel work
   - docex: Document extraction
4. **Constellations**: DAG workflows connecting stars via nodes and edges

Your task is to build a complete constellation:

1. DISCOVERY PHASE: First, list available probes to understand capabilities
2. DIRECTIVE PHASE: Create directives for each analyst/worker role
   - Each directive should have focused probe access (tool scoping)
   - Use @variable:name syntax for template variables in content
3. STAR PHASE: Create stars for each directive
   - Use appropriate star types (worker for analysis, synthesis for aggregation)
4. CONSTELLATION PHASE: Wire everything together
   - Create nodes referencing stars
   - Create edges including 'start' -> first nodes and last nodes -> 'end'
   - Position nodes logically (x increases left-to-right, y varies for parallel)
5. VALIDATION PHASE: Validate the constellation

Generate unique IDs using the pattern: {use_case}-{component}-{number} (e.g., 'investment-dd-financial-analyst-1')

IMPORTANT:
- Start nodes must connect FROM 'start'
- End nodes must connect TO 'end'
- Parallel nodes should have same x position, different y
- Sequential nodes should have increasing x positions
- Use descriptive content in directives with clear instructions"""

        user_message = f"""Build a constellation for this use case:

{use_case_prompt}

Start by listing available probes, then create the directives, stars, and constellation.
Use unique IDs prefixed with '{use_case_name}-'.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        # Track phases - use flags to ensure we only record first transition
        phase_start = time.perf_counter()
        current_phase = "discovery"
        phase_recorded = {
            "discovery": False,
            "directive": False,
            "star": False,
            "constellation": False,
            "validation": False,
        }
        directive_start = None
        star_start = None
        constellation_start = None

        max_iterations = 20
        iterations = 0
        constellation_id = ""

        try:
            while iterations < max_iterations:
                iterations += 1

                if self.verbose:
                    print(f"  Iteration {iterations}...")

                response = llm_with_tools.invoke(messages)

                # Track token usage
                if hasattr(response, "response_metadata"):
                    metadata = response.response_metadata
                    if "token_usage" in metadata:
                        usage = metadata["token_usage"]
                        self.usage.add(
                            usage.get("prompt_tokens", 0),
                            usage.get("completion_tokens", 0)
                        )

                # Process tool calls
                if hasattr(response, "tool_calls") and response.tool_calls:
                    messages.append(response)
                    tool_messages = []

                    for tc in response.tool_calls:
                        tool_name = tc.get("name", "")
                        tool_args = tc.get("args", {})

                        if self.verbose:
                            print(f"    Tool: {tool_name}")

                        # Track phase transitions based on first occurrence of each action type
                        now = time.perf_counter()

                        if tool_name == "create_directive":
                            if not phase_recorded["discovery"]:
                                # End discovery phase when first directive is created
                                phases.discovery_ms = (now - phase_start) * 1000
                                phase_recorded["discovery"] = True
                                directive_start = now
                            current_phase = "directive"

                        elif tool_name == "create_star":
                            if current_phase == "directive" and not phase_recorded["directive"]:
                                # End directive phase when first star is created
                                phases.directive_creation_ms = (now - (directive_start or phase_start)) * 1000
                                phase_recorded["directive"] = True
                                star_start = now
                            elif not phase_recorded["discovery"]:
                                # If we jump to stars without creating directives
                                phases.discovery_ms = (now - phase_start) * 1000
                                phase_recorded["discovery"] = True
                                star_start = now
                            current_phase = "star"

                        elif tool_name == "create_constellation":
                            if current_phase == "star" and not phase_recorded["star"]:
                                # End star phase when constellation is created
                                phases.star_creation_ms = (now - (star_start or directive_start or phase_start)) * 1000
                                phase_recorded["star"] = True
                                constellation_start = now
                            elif current_phase == "directive" and not phase_recorded["directive"]:
                                # If jumping from directive to constellation
                                phases.directive_creation_ms = (now - (directive_start or phase_start)) * 1000
                                phase_recorded["directive"] = True
                                constellation_start = now
                            elif not phase_recorded["discovery"]:
                                phases.discovery_ms = (now - phase_start) * 1000
                                phase_recorded["discovery"] = True
                                constellation_start = now
                            current_phase = "constellation"

                        elif tool_name == "validate_constellation":
                            if not phase_recorded["constellation"]:
                                # End constellation phase when validation starts
                                phases.constellation_wiring_ms = (now - (constellation_start or star_start or directive_start or phase_start)) * 1000
                                phase_recorded["constellation"] = True
                            current_phase = "validation"

                        elif tool_name in ["list_probes", "list_existing_directives", "list_existing_stars"]:
                            # These are discovery actions, don't change phase if we've moved past discovery
                            if current_phase == "discovery":
                                pass  # Stay in discovery

                        # Execute tool
                        try:
                            tool_func = {
                                "list_probes": self.toolset.list_probes,
                                "list_existing_directives": self.toolset.list_existing_directives,
                                "list_existing_stars": self.toolset.list_existing_stars,
                                "create_directive": self.toolset.create_directive,
                                "create_star": self.toolset.create_star,
                                "create_constellation": self.toolset.create_constellation,
                                "validate_constellation": self.toolset.validate_constellation,
                            }.get(tool_name)

                            if tool_func:
                                result = await tool_func(**tool_args)
                                result_str = json.dumps(result, indent=2)

                                # Track constellation ID
                                if tool_name == "create_constellation" and result.get("status") == "success":
                                    constellation_id = result.get("id", "")

                                # Track errors
                                if isinstance(result, dict) and result.get("status") == "error":
                                    phases.errors_encountered += 1
                            else:
                                result_str = f"Unknown tool: {tool_name}"
                                phases.errors_encountered += 1

                        except Exception as e:
                            result_str = f"Error executing {tool_name}: {str(e)}"
                            phases.errors_encountered += 1

                        tool_messages.append(
                            ToolMessage(content=result_str, tool_call_id=tc.get("id", ""))
                        )

                    messages.extend(tool_messages)
                    continue

                # No tool calls - agent is done
                now = time.perf_counter()
                if current_phase == "validation" and not phase_recorded["validation"]:
                    # Calculate validation time from when constellation phase ended
                    validation_start = constellation_start or star_start or directive_start or phase_start
                    phases.validation_ms = (now - validation_start) * 1000
                    phase_recorded["validation"] = True

                break

            # Calculate totals
            total_end = time.perf_counter()
            phases.total_ms = (total_end - total_start) * 1000

            # Calculate cost
            cost = self._calculate_cost()

            # Get created counts
            created_ids = self.toolset.get_created_ids()

            # Validate final constellation
            if constellation_id:
                validation = await self.toolset.validate_constellation(constellation_id)
                success = validation.get("status") == "valid"
                node_count = validation.get("node_count", 0)
                edge_count = validation.get("edge_count", 0)
                error_msg = validation.get("error") if not success else None
            else:
                success = False
                node_count = 0
                edge_count = 0
                error_msg = "No constellation was created"

            return DeveloperBenchmarkResult(
                use_case=use_case_name,
                phases=phases,
                llm_tokens=self.usage,
                llm_cost=cost,
                constellation_id=constellation_id,
                node_count=node_count,
                edge_count=edge_count,
                directive_count=len(created_ids["directives"]),
                star_count=len(created_ids["stars"]),
                success=success,
                error_message=error_msg,
                created_ids=created_ids,
            )

        except Exception as e:
            phases.total_ms = (time.perf_counter() - total_start) * 1000
            return DeveloperBenchmarkResult(
                use_case=use_case_name,
                phases=phases,
                llm_tokens=self.usage,
                llm_cost=self._calculate_cost(),
                constellation_id=constellation_id,
                node_count=0,
                edge_count=0,
                directive_count=len(self.toolset.created_directives),
                star_count=len(self.toolset.created_stars),
                success=False,
                error_message=str(e),
                created_ids=self.toolset.get_created_ids(),
            )

    def _calculate_cost(self) -> float:
        """Calculate LLM cost based on token usage."""
        pricing = PRICING.get(self.model, PRICING.get("gpt-5-nano", {"input": 0.10, "output": 0.40}))
        input_cost = (self.usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.usage.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


# =============================================================================
# Benchmark Runner
# =============================================================================

def format_time(ms: float) -> str:
    """Format milliseconds into human-readable string."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        minutes = int(ms / 60000)
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"


async def run_developer_benchmark(
    use_cases: Optional[List[str]] = None,
    model: str = "gpt-5-nano",
    output_dir: str = "benchmark_results",
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run the developer benchmark.

    Args:
        use_cases: List of use case names to run. None means all.
        model: LLM model to use.
        output_dir: Directory to save results.
        verbose: Whether to print detailed progress.

    Returns:
        Benchmark results dict.
    """
    from astro_backend_service.foundry.persistence import FoundryPersistence

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("MONGO_DB", "astro")

    print("\n" + "=" * 70)
    print("DEVELOPER BENCHMARK")
    print("LLM-as-Developer Building Astro Constellations")
    print("=" * 70)
    print(f"\nModel: {model}")
    print(f"MongoDB: {MONGO_URI}/{DATABASE_NAME}")

    # Initialize persistence
    persistence = FoundryPersistence(MONGO_URI, DATABASE_NAME)

    # Determine use cases to run
    if use_cases is None or "all" in use_cases:
        selected_use_cases = list(USE_CASES.keys())
    else:
        selected_use_cases = [uc for uc in use_cases if uc in USE_CASES]

    print(f"Use cases: {selected_use_cases}")
    print()

    results: List[DeveloperBenchmarkResult] = []

    for i, use_case_name in enumerate(selected_use_cases, 1):
        print(f"\n{'='*60}")
        print(f"Use Case {i}/{len(selected_use_cases)}: {use_case_name}")
        print("=" * 60)

        use_case_prompt = USE_CASES[use_case_name]

        # Create fresh toolset and agent for each use case
        toolset = AstroToolset(persistence)
        agent = DeveloperAgent(toolset, model=model, verbose=verbose)

        result = await agent.build_constellation(use_case_name, use_case_prompt)
        results.append(result)

        # Print result summary
        print(f"\n  Status: {'✓ Success' if result.success else '✗ Failed'}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
        print(f"  Constellation ID: {result.constellation_id}")
        print(f"  Nodes: {result.node_count}, Edges: {result.edge_count}")
        print(f"  Directives created: {result.directive_count}")
        print(f"  Stars created: {result.star_count}")
        print(f"\n  Phase Timing:")
        print(f"    Discovery:     {format_time(result.phases.discovery_ms)}")
        print(f"    Directives:    {format_time(result.phases.directive_creation_ms)}")
        print(f"    Stars:         {format_time(result.phases.star_creation_ms)}")
        print(f"    Constellation: {format_time(result.phases.constellation_wiring_ms)}")
        print(f"    Validation:    {format_time(result.phases.validation_ms)}")
        print(f"    Total:         {format_time(result.phases.total_ms)}")
        print(f"\n  LLM Usage:")
        print(f"    Tokens: {result.llm_tokens.total_tokens:,} ({result.llm_tokens.input_tokens:,} in, {result.llm_tokens.output_tokens:,} out)")
        print(f"    Calls: {result.llm_tokens.calls}")
        print(f"    Cost: ${result.llm_cost:.4f}")
        print(f"    Errors: {result.phases.errors_encountered}")

    # Close persistence
    await persistence.close()

    # Calculate summary statistics
    successful_results = [r for r in results if r.success]
    avg_time = sum(r.phases.total_ms for r in results) / len(results) if results else 0
    avg_cost = sum(r.llm_cost for r in results) / len(results) if results else 0
    success_rate = len(successful_results) / len(results) * 100 if results else 0
    avg_nodes = sum(r.node_count for r in successful_results) / len(successful_results) if successful_results else 0
    avg_edges = sum(r.edge_count for r in successful_results) / len(successful_results) if successful_results else 0
    total_errors = sum(r.phases.errors_encountered for r in results)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nResults by Use Case:")
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.use_case}: {format_time(result.phases.total_ms)}, ${result.llm_cost:.4f}, {result.node_count} nodes")

    print(f"\n{'='*40}")
    print(f"Average Time:     {format_time(avg_time)}")
    print(f"Average Cost:     ${avg_cost:.4f}")
    print(f"Success Rate:     {success_rate:.0f}%")
    print(f"Average Nodes:    {avg_nodes:.1f}")
    print(f"Average Edges:    {avg_edges:.1f}")
    print(f"Total Errors:     {total_errors}")
    print("=" * 40)

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    summary = {
        "timestamp": timestamp,
        "model": model,
        "use_cases": selected_use_cases,
        "individual_results": [r.to_dict() for r in results],
        "summary": {
            "average_time_ms": round(avg_time, 2),
            "average_time_formatted": format_time(avg_time),
            "average_cost_usd": round(avg_cost, 4),
            "success_rate_percent": round(success_rate, 1),
            "average_nodes": round(avg_nodes, 1),
            "average_edges": round(avg_edges, 1),
            "total_errors": total_errors,
            "successful_count": len(successful_results),
            "total_count": len(results),
        },
    }

    summary_path = os.path.join(output_dir, f"developer_benchmark_{timestamp}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n📁 Results saved to: {summary_path}")

    return summary


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Developer Benchmark - LLM building Astro constellations"
    )
    parser.add_argument(
        "--use-cases",
        nargs="+",
        default=["all"],
        help="Use cases to run (default: all). Options: investment_dd, competitive_intel, risk_assessment, product_launch, ma_screening",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model to use (defaults to LLM_MODEL env var or gpt-5-nano)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Directory to save results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress",
    )
    parser.add_argument(
        "--list-use-cases",
        action="store_true",
        help="List available use cases and exit",
    )

    args = parser.parse_args()

    if args.list_use_cases:
        print("Available use cases:")
        for name, prompt in USE_CASES.items():
            print(f"\n  {name}:")
            print(f"    {prompt.strip()[:200]}...")
        return

    model = args.model or os.getenv("LLM_MODEL", "gpt-5-nano")

    await run_developer_benchmark(
        use_cases=args.use_cases,
        model=model,
        output_dir=args.output_dir,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    asyncio.run(main())
