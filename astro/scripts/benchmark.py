#!/usr/bin/env python3
"""
Benchmark comparing multiple orchestration approaches:
1. Zero-shot LLM (single call)
2. Astro Constellation (multi-step DAG)
3. Multi Agent Research (LangGraph with dynamic planning)

Compares:
- Execution time
- Token usage (input/output)
- Cost
- Output quality (diff)

Usage:
    cd /Users/rishimeka/Documents/Code/astrix-labs/astro

    # =========================================================================
    # MARKET RESEARCH BENCHMARK (Original)
    # =========================================================================

    # Compare all three
    PYTHONPATH=. python scripts/benchmark.py --query "Can you do some company analysis on AirBnB?" --include-multi-agent

    # Just Astro vs Zero-shot
    PYTHONPATH=. python scripts/benchmark.py --query "Can you do some company analysis on AirBnB?"

    # With quality evaluation
    PYTHONPATH=. python scripts/benchmark.py --query "Can you do some company analysis on AirBnB?" --include-multi-agent --full-evaluation

    # =========================================================================
    # DUE DILIGENCE BENCHMARK (New - Tests Tool Scoping)
    # =========================================================================

    # Run full DD benchmark comparing all approaches (zero-shot, naive multi-agent, Astro)
    PYTHONPATH=. python scripts/benchmark.py --due-diligence --dd-all-approaches --dd-evaluate

    # Standard scenario (no conditional branches)
    PYTHONPATH=. python scripts/benchmark.py --due-diligence --dd-scenario standard --dd-company "Airbnb"

    # Regulated industry scenario (triggers regulatory deep-dive)
    PYTHONPATH=. python scripts/benchmark.py --due-diligence --dd-scenario regulated --dd-company "Pfizer"

    # Anomaly scenario (triggers forensic analyst)
    PYTHONPATH=. python scripts/benchmark.py --due-diligence --dd-scenario anomaly

    # Full scenario (triggers both conditional branches)
    PYTHONPATH=. python scripts/benchmark.py --due-diligence --dd-scenario full --dd-evaluate

    # Custom company
    PYTHONPATH=. python scripts/benchmark.py --due-diligence --dd-all-approaches --dd-company "Tesla" --dd-evaluate

The Due Diligence benchmark tests Astro's key differentiators:
- Tool scoping: Each analyst has access only to relevant probes
- Sub-directive composition: Shared analysis framework across workers
- Conditional branching: Regulatory deep-dive and forensic analysis paths
- Probe isolation as quality mechanism: Prevents cross-contamination
"""

import argparse
import asyncio
import difflib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# Pricing per 1M tokens (as of 2024 - update as needed)
PRICING = {
    "gpt-5-nano": {"input": 0.10, "output": 0.40},  # Default model for benchmarks
    "gpt-5-nano": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}


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
class QualityScore:
    """Quality assessment scores for an output."""
    completeness: float = 0.0  # 0-10: Does it cover all key aspects?
    structure: float = 0.0     # 0-10: Is it well-organized?
    actionability: float = 0.0 # 0-10: Are recommendations clear/useful?
    clarity: float = 0.0       # 0-10: Is it easy to understand?
    depth: float = 0.0         # 0-10: How thorough is the analysis?
    overall: float = 0.0       # 0-10: Overall quality
    reasoning: str = ""        # Explanation of scores

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completeness": self.completeness,
            "structure": self.structure,
            "actionability": self.actionability,
            "clarity": self.clarity,
            "depth": self.depth,
            "overall": self.overall,
            "reasoning": self.reasoning,
        }


@dataclass
class DueDiligenceMetrics:
    """Metrics specific to the Due Diligence benchmark."""
    analytical_independence: float = 0.0  # 0-10: Do analysts reach independent conclusions?
    cross_contamination_score: float = 0.0  # Count of scope violations
    tool_call_efficiency: float = 0.0  # Ratio of relevant to total tool calls
    conditional_path_accuracy: bool = False  # Did correct conditional branches trigger?
    output_consistency: float = 0.0  # 0-10: Are outputs consistently formatted?
    conflict_detection: float = 0.0  # 0-10: Does synthesis identify contradictions?
    probe_scope_violations: List[Dict[str, Any]] = field(default_factory=list)
    conditional_branches_triggered: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analytical_independence": self.analytical_independence,
            "cross_contamination_score": self.cross_contamination_score,
            "tool_call_efficiency": self.tool_call_efficiency,
            "conditional_path_accuracy": self.conditional_path_accuracy,
            "output_consistency": self.output_consistency,
            "conflict_detection": self.conflict_detection,
            "probe_scope_violations": self.probe_scope_violations[:10],
            "conditional_branches_triggered": self.conditional_branches_triggered,
            "reasoning": self.reasoning,
        }


@dataclass
class FactualAccuracy:
    """Factual accuracy assessment."""
    claims_identified: int = 0
    claims_verified: int = 0
    claims_unverifiable: int = 0
    claims_incorrect: int = 0
    accuracy_score: float = 0.0  # 0-100%
    key_claims: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims_identified": self.claims_identified,
            "claims_verified": self.claims_verified,
            "claims_unverifiable": self.claims_unverifiable,
            "claims_incorrect": self.claims_incorrect,
            "accuracy_score": self.accuracy_score,
            "key_claims": self.key_claims[:10],  # Limit to top 10
            "reasoning": self.reasoning,
        }


@dataclass
class BenchmarkResult:
    """Result from a benchmark run."""
    name: str
    query: str
    output: str
    duration_ms: float
    token_usage: TokenUsage
    cost_usd: float
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: Optional[QualityScore] = None
    factual_accuracy: Optional[FactualAccuracy] = None
    dd_metrics: Optional[DueDiligenceMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "query": self.query,
            "output": self.output[:1000] + "..." if len(self.output) > 1000 else self.output,
            "output_length": len(self.output),
            "duration_ms": self.duration_ms,
            "duration_seconds": round(self.duration_ms / 1000, 2),
            "token_usage": self.token_usage.to_dict(),
            "cost_usd": round(self.cost_usd, 4),
            "model": self.model,
            "metadata": self.metadata,
        }
        if self.quality_score:
            result["quality_score"] = self.quality_score.to_dict()
        if self.factual_accuracy:
            result["factual_accuracy"] = self.factual_accuracy.to_dict()
        if self.dd_metrics:
            result["dd_metrics"] = self.dd_metrics.to_dict()
        return result


# Due Diligence Benchmark Test Queries
DD_BENCHMARK_QUERIES = {
    "standard": {
        "query": "Due diligence on Airbnb",
        "company": "Airbnb",
        "expected_behavior": "Standard path (A,B,C,D → G → H). No conditional branches.",
        "expected_branches": [],
    },
    "regulated": {
        "query": "Due diligence on Pfizer",
        "company": "Pfizer",
        "expected_behavior": "Triggers regulatory deep dive (E) because pharma = heavily regulated",
        "expected_branches": ["regulatory_deep_dive"],
    },
    "anomaly": {
        "query": "Due diligence on Enron",  # Historical example
        "company": "Enron",
        "expected_behavior": "Triggers forensic analyst (F) when financial analyst flags anomalies",
        "expected_branches": ["forensic_analyst"],
    },
    "full": {
        "query": "Due diligence on a heavily regulated company with accounting concerns",
        "company": "Theranos",  # Historical example
        "expected_behavior": "Triggers BOTH regulatory deep dive (E) and forensic analyst (F)",
        "expected_branches": ["regulatory_deep_dive", "forensic_analyst"],
    },
}

# Probe scoping matrix for validation
PROBE_SCOPING_MATRIX = {
    "financial_analyst": ["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
    "sentiment_analyst": ["search_news", "get_social_sentiment", "get_analyst_ratings"],
    "regulatory_analyst": ["search_sec_filings", "search_legal_cases", "search_regulatory_filings"],
    "competitive_analyst": ["get_market_research", "search_news", "get_financial_data"],
    "regulatory_deep_dive": ["search_regulatory_filings", "search_legal_cases", "search_news", "search_sec_filings"],
    "forensic_analyst": ["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
    "risk_scorer": [],
    "final_synthesis": [],
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing."""
    pricing = PRICING.get(model, PRICING.get("gpt-5-nano", {"input": 0.10, "output": 0.40}))
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


async def evaluate_quality(output: str, query: str, model: str) -> QualityScore:
    """Evaluate output quality using LLM-as-judge."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return QualityScore(reasoning="API key not available")

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=SecretStr(api_key),
    )

    system_prompt = """You are an expert evaluator of investment research reports.
Evaluate the given output on these dimensions (score 0-10 each):

1. **Completeness** (0-10): Does it cover company overview, bull case, bear case, and investment thesis?
2. **Structure** (0-10): Is it well-organized with clear sections and formatting?
3. **Actionability** (0-10): Are recommendations specific and useful for decision-making?
4. **Clarity** (0-10): Is the writing clear, professional, and easy to understand?
5. **Depth** (0-10): How thorough is the analysis? Does it provide meaningful insights?
6. **Overall** (0-10): Overall quality of the analysis.

Respond in this exact JSON format:
{
    "completeness": <score>,
    "structure": <score>,
    "actionability": <score>,
    "clarity": <score>,
    "depth": <score>,
    "overall": <score>,
    "reasoning": "<brief 2-3 sentence explanation of scores>"
}"""

    user_message = f"""Query: {query}

Output to evaluate:
{output}

Provide your evaluation in JSON format."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        # Parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return QualityScore(
                completeness=float(data.get("completeness", 0)),
                structure=float(data.get("structure", 0)),
                actionability=float(data.get("actionability", 0)),
                clarity=float(data.get("clarity", 0)),
                depth=float(data.get("depth", 0)),
                overall=float(data.get("overall", 0)),
                reasoning=data.get("reasoning", ""),
            )
    except Exception as e:
        return QualityScore(reasoning=f"Error evaluating quality: {str(e)}")

    return QualityScore(reasoning="Could not parse evaluation response")


async def evaluate_dd_metrics(
    output: str,
    query: str,
    model: str,
    node_outputs: Optional[Dict[str, Any]] = None,
    expected_branches: Optional[List[str]] = None,
) -> DueDiligenceMetrics:
    """Evaluate Due Diligence specific metrics using LLM-as-judge."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return DueDiligenceMetrics(reasoning="API key not available")

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=SecretStr(api_key),
    )

    system_prompt = """You are an expert evaluator of investment due diligence reports.
Evaluate the given output on these dimensions specific to multi-analyst due diligence:

1. **Analytical Independence** (0-10): Do different analytical sections (financial, sentiment, regulatory, competitive)
   reach independent conclusions without cross-contamination? Look for:
   - Sentiment analysis that doesn't reference specific financial numbers
   - Financial analysis that doesn't speculate on narrative/perception
   - Regulatory analysis that focuses on facts from filings, not opinions

2. **Output Consistency** (0-10): Are all sections formatted consistently? Look for:
   - Consistent section headers
   - Consistent confidence level indicators
   - Consistent evidence citation format

3. **Conflict Detection** (0-10): Does the synthesis identify contradictions between analysts?
   - Are bull vs bear disagreements explicitly called out?
   - Are conflicting data points from different sources noted?

Respond in this exact JSON format:
{
    "analytical_independence": <score>,
    "output_consistency": <score>,
    "conflict_detection": <score>,
    "cross_contamination_examples": ["example 1", "example 2"],
    "reasoning": "<brief explanation of scores>"
}"""

    user_message = f"""Query: {query}

Due Diligence Report to evaluate:
{output}

Evaluate this report. Respond in JSON format."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        # Parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())

            # Check conditional branch accuracy
            conditional_accuracy = True
            triggered_branches = []
            if node_outputs:
                for node_id, output_data in node_outputs.items():
                    if node_id in ["regulatory_deep_dive", "forensic_analyst"]:
                        if output_data.get("status") == "completed":
                            triggered_branches.append(node_id)

                if expected_branches:
                    conditional_accuracy = set(triggered_branches) == set(expected_branches)

            return DueDiligenceMetrics(
                analytical_independence=float(data.get("analytical_independence", 0)),
                cross_contamination_score=len(data.get("cross_contamination_examples", [])),
                tool_call_efficiency=0.0,  # Calculated separately from tool call logs
                conditional_path_accuracy=conditional_accuracy,
                output_consistency=float(data.get("output_consistency", 0)),
                conflict_detection=float(data.get("conflict_detection", 0)),
                probe_scope_violations=[{"example": ex} for ex in data.get("cross_contamination_examples", [])],
                conditional_branches_triggered=triggered_branches,
                reasoning=data.get("reasoning", ""),
            )
    except Exception as e:
        return DueDiligenceMetrics(reasoning=f"Error evaluating DD metrics: {str(e)}")

    return DueDiligenceMetrics(reasoning="Could not parse evaluation response")


async def check_factual_accuracy(output: str, query: str, model: str) -> FactualAccuracy:
    """Check factual accuracy of claims in the output using LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return FactualAccuracy(reasoning="API key not available")

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=SecretStr(api_key),
    )

    system_prompt = """You are a fact-checker for investment research. Analyze the given output and:

1. Identify specific factual claims (company facts, statistics, events, partnerships, etc.)
2. Assess each claim's accuracy based on your knowledge (as of your training data)
3. Categorize claims as: VERIFIED (known to be true), INCORRECT (known to be false), or UNVERIFIABLE (cannot confirm)

Focus on concrete, verifiable facts, not opinions or predictions.

Respond in this exact JSON format:
{
    "claims": [
        {
            "claim": "<the specific claim>",
            "status": "VERIFIED|INCORRECT|UNVERIFIABLE",
            "explanation": "<brief explanation>"
        }
    ],
    "summary": {
        "total": <number>,
        "verified": <number>,
        "incorrect": <number>,
        "unverifiable": <number>
    },
    "accuracy_score": <0-100 percentage based on verified/(verified+incorrect)>,
    "reasoning": "<overall assessment of factual reliability>"
}

Identify at least 5-10 key factual claims if present."""

    user_message = f"""Query: {query}

Output to fact-check:
{output}

Identify and verify factual claims. Respond in JSON format."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        # Parse JSON from response - handle nested structure
        import re
        # Find the outermost JSON object
        json_match = re.search(r'\{(?:[^{}]|\{[^{}]*\})*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            summary = data.get("summary", {})
            claims = data.get("claims", [])

            return FactualAccuracy(
                claims_identified=summary.get("total", len(claims)),
                claims_verified=summary.get("verified", 0),
                claims_unverifiable=summary.get("unverifiable", 0),
                claims_incorrect=summary.get("incorrect", 0),
                accuracy_score=float(data.get("accuracy_score", 0)),
                key_claims=claims,
                reasoning=data.get("reasoning", ""),
            )
    except Exception as e:
        return FactualAccuracy(reasoning=f"Error checking accuracy: {str(e)}")

    return FactualAccuracy(reasoning="Could not parse fact-check response")


async def compare_outputs(
    zero_shot_output: str,
    astro_output: str,
    query: str,
    model: str,
) -> Dict[str, Any]:
    """Compare two outputs head-to-head using LLM-as-judge."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "API key not available"}

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=SecretStr(api_key),
    )

    system_prompt = """You are an expert evaluator comparing two investment research outputs.

Compare Output A (Zero-Shot) vs Output B (Astro Constellation) on these criteria:
1. **Information Quality**: Which provides more accurate, relevant information?
2. **Depth of Analysis**: Which goes deeper into bull/bear cases?
3. **Actionability**: Which provides clearer investment guidance?
4. **Professionalism**: Which is better formatted for professional use?
5. **Specificity**: Which includes more specific, concrete details?

Respond in this exact JSON format:
{
    "winner": "A|B|TIE",
    "scores": {
        "information_quality": {"A": <1-10>, "B": <1-10>},
        "depth_of_analysis": {"A": <1-10>, "B": <1-10>},
        "actionability": {"A": <1-10>, "B": <1-10>},
        "professionalism": {"A": <1-10>, "B": <1-10>},
        "specificity": {"A": <1-10>, "B": <1-10>}
    },
    "total_scores": {"A": <sum>, "B": <sum>},
    "reasoning": "<2-3 sentence explanation of why one is better>"
}"""

    user_message = f"""Query: {query}

=== OUTPUT A (Zero-Shot) ===
{zero_shot_output}

=== OUTPUT B (Astro Constellation) ===
{astro_output}

Compare these outputs. Respond in JSON format."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        import re
        json_match = re.search(r'\{(?:[^{}]|\{[^{}]*\})*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        return {"error": f"Error comparing outputs: {str(e)}"}

    return {"error": "Could not parse comparison response"}


class TokenTrackingLLM:
    """Wrapper around LLM that tracks token usage."""

    def __init__(self, llm, usage: TokenUsage):
        self._llm = llm
        self._usage = usage

    def invoke(self, messages, **kwargs):
        response = self._llm.invoke(messages, **kwargs)
        # Extract usage from response metadata
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "token_usage" in metadata:
                usage = metadata["token_usage"]
                self._usage.add(
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0)
                )
            elif "usage" in metadata:
                usage = metadata["usage"]
                self._usage.add(
                    usage.get("input_tokens", usage.get("prompt_tokens", 0)),
                    usage.get("output_tokens", usage.get("completion_tokens", 0))
                )
        return response

    def bind_tools(self, tools):
        """Wrap bind_tools to maintain tracking."""
        bound = self._llm.bind_tools(tools)
        return TokenTrackingLLM(bound, self._usage)

    def __getattr__(self, name):
        return getattr(self._llm, name)


MULTI_AGENT_PATH = "/Users/rishimeka/Documents/Code/Multi Agent Research Implementation"


async def run_multi_agent_research(query: str, model: str = None) -> BenchmarkResult:
    """Run a query through the Multi Agent Research system."""
    import sys

    print("\n" + "=" * 60)
    print("MULTI AGENT RESEARCH BENCHMARK")
    print("=" * 60)

    # Add Multi Agent Research to path
    if MULTI_AGENT_PATH not in sys.path:
        sys.path.insert(0, MULTI_AGENT_PATH)

    usage = TokenUsage()

    # Patch get_llm to track tokens
    def patched_get_llm(temperature: float = 0):
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        # Use the model from Multi Agent Research (gpt-5-nano) or override
        llm_model = model or os.getenv("LLM_MODEL", "gpt-5-nano")
        base_llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature,
            api_key=api_key,
        )
        return TokenTrackingLLM(base_llm, usage)

    # Monkey-patch the get_llm function in Multi Agent Research
    try:
        import utils as multi_agent_utils
        original_get_llm = multi_agent_utils.get_llm
        multi_agent_utils.get_llm = patched_get_llm
    except ImportError:
        print("Warning: Could not import Multi Agent Research utils")
        return BenchmarkResult(
            name="multi_agent_research",
            query=query,
            output="Error: Could not import Multi Agent Research",
            duration_ms=0,
            token_usage=usage,
            cost_usd=0,
            model=model or "unknown",
            metadata={"error": "Import failed"},
        )

    try:
        from models import AgentState
        from nodes.research_agent import research_graph

        print(f"Query: {query}")
        llm_model = model or os.getenv("LLM_MODEL", "gpt-5-nano")
        print(f"Model: {llm_model}")
        print("Running multi-agent research...")

        # Create initial state
        initial_state = AgentState(query=query)

        start_time = time.perf_counter()
        result = await research_graph.ainvoke(initial_state)
        end_time = time.perf_counter()

        # Extract results
        final_state = result if isinstance(result, AgentState) else AgentState(**result)
        duration_ms = (end_time - start_time) * 1000
        output = final_state.final_report or ""
        cost = calculate_cost(llm_model, usage.input_tokens, usage.output_tokens)

        # Collect metadata
        total_phases = sum(len(p.phases) for p in final_state.plan_history)
        total_workers = sum(
            len(phase.worker_tasks)
            for plan in final_state.plan_history
            for phase in plan.phases
        )

        print(f"Completed in {duration_ms:.0f}ms")
        print(f"Status: {final_state.status}")
        print(f"Planning iterations: {final_state.planning_iteration}")
        print(f"Total phases: {total_phases}")
        print(f"Total workers: {total_workers}")
        print(f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output")
        print(f"LLM calls: {usage.calls}")
        print(f"Cost: ${cost:.4f}")

        return BenchmarkResult(
            name="multi_agent_research",
            query=query,
            output=output,
            duration_ms=duration_ms,
            token_usage=usage,
            cost_usd=cost,
            model=llm_model,
            metadata={
                "status": final_state.status,
                "planning_iterations": final_state.planning_iteration,
                "total_phases": total_phases,
                "total_workers": total_workers,
                "errors": final_state.errors,
            },
        )

    except Exception as e:
        print(f"Error running Multi Agent Research: {e}")
        import traceback
        traceback.print_exc()
        return BenchmarkResult(
            name="multi_agent_research",
            query=query,
            output=f"Error: {str(e)}",
            duration_ms=0,
            token_usage=usage,
            cost_usd=0,
            model=model or "unknown",
            metadata={"error": str(e)},
        )
    finally:
        # Restore original get_llm
        try:
            multi_agent_utils.get_llm = original_get_llm
        except:
            pass
        # Remove from path
        if MULTI_AGENT_PATH in sys.path:
            sys.path.remove(MULTI_AGENT_PATH)


async def run_zero_shot(query: str, model: str) -> BenchmarkResult:
    """Run a zero-shot query directly to the LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    print("\n" + "=" * 60)
    print("ZERO-SHOT BENCHMARK")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    usage = TokenUsage()

    # Create LLM with token tracking
    base_llm = ChatOpenAI(
        model=model,
        temperature=0.7,
        api_key=SecretStr(api_key),
    )
    llm = TokenTrackingLLM(base_llm, usage)

    # Create a comprehensive zero-shot prompt
    system_prompt = """You are a senior investment analyst. Provide comprehensive company analysis including:

1. **Company Overview**: Brief description, industry, market position
2. **Bull Case**: Key growth catalysts, competitive advantages, positive trends
3. **Bear Case**: Key risks, competitive threats, concerns
4. **Investment Thesis**: Balanced recommendation with key monitoring points

Be thorough but concise. Support your analysis with reasoning."""

    user_message = f"""Please analyze the following company:

{query}

Provide a complete investment research report."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    print(f"Query: {query}")
    print(f"Model: {model}")
    print("Running zero-shot query...")

    start_time = time.perf_counter()
    response = llm.invoke(messages)
    end_time = time.perf_counter()

    duration_ms = (end_time - start_time) * 1000
    output = response.content if hasattr(response, "content") else str(response)
    cost = calculate_cost(model, usage.input_tokens, usage.output_tokens)

    print(f"Completed in {duration_ms:.0f}ms")
    print(f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output")
    print(f"Cost: ${cost:.4f}")

    return BenchmarkResult(
        name="zero_shot",
        query=query,
        output=output,
        duration_ms=duration_ms,
        token_usage=usage,
        cost_usd=cost,
        model=model,
    )


async def run_zero_shot_dd(query: str, company: str, model: str) -> BenchmarkResult:
    """Run a zero-shot due diligence query with all tools available.

    Single prompt with ALL 9 probes bound - tests if one smart call can match
    8 coordinated workers.
    """
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    print("\n" + "=" * 60)
    print("ZERO-SHOT DUE DILIGENCE BENCHMARK (ALL TOOLS)")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    usage = TokenUsage()

    # Create LLM with token tracking
    base_llm = ChatOpenAI(
        model=model,
        temperature=0.5,
        api_key=SecretStr(api_key),
    )
    llm = TokenTrackingLLM(base_llm, usage)

    # Bind ALL DD probes to the LLM
    from astro_backend_service.probes.registry import ProbeRegistry
    dd_probe_names = [
        "search_sec_filings", "get_financial_data", "search_earnings_transcripts",
        "search_news", "get_social_sentiment", "get_analyst_ratings",
        "search_legal_cases", "search_regulatory_filings", "get_market_research"
    ]

    all_probes = ProbeRegistry.all()
    probes = [p for p in all_probes if p.name in dd_probe_names]

    langchain_tools = []
    probe_map = {}
    for probe in probes:
        tool = StructuredTool.from_function(
            func=probe._callable,
            name=probe.name,
            description=probe.description,
        )
        langchain_tools.append(tool)
        probe_map[probe.name] = probe

    llm_with_tools = llm._llm.bind_tools(langchain_tools)

    print(f"Bound {len(langchain_tools)} tools to LLM")

    system_prompt = f"""You are a senior investment analyst conducting comprehensive due diligence on {company}.

You have access to 9 research tools. Use them to gather data, then produce a complete due diligence report.

## Your Task
1. Use the available tools to gather financial, sentiment, regulatory, and competitive data
2. Synthesize findings into a comprehensive due diligence report

## Required Report Sections
1. Executive Summary (3-5 sentences)
2. Investment Thesis (Bull case, Bear case, Key debate points)
3. Risk Assessment (Financial, Regulatory, Competitive, Sentiment - score 1-10 each)
4. Recommendation (Rating, Conviction, Key monitoring triggers)

## Guidelines
- Call multiple tools to gather comprehensive data
- Support all claims with evidence from tool results
- Be objective and balanced"""

    user_message = f"Conduct comprehensive due diligence on {company}. Use the available tools to gather data."

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    print(f"Query: {query}")
    print(f"Company: {company}")
    print(f"Model: {model}")
    print("Running zero-shot due diligence with tool calling...")

    start_time = time.perf_counter()

    tool_calls_made = []
    max_iterations = 10
    iterations = 0

    # Tool calling loop
    while iterations < max_iterations:
        iterations += 1
        response = llm_with_tools.invoke(messages)
        usage.add(
            response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
            response.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
        )

        if hasattr(response, "tool_calls") and response.tool_calls:
            messages.append(response)
            tool_messages = []

            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})

                try:
                    if tool_name in probe_map:
                        result = str(probe_map[tool_name].invoke(**tool_args))
                    else:
                        result = f"Tool '{tool_name}' not found"
                except Exception as e:
                    result = f"Error: {str(e)}"

                tool_calls_made.append({"tool": tool_name, "args": tool_args})
                tool_messages.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))

            messages.extend(tool_messages)
            print(f"  Iteration {iterations}: {len(response.tool_calls)} tool calls")
        else:
            # No more tool calls - got final response
            break

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    output = response.content if hasattr(response, "content") else str(response)
    cost = calculate_cost(model, usage.input_tokens, usage.output_tokens)

    print(f"Completed in {duration_ms:.0f}ms")
    print(f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output")
    print(f"Tool calls: {len(tool_calls_made)}")
    print(f"Cost: ${cost:.4f}")

    return BenchmarkResult(
        name="zero_shot_dd",
        query=query,
        output=output,
        duration_ms=duration_ms,
        token_usage=usage,
        cost_usd=cost,
        model=model,
        metadata={
            "company": company,
            "benchmark_type": "due_diligence",
            "approach": "zero_shot",
            "tool_calls": tool_calls_made,
            "iterations": iterations,
        },
    )


async def run_naive_multi_agent_dd(query: str, company: str, model: str) -> BenchmarkResult:
    """Run naive multi-agent due diligence WITHOUT probe scoping.

    All agents have access to ALL 9 tools - tests whether probe isolation matters.
    Key differences from Astro:
    - No probe scoping (every agent can call any tool)
    - No sub-directives (formatting instructions copy-pasted per agent)
    - No conditional branching (all agents always run)
    """
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    print("\n" + "=" * 60)
    print("NAIVE MULTI-AGENT DD (NO PROBE SCOPING)")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    usage = TokenUsage()

    # Bind ALL DD probes - every agent gets every tool
    from astro_backend_service.probes.registry import ProbeRegistry
    dd_probe_names = [
        "search_sec_filings", "get_financial_data", "search_earnings_transcripts",
        "search_news", "get_social_sentiment", "get_analyst_ratings",
        "search_legal_cases", "search_regulatory_filings", "get_market_research"
    ]

    all_probes = ProbeRegistry.all()
    probes = [p for p in all_probes if p.name in dd_probe_names]

    langchain_tools = []
    probe_map = {}
    for probe in probes:
        tool = StructuredTool.from_function(
            func=probe._callable,
            name=probe.name,
            description=probe.description,
        )
        langchain_tools.append(tool)
        probe_map[probe.name] = probe

    # Create LLM with ALL tools bound
    base_llm = ChatOpenAI(
        model=model,
        temperature=0.3,
        api_key=SecretStr(api_key),
    )
    llm_with_tools = base_llm.bind_tools(langchain_tools)

    print(f"Each agent has access to ALL {len(langchain_tools)} tools (no scoping)")

    # Copy-pasted formatting instructions (no sub-directives)
    formatting_instructions = """## Output Format
- State findings as numbered claims with confidence (HIGH/MEDIUM/LOW)
- Include evidence for each finding
- Flag any risks as MATERIAL/MODERATE/INFORMATIONAL
- Note limitations and data gaps"""

    # Define agents - each gets ALL tools (no scoping)
    agents = [
        {
            "name": "Financial Analyst",
            "role": "financial analyst",
            "task": f"Analyze {company}'s financial performance, metrics, valuation, and cash flow.",
            "focus": "Use financial tools to gather revenue, earnings, balance sheet data.",
        },
        {
            "name": "Sentiment Analyst",
            "role": "market sentiment analyst",
            "task": f"Analyze market sentiment, media narrative, and analyst opinions on {company}.",
            "focus": "Use news and sentiment tools to gauge market perception.",
        },
        {
            "name": "Regulatory Analyst",
            "role": "regulatory and compliance analyst",
            "task": f"Analyze {company}'s regulatory environment, legal exposure, and compliance.",
            "focus": "Use legal and regulatory tools to assess risk.",
        },
        {
            "name": "Competitive Analyst",
            "role": "competitive intelligence analyst",
            "task": f"Analyze {company}'s competitive positioning and market share.",
            "focus": "Use market research tools to map competitive landscape.",
        },
    ]

    print(f"Query: {query}")
    print(f"Company: {company}")
    print(f"Model: {model}")
    print("Running naive multi-agent (ALL tools available to ALL agents)...")

    start_time = time.perf_counter()
    all_tool_calls = []
    agent_outputs = []

    # Run each agent with tool calling
    for agent in agents:
        print(f"  Running {agent['name']}...")

        agent_prompt = f"""You are a {agent['role']} conducting due diligence on {company}.

You have access to ALL research tools. {agent['focus']}

Your task: {agent['task']}

{formatting_instructions}

Use the available tools to gather data, then provide your analysis."""

        messages = [
            SystemMessage(content=agent_prompt),
            HumanMessage(content=query),
        ]

        agent_tool_calls = []
        max_iterations = 5
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            response = llm_with_tools.invoke(messages)
            usage.add(
                response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
                response.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
            )

            if hasattr(response, "tool_calls") and response.tool_calls:
                messages.append(response)
                tool_messages = []

                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})

                    try:
                        result = str(probe_map[tool_name].invoke(**tool_args)) if tool_name in probe_map else f"Tool not found"
                    except Exception as e:
                        result = f"Error: {str(e)}"

                    agent_tool_calls.append({"agent": agent["name"], "tool": tool_name})
                    tool_messages.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))

                messages.extend(tool_messages)
            else:
                break

        content = response.content if hasattr(response, "content") else str(response)
        agent_outputs.append({
            "agent": agent["name"],
            "output": content,
            "tool_calls": agent_tool_calls,
        })
        all_tool_calls.extend(agent_tool_calls)
        print(f"    {len(agent_tool_calls)} tool calls")

    # Synthesis step (also gets all tools)
    print("  Running synthesis...")
    synthesis_prompt = f"""You are a senior analyst synthesizing due diligence findings for {company}.

## Agent Outputs

""" + "\n\n".join([f"### {ao['agent']}\n{ao['output']}" for ao in agent_outputs]) + f"""

{formatting_instructions}

## Your Task
Synthesize all findings into a comprehensive due diligence report with:
1. Executive Summary
2. Investment Thesis (Bull/Bear cases)
3. Risk Assessment (Financial, Regulatory, Competitive, Sentiment - score 1-10)
4. Information Conflicts between analysts
5. Recommendation (Rating, Conviction, Monitoring triggers)"""

    messages = [
        SystemMessage(content=synthesis_prompt),
        HumanMessage(content="Synthesize the due diligence findings into a final report."),
    ]

    response = llm_with_tools.invoke(messages)
    usage.add(
        response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
        response.response_metadata.get("token_usage", {}).get("completion_tokens", 0)
    )
    final_output = response.content if hasattr(response, "content") else str(response)

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    cost = calculate_cost(model, usage.input_tokens, usage.output_tokens)

    # Check for cross-contamination: did sentiment analyst use financial tools?
    cross_contamination = []
    for tc in all_tool_calls:
        if tc["agent"] == "Sentiment Analyst" and tc["tool"] in ["get_financial_data", "search_sec_filings", "search_earnings_transcripts"]:
            cross_contamination.append(tc)
        if tc["agent"] == "Financial Analyst" and tc["tool"] in ["search_news", "get_social_sentiment", "get_analyst_ratings"]:
            cross_contamination.append(tc)

    print(f"Completed in {duration_ms:.0f}ms")
    print(f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output")
    print(f"Total tool calls: {len(all_tool_calls)}")
    print(f"Cross-contamination instances: {len(cross_contamination)}")
    print(f"Cost: ${cost:.4f}")

    return BenchmarkResult(
        name="naive_multi_agent_dd",
        query=query,
        output=final_output,
        duration_ms=duration_ms,
        token_usage=usage,
        cost_usd=cost,
        model=model,
        metadata={
            "company": company,
            "benchmark_type": "due_diligence",
            "approach": "naive_multi_agent",
            "agents": [a["name"] for a in agents],
            "total_tool_calls": len(all_tool_calls),
            "tool_calls_by_agent": {ao["agent"]: len(ao["tool_calls"]) for ao in agent_outputs},
            "cross_contamination": cross_contamination,
            "cross_contamination_count": len(cross_contamination),
        },
    )


async def run_astro_dd_constellation(
    query: str,
    company: str,
    constellation_id: str = "const-dd-001",
) -> BenchmarkResult:
    """Run the Due Diligence constellation benchmark."""
    from astro_backend_service.foundry import Foundry
    from astro_backend_service.executor.runner import ConstellationRunner

    print("\n" + "=" * 60)
    print("ASTRO DUE DILIGENCE CONSTELLATION BENCHMARK")
    print("=" * 60)

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("MONGO_DB", "astro")

    # Patch get_llm to track tokens
    usage = TokenUsage()
    original_get_llm = None

    def patched_get_llm(temperature: float = 0):
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "gpt-5-nano")
        base_llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=SecretStr(api_key),
        )
        return TokenTrackingLLM(base_llm, usage)

    # Monkey-patch the get_llm function
    import astro_backend_service.llm_utils as llm_utils
    original_get_llm = llm_utils.get_llm
    llm_utils.get_llm = patched_get_llm

    try:
        # Initialize Foundry
        foundry = Foundry(MONGO_URI, DATABASE_NAME)
        await foundry.startup()

        # Create runner
        runner = ConstellationRunner(foundry)

        # Set up variables
        run_variables = {
            "company_name": company,
        }

        model = os.getenv("LLM_MODEL", "gpt-5-nano")

        print(f"Query: {query}")
        print(f"Company: {company}")
        print(f"Constellation: {constellation_id}")
        print(f"Model: {model}")
        print("Running due diligence constellation...")

        start_time = time.perf_counter()
        run = await runner.run(
            constellation_id=constellation_id,
            variables=run_variables,
            original_query=query,
        )
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000
        output = run.final_output or ""
        cost = calculate_cost(model, usage.input_tokens, usage.output_tokens)

        # Collect node execution info for DD metrics
        node_info = {}
        tool_calls_by_node = {}
        for node_id, node_output in run.node_outputs.items():
            # Convert tool calls to serializable dicts
            tc_list = []
            if hasattr(node_output, "tool_calls") and node_output.tool_calls:
                for tc in node_output.tool_calls:
                    tc_dict = {
                        "tool": tc.tool_name if hasattr(tc, "tool_name") else str(tc),
                        "arguments": tc.arguments if hasattr(tc, "arguments") else {},
                        "result": tc.result[:200] if hasattr(tc, "result") and tc.result else None,
                        "error": tc.error if hasattr(tc, "error") else None,
                    }
                    tc_list.append(tc_dict)

            node_info[node_id] = {
                "star_id": node_output.star_id,
                "status": node_output.status,
                "tool_calls": tc_list,
            }
            tool_calls_by_node[node_id] = tc_list

        # Check for probe scope violations
        scope_violations = []
        for node_id, tool_calls in tool_calls_by_node.items():
            if node_id in PROBE_SCOPING_MATRIX:
                allowed_probes = PROBE_SCOPING_MATRIX[node_id]
                for tc in tool_calls:
                    tool_name = tc.get("tool", "") if isinstance(tc, dict) else str(tc)
                    if tool_name and tool_name not in allowed_probes:
                        scope_violations.append({
                            "node": node_id,
                            "tool": tool_name,
                            "allowed": allowed_probes,
                        })

        print(f"Completed in {duration_ms:.0f}ms")
        print(f"Status: {run.status}")
        print(f"Nodes executed: {len(run.node_outputs)}")
        print(f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output")
        print(f"LLM calls: {usage.calls}")
        print(f"Cost: ${cost:.4f}")
        if scope_violations:
            print(f"WARNING: {len(scope_violations)} probe scope violations detected!")

        await foundry.shutdown()

        return BenchmarkResult(
            name="astro_dd_constellation",
            query=query,
            output=output,
            duration_ms=duration_ms,
            token_usage=usage,
            cost_usd=cost,
            model=model,
            metadata={
                "run_id": run.id,
                "constellation_id": constellation_id,
                "company": company,
                "status": run.status,
                "nodes_executed": len(run.node_outputs),
                "node_info": node_info,
                "benchmark_type": "due_diligence",
                "approach": "astro_constellation",
                "scope_violations": scope_violations,
            },
        )

    finally:
        # Restore original get_llm
        llm_utils.get_llm = original_get_llm


async def run_astro_constellation(
    query: str,
    constellation_id: str = "const-001",
    variables: Optional[Dict[str, Any]] = None,
) -> BenchmarkResult:
    """Run a query through the Astro constellation."""
    from astro_backend_service.foundry import Foundry
    from astro_backend_service.executor.runner import ConstellationRunner

    print("\n" + "=" * 60)
    print("ASTRO CONSTELLATION BENCHMARK")
    print("=" * 60)

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("MONGO_DB", "astro")

    # Patch get_llm to track tokens
    usage = TokenUsage()
    original_get_llm = None

    def patched_get_llm(temperature: float = 0):
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "gpt-5-nano")
        base_llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=SecretStr(api_key),
        )
        return TokenTrackingLLM(base_llm, usage)

    # Monkey-patch the get_llm function
    import astro_backend_service.llm_utils as llm_utils
    original_get_llm = llm_utils.get_llm
    llm_utils.get_llm = patched_get_llm

    try:
        # Initialize Foundry with URI strings (not persistence object)
        foundry = Foundry(MONGO_URI, DATABASE_NAME)
        await foundry.startup()

        # Create runner
        runner = ConstellationRunner(foundry)

        # Extract company name from query
        company_name = "AirBnB"  # Default
        if "airbnb" in query.lower():
            company_name = "AirBnB"
        elif "tesla" in query.lower():
            company_name = "Tesla"
        elif "apple" in query.lower():
            company_name = "Apple"

        # Set up variables
        run_variables = variables or {
            "company_name": company_name,
        }

        print(f"Query: {query}")
        print(f"Constellation: {constellation_id}")
        print(f"Variables: {run_variables}")

        model = os.getenv("LLM_MODEL", "gpt-5-nano")
        print(f"Model: {model}")
        print("Running constellation...")

        start_time = time.perf_counter()
        run = await runner.run(
            constellation_id=constellation_id,
            variables=run_variables,
            original_query=query,
        )
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000
        output = run.final_output or ""
        cost = calculate_cost(model, usage.input_tokens, usage.output_tokens)

        # Collect node execution info
        node_info = []
        for node_id, node_output in run.node_outputs.items():
            node_info.append({
                "node_id": node_id,
                "star_id": node_output.star_id,
                "status": node_output.status,
            })

        print(f"Completed in {duration_ms:.0f}ms")
        print(f"Status: {run.status}")
        print(f"Nodes executed: {len(run.node_outputs)}")
        print(f"Tokens: {usage.input_tokens} input, {usage.output_tokens} output")
        print(f"LLM calls: {usage.calls}")
        print(f"Cost: ${cost:.4f}")

        await foundry.shutdown()

        return BenchmarkResult(
            name="astro_constellation",
            query=query,
            output=output,
            duration_ms=duration_ms,
            token_usage=usage,
            cost_usd=cost,
            model=model,
            metadata={
                "run_id": run.id,
                "constellation_id": constellation_id,
                "status": run.status,
                "nodes_executed": len(run.node_outputs),
                "node_info": node_info,
            },
        )

    finally:
        # Restore original get_llm
        llm_utils.get_llm = original_get_llm


def generate_diff(zero_shot_output: str, astro_output: str) -> str:
    """Generate a readable diff between the two outputs."""
    zero_shot_lines = zero_shot_output.splitlines()
    astro_lines = astro_output.splitlines()

    diff = difflib.unified_diff(
        zero_shot_lines,
        astro_lines,
        fromfile="Zero-Shot",
        tofile="Astro Constellation",
        lineterm="",
    )

    return "\n".join(diff)


def print_comparison(
    zero_shot: BenchmarkResult,
    astro: BenchmarkResult,
    head_to_head: Optional[Dict[str, Any]] = None,
):
    """Print a detailed comparison of the two benchmarks."""
    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON")
    print("=" * 80)

    # Performance metrics
    print("\n📊 PERFORMANCE METRICS")
    print("-" * 40)
    print(f"{'Metric':<25} {'Zero-Shot':>15} {'Astro':>15} {'Diff':>15}")
    print("-" * 70)

    time_diff = astro.duration_ms - zero_shot.duration_ms
    time_pct = ((astro.duration_ms / zero_shot.duration_ms) - 1) * 100 if zero_shot.duration_ms > 0 else 0
    print(f"{'Duration (ms)':<25} {zero_shot.duration_ms:>15,.0f} {astro.duration_ms:>15,.0f} {time_diff:>+15,.0f}")

    token_diff = astro.token_usage.total_tokens - zero_shot.token_usage.total_tokens
    token_pct = ((astro.token_usage.total_tokens / zero_shot.token_usage.total_tokens) - 1) * 100 if zero_shot.token_usage.total_tokens > 0 else 0
    print(f"{'Total Tokens':<25} {zero_shot.token_usage.total_tokens:>15,} {astro.token_usage.total_tokens:>15,} {token_diff:>+15,}")

    print(f"{'Input Tokens':<25} {zero_shot.token_usage.input_tokens:>15,} {astro.token_usage.input_tokens:>15,}")
    print(f"{'Output Tokens':<25} {zero_shot.token_usage.output_tokens:>15,} {astro.token_usage.output_tokens:>15,}")

    print(f"{'LLM Calls':<25} {zero_shot.token_usage.calls:>15} {astro.token_usage.calls:>15}")

    cost_diff = astro.cost_usd - zero_shot.cost_usd
    print(f"{'Cost (USD)':<25} ${zero_shot.cost_usd:>14.4f} ${astro.cost_usd:>14.4f} ${cost_diff:>+14.4f}")

    print(f"{'Output Length (chars)':<25} {len(zero_shot.output):>15,} {len(astro.output):>15,}")

    # Quality scores if available
    if zero_shot.quality_score or astro.quality_score:
        print("\n⭐ QUALITY SCORES (0-10)")
        print("-" * 40)
        print(f"{'Dimension':<20} {'Zero-Shot':>12} {'Astro':>12} {'Winner':>12}")
        print("-" * 56)

        dimensions = ["completeness", "structure", "actionability", "clarity", "depth", "overall"]
        for dim in dimensions:
            zs_score = getattr(zero_shot.quality_score, dim, 0) if zero_shot.quality_score else 0
            astro_score = getattr(astro.quality_score, dim, 0) if astro.quality_score else 0
            winner = "Zero-Shot" if zs_score > astro_score else ("Astro" if astro_score > zs_score else "Tie")
            print(f"{dim.capitalize():<20} {zs_score:>12.1f} {astro_score:>12.1f} {winner:>12}")

        if zero_shot.quality_score and zero_shot.quality_score.reasoning:
            print(f"\nZero-Shot Assessment: {zero_shot.quality_score.reasoning}")
        if astro.quality_score and astro.quality_score.reasoning:
            print(f"Astro Assessment: {astro.quality_score.reasoning}")

    # Factual accuracy if available
    if zero_shot.factual_accuracy or astro.factual_accuracy:
        print("\n🔍 FACTUAL ACCURACY")
        print("-" * 40)
        print(f"{'Metric':<25} {'Zero-Shot':>15} {'Astro':>15}")
        print("-" * 55)

        zs_acc = zero_shot.factual_accuracy
        astro_acc = astro.factual_accuracy

        if zs_acc and astro_acc:
            print(f"{'Claims Identified':<25} {zs_acc.claims_identified:>15} {astro_acc.claims_identified:>15}")
            print(f"{'Claims Verified':<25} {zs_acc.claims_verified:>15} {astro_acc.claims_verified:>15}")
            print(f"{'Claims Unverifiable':<25} {zs_acc.claims_unverifiable:>15} {astro_acc.claims_unverifiable:>15}")
            print(f"{'Claims Incorrect':<25} {zs_acc.claims_incorrect:>15} {astro_acc.claims_incorrect:>15}")
            print(f"{'Accuracy Score':<25} {zs_acc.accuracy_score:>14.1f}% {astro_acc.accuracy_score:>14.1f}%")

            if zs_acc.reasoning:
                print(f"\nZero-Shot Accuracy: {zs_acc.reasoning}")
            if astro_acc.reasoning:
                print(f"Astro Accuracy: {astro_acc.reasoning}")

    # Head-to-head comparison
    if head_to_head and "error" not in head_to_head:
        print("\n⚔️ HEAD-TO-HEAD COMPARISON")
        print("-" * 40)

        winner = head_to_head.get("winner", "TIE")
        winner_name = "Zero-Shot" if winner == "A" else ("Astro" if winner == "B" else "TIE")
        print(f"🏆 WINNER: {winner_name}")

        scores = head_to_head.get("scores", {})
        if scores:
            print(f"\n{'Category':<25} {'Zero-Shot':>12} {'Astro':>12}")
            print("-" * 49)
            for category, vals in scores.items():
                cat_name = category.replace("_", " ").title()
                print(f"{cat_name:<25} {vals.get('A', 0):>12} {vals.get('B', 0):>12}")

        total = head_to_head.get("total_scores", {})
        if total:
            print("-" * 49)
            print(f"{'TOTAL':<25} {total.get('A', 0):>12} {total.get('B', 0):>12}")

        reasoning = head_to_head.get("reasoning", "")
        if reasoning:
            print(f"\n📋 Reasoning: {reasoning}")

    # Summary
    print("\n📈 PERFORMANCE SUMMARY")
    print("-" * 40)
    if time_pct > 0:
        print(f"⏱️  Astro is {time_pct:.1f}% SLOWER ({time_diff/1000:.1f}s longer)")
    else:
        print(f"⏱️  Astro is {abs(time_pct):.1f}% FASTER ({abs(time_diff)/1000:.1f}s shorter)")

    if token_pct > 0:
        print(f"🎫 Astro uses {token_pct:.1f}% MORE tokens ({token_diff:+,} tokens)")
    else:
        print(f"🎫 Astro uses {abs(token_pct):.1f}% FEWER tokens ({token_diff:+,} tokens)")

    if cost_diff > 0:
        print(f"💰 Astro costs ${cost_diff:.4f} MORE per query")
    else:
        print(f"💰 Astro costs ${abs(cost_diff):.4f} LESS per query")

    # Output samples
    print("\n📝 OUTPUT SAMPLES")
    print("-" * 40)

    print("\n🎯 ZERO-SHOT OUTPUT (first 500 chars):")
    print("-" * 30)
    print(zero_shot.output[:500] + "..." if len(zero_shot.output) > 500 else zero_shot.output)

    print("\n🌟 ASTRO OUTPUT (first 500 chars):")
    print("-" * 30)
    print(astro.output[:500] + "..." if len(astro.output) > 500 else astro.output)


def print_dd_comparison(results: Dict[str, BenchmarkResult]):
    """Print Due Diligence specific benchmark comparison."""
    print("\n" + "=" * 100)
    print("DUE DILIGENCE BENCHMARK COMPARISON")
    print("=" * 100)

    result_names = list(results.keys())
    result_list = list(results.values())

    # Performance metrics
    print("\n📊 PERFORMANCE METRICS")
    print("-" * 80)

    header = f"{'Metric':<25}"
    for name in result_names:
        header += f" {name.replace('_', ' ').title():>22}"
    print(header)
    print("-" * 80)

    metrics = [
        ("Duration (s)", lambda r: f"{r.duration_ms / 1000:.1f}"),
        ("Total Tokens", lambda r: f"{r.token_usage.total_tokens:,}"),
        ("LLM Calls", lambda r: f"{r.token_usage.calls}"),
        ("Cost (USD)", lambda r: f"${r.cost_usd:.4f}"),
        ("Output Length", lambda r: f"{len(r.output):,}"),
    ]

    for label, getter in metrics:
        row = f"{label:<25}"
        for r in result_list:
            row += f" {getter(r):>22}"
        print(row)

    # DD-specific metrics
    has_dd_metrics = any(r.dd_metrics for r in result_list)
    if has_dd_metrics:
        print("\n🎯 DUE DILIGENCE SPECIFIC METRICS")
        print("-" * 80)

        dd_metrics = [
            ("Analytical Independence", lambda r: f"{r.dd_metrics.analytical_independence:.1f}/10" if r.dd_metrics else "N/A"),
            ("Cross-Contamination", lambda r: f"{r.dd_metrics.cross_contamination_score:.0f} violations" if r.dd_metrics else "N/A"),
            ("Output Consistency", lambda r: f"{r.dd_metrics.output_consistency:.1f}/10" if r.dd_metrics else "N/A"),
            ("Conflict Detection", lambda r: f"{r.dd_metrics.conflict_detection:.1f}/10" if r.dd_metrics else "N/A"),
            ("Conditional Accuracy", lambda r: "✓" if r.dd_metrics and r.dd_metrics.conditional_path_accuracy else "✗" if r.dd_metrics else "N/A"),
        ]

        for label, getter in dd_metrics:
            row = f"{label:<25}"
            for r in result_list:
                row += f" {getter(r):>22}"
            print(row)

    # Quality scores
    has_quality = any(r.quality_score for r in result_list)
    if has_quality:
        print("\n⭐ QUALITY SCORES (0-10)")
        print("-" * 80)

        dimensions = ["completeness", "structure", "actionability", "depth", "overall"]
        for dim in dimensions:
            row = f"{dim.capitalize():<25}"
            for r in result_list:
                score = getattr(r.quality_score, dim, 0) if r.quality_score else 0
                row += f" {score:>22.1f}"
            print(row)

    # Summary with winner determination
    print("\n🏆 SUMMARY")
    print("-" * 80)

    # Find best in each category
    if has_quality:
        best_quality = max(result_list, key=lambda r: r.quality_score.overall if r.quality_score else 0)
    fastest = min(result_list, key=lambda r: r.duration_ms)
    cheapest = min(result_list, key=lambda r: r.cost_usd)
    if has_dd_metrics:
        best_independence = max(result_list, key=lambda r: r.dd_metrics.analytical_independence if r.dd_metrics else 0)
        least_contamination = min(result_list, key=lambda r: r.dd_metrics.cross_contamination_score if r.dd_metrics else float('inf'))

    for name, r in results.items():
        badges = []
        if r == fastest:
            badges.append("⚡ Fastest")
        if r == cheapest:
            badges.append("💰 Cheapest")
        if has_quality and r == best_quality:
            badges.append("⭐ Best Quality")
        if has_dd_metrics and r == best_independence:
            badges.append("🎯 Best Independence")
        if has_dd_metrics and r == least_contamination:
            badges.append("🛡️ Least Contamination")

        badge_str = " | ".join(badges) if badges else ""
        print(f"{name.replace('_', ' ').title():>25}: {badge_str}")

    # Hypothesis validation
    if has_dd_metrics:
        print("\n📋 HYPOTHESIS VALIDATION")
        print("-" * 80)

        astro = results.get("astro_dd_constellation")
        naive = results.get("naive_multi_agent_dd")
        zero_shot = results.get("zero_shot_dd")

        if astro and astro.dd_metrics:
            print(f"\n1. Probe Isolation Test:")
            if naive and naive.dd_metrics:
                if astro.dd_metrics.analytical_independence > naive.dd_metrics.analytical_independence:
                    print(f"   ✓ Astro ({astro.dd_metrics.analytical_independence:.1f}) beats Naive ({naive.dd_metrics.analytical_independence:.1f}) on analytical independence")
                else:
                    print(f"   ✗ Naive matches or beats Astro on analytical independence - probe scoping may not matter")

            print(f"\n2. Cross-Contamination Test:")
            if naive and naive.dd_metrics:
                if astro.dd_metrics.cross_contamination_score < naive.dd_metrics.cross_contamination_score:
                    print(f"   ✓ Astro ({astro.dd_metrics.cross_contamination_score}) has fewer scope violations than Naive ({naive.dd_metrics.cross_contamination_score})")
                else:
                    print(f"   ✗ Scope violations are similar - isolation thesis may be wrong")

            print(f"\n3. Quality vs Cost Trade-off:")
            if astro.quality_score and zero_shot and zero_shot.quality_score:
                quality_diff = astro.quality_score.overall - zero_shot.quality_score.overall
                cost_ratio = astro.cost_usd / zero_shot.cost_usd if zero_shot.cost_usd > 0 else float('inf')
                if quality_diff > 0 and cost_ratio < 5:
                    print(f"   ✓ Astro is {quality_diff:.1f} points better at {cost_ratio:.1f}x cost - justified")
                elif quality_diff <= 0:
                    print(f"   ✗ Zero-shot matches quality - orchestration may not be needed")
                else:
                    print(f"   ? {quality_diff:.1f} points better at {cost_ratio:.1f}x cost - value judgment required")


def print_multi_comparison(
    results: Dict[str, BenchmarkResult],
    head_to_head: Optional[Dict[str, Any]] = None,
):
    """Print comparison of multiple benchmark results."""
    print("\n" + "=" * 100)
    print("BENCHMARK COMPARISON")
    print("=" * 100)

    result_names = list(results.keys())
    result_list = list(results.values())

    # Performance metrics table
    print("\n📊 PERFORMANCE METRICS")
    print("-" * 80)

    # Header
    header = f"{'Metric':<25}"
    for name in result_names:
        header += f" {name.replace('_', ' ').title():>18}"
    print(header)
    print("-" * 80)

    # Duration
    row = f"{'Duration (ms)':<25}"
    for r in result_list:
        row += f" {r.duration_ms:>18,.0f}"
    print(row)

    # Total tokens
    row = f"{'Total Tokens':<25}"
    for r in result_list:
        row += f" {r.token_usage.total_tokens:>18,}"
    print(row)

    # Input tokens
    row = f"{'Input Tokens':<25}"
    for r in result_list:
        row += f" {r.token_usage.input_tokens:>18,}"
    print(row)

    # Output tokens
    row = f"{'Output Tokens':<25}"
    for r in result_list:
        row += f" {r.token_usage.output_tokens:>18,}"
    print(row)

    # LLM calls
    row = f"{'LLM Calls':<25}"
    for r in result_list:
        row += f" {r.token_usage.calls:>18}"
    print(row)

    # Cost
    row = f"{'Cost (USD)':<25}"
    for r in result_list:
        row += f" ${r.cost_usd:>17.4f}"
    print(row)

    # Output length
    row = f"{'Output Length (chars)':<25}"
    for r in result_list:
        row += f" {len(r.output):>18,}"
    print(row)

    # Quality scores if available
    has_quality = any(r.quality_score for r in result_list)
    if has_quality:
        print("\n⭐ QUALITY SCORES (0-10)")
        print("-" * 80)

        header = f"{'Dimension':<25}"
        for name in result_names:
            header += f" {name.replace('_', ' ').title():>18}"
        print(header)
        print("-" * 80)

        dimensions = ["completeness", "structure", "actionability", "clarity", "depth", "overall"]
        for dim in dimensions:
            row = f"{dim.capitalize():<25}"
            for r in result_list:
                score = getattr(r.quality_score, dim, 0) if r.quality_score else 0
                row += f" {score:>18.1f}"
            print(row)

    # Factual accuracy if available
    has_accuracy = any(r.factual_accuracy for r in result_list)
    if has_accuracy:
        print("\n🔍 FACTUAL ACCURACY")
        print("-" * 80)

        header = f"{'Metric':<25}"
        for name in result_names:
            header += f" {name.replace('_', ' ').title():>18}"
        print(header)
        print("-" * 80)

        metrics = [
            ("Claims Identified", "claims_identified"),
            ("Claims Verified", "claims_verified"),
            ("Claims Unverifiable", "claims_unverifiable"),
            ("Claims Incorrect", "claims_incorrect"),
            ("Accuracy Score", "accuracy_score"),
        ]
        for label, attr in metrics:
            row = f"{label:<25}"
            for r in result_list:
                val = getattr(r.factual_accuracy, attr, 0) if r.factual_accuracy else 0
                if attr == "accuracy_score":
                    row += f" {val:>17.1f}%"
                else:
                    row += f" {val:>18}"
            print(row)

    # Head-to-head comparisons
    if head_to_head:
        print("\n⚔️ HEAD-TO-HEAD COMPARISONS")
        print("-" * 80)
        for comparison_key, comparison in head_to_head.items():
            if "error" in comparison:
                continue
            parts = comparison_key.split("_vs_")
            name_a, name_b = parts[0].replace("_", " ").title(), parts[1].replace("_", " ").title()
            winner = comparison.get("winner", "TIE")
            winner_name = name_a if winner == "A" else (name_b if winner == "B" else "TIE")
            print(f"\n{name_a} vs {name_b}: Winner = {winner_name}")
            if comparison.get("total_scores"):
                print(f"  Scores: {name_a}={comparison['total_scores'].get('A', 0)}, {name_b}={comparison['total_scores'].get('B', 0)}")
            if comparison.get("reasoning"):
                print(f"  Reasoning: {comparison['reasoning'][:200]}...")

    # Summary
    print("\n📈 SUMMARY")
    print("-" * 80)

    # Find fastest/cheapest/best quality
    fastest = min(result_list, key=lambda r: r.duration_ms)
    cheapest = min(result_list, key=lambda r: r.cost_usd)
    if has_quality:
        best_quality = max(result_list, key=lambda r: r.quality_score.overall if r.quality_score else 0)

    for name, r in results.items():
        badges = []
        if r == fastest:
            badges.append("⚡ Fastest")
        if r == cheapest:
            badges.append("💰 Cheapest")
        if has_quality and r == best_quality:
            badges.append("⭐ Best Quality")
        badge_str = " | ".join(badges) if badges else ""
        print(f"{name.replace('_', ' ').title():>20}: {r.duration_ms/1000:.1f}s, ${r.cost_usd:.4f}, {r.token_usage.total_tokens:,} tokens {badge_str}")

    # Output samples
    print("\n📝 OUTPUT SAMPLES (first 300 chars each)")
    print("-" * 80)
    for name, r in results.items():
        print(f"\n🔹 {name.replace('_', ' ').upper()}:")
        print(r.output[:300] + "..." if len(r.output) > 300 else r.output)


def save_multi_results(
    results: Dict[str, BenchmarkResult],
    output_dir: str = "benchmark_results",
    head_to_head: Optional[Dict[str, Any]] = None,
):
    """Save multiple benchmark results to files."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Get query from first result
    first_result = list(results.values())[0]

    # Save summary JSON
    summary = {
        "timestamp": timestamp,
        "query": first_result.query,
        "results": {name: r.to_dict() for name, r in results.items()},
    }

    if head_to_head:
        summary["head_to_head"] = head_to_head

    summary_path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n📁 Summary saved to: {summary_path}")

    # Save individual outputs
    for name, result in results.items():
        output_path = os.path.join(output_dir, f"{name}_{timestamp}.txt")
        with open(output_path, "w") as f:
            f.write(result.output)
        print(f"📁 {name} output saved to: {output_path}")

    return summary_path


def save_results(
    zero_shot: BenchmarkResult,
    astro: BenchmarkResult,
    output_dir: str = "benchmark_results",
    head_to_head: Optional[Dict[str, Any]] = None,
):
    """Save benchmark results to files (legacy two-way comparison)."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save summary JSON
    summary = {
        "timestamp": timestamp,
        "query": zero_shot.query,
        "zero_shot": zero_shot.to_dict(),
        "astro": astro.to_dict(),
        "comparison": {
            "duration_diff_ms": astro.duration_ms - zero_shot.duration_ms,
            "token_diff": astro.token_usage.total_tokens - zero_shot.token_usage.total_tokens,
            "cost_diff_usd": astro.cost_usd - zero_shot.cost_usd,
        },
    }

    if head_to_head:
        summary["head_to_head"] = head_to_head

    summary_path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n📁 Summary saved to: {summary_path}")

    # Save full outputs
    zero_shot_path = os.path.join(output_dir, f"zero_shot_{timestamp}.txt")
    with open(zero_shot_path, "w") as f:
        f.write(zero_shot.output)
    print(f"📁 Zero-shot output saved to: {zero_shot_path}")

    astro_path = os.path.join(output_dir, f"astro_{timestamp}.txt")
    with open(astro_path, "w") as f:
        f.write(astro.output)
    print(f"📁 Astro output saved to: {astro_path}")

    # Save diff
    diff = generate_diff(zero_shot.output, astro.output)
    diff_path = os.path.join(output_dir, f"diff_{timestamp}.txt")
    with open(diff_path, "w") as f:
        f.write(diff)
    print(f"📁 Diff saved to: {diff_path}")

    return summary_path


async def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Astro constellation vs zero-shot LLM"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="Can you do some company analysis on AirBnB?",
        help="Query to benchmark",
    )
    parser.add_argument(
        "--constellation",
        type=str,
        default="const-001",
        help="Constellation ID to use",
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
        "--zero-shot-only",
        action="store_true",
        help="Run only the zero-shot benchmark",
    )
    parser.add_argument(
        "--astro-only",
        action="store_true",
        help="Run only the Astro benchmark",
    )
    parser.add_argument(
        "--evaluate-quality",
        action="store_true",
        help="Run quality scoring on outputs (adds LLM calls)",
    )
    parser.add_argument(
        "--check-facts",
        action="store_true",
        help="Run factual accuracy checks on outputs (adds LLM calls)",
    )
    parser.add_argument(
        "--full-evaluation",
        action="store_true",
        help="Run both quality scoring and fact checking",
    )
    parser.add_argument(
        "--include-multi-agent",
        action="store_true",
        help="Include Multi Agent Research in the benchmark",
    )
    parser.add_argument(
        "--multi-agent-only",
        action="store_true",
        help="Run only the Multi Agent Research benchmark",
    )
    # Due Diligence Benchmark Arguments
    parser.add_argument(
        "--due-diligence",
        action="store_true",
        help="Run the Due Diligence benchmark (tests tool-scoping, conditional branching)",
    )
    parser.add_argument(
        "--dd-scenario",
        type=str,
        choices=["standard", "regulated", "anomaly", "full"],
        default="standard",
        help="Due Diligence scenario: standard (no conditionals), regulated (triggers deep-dive), anomaly (triggers forensic), full (both)",
    )
    parser.add_argument(
        "--dd-company",
        type=str,
        default=None,
        help="Company name for due diligence (overrides scenario default)",
    )
    parser.add_argument(
        "--dd-all-approaches",
        action="store_true",
        help="Run all three DD approaches: zero-shot, naive multi-agent, and Astro constellation",
    )
    parser.add_argument(
        "--dd-evaluate",
        action="store_true",
        help="Run DD-specific evaluations (analytical independence, cross-contamination, etc.)",
    )

    args = parser.parse_args()

    # --full-evaluation enables both
    if args.full_evaluation:
        args.evaluate_quality = True
        args.check_facts = True

    # --multi-agent-only implies include-multi-agent
    if args.multi_agent_only:
        args.include_multi_agent = True

    # --dd-all-approaches enables DD mode
    if args.dd_all_approaches:
        args.due_diligence = True

    model = args.model or os.getenv("LLM_MODEL", "gpt-5-nano")

    # =========================================================================
    # DUE DILIGENCE BENCHMARK MODE
    # =========================================================================
    if args.due_diligence:
        print("\n" + "🔍" * 30)
        print("DUE DILIGENCE BENCHMARK")
        print("🔍" * 30)

        # Get scenario details
        scenario = DD_BENCHMARK_QUERIES.get(args.dd_scenario, DD_BENCHMARK_QUERIES["standard"])
        company = args.dd_company or scenario["company"]
        query = f"Due diligence on {company}"
        expected_branches = scenario["expected_branches"]

        print(f"\nScenario: {args.dd_scenario}")
        print(f"Company: {company}")
        print(f"Query: {query}")
        print(f"Expected behavior: {scenario['expected_behavior']}")
        print(f"Model: {model}")

        dd_results = {}

        if args.dd_all_approaches:
            print("\nRunning all three approaches for comparison...")

            # 1. Zero-shot
            dd_results["zero_shot_dd"] = await run_zero_shot_dd(query, company, model)

            # 2. Naive Multi-Agent (no probe scoping)
            dd_results["naive_multi_agent_dd"] = await run_naive_multi_agent_dd(query, company, model)

            # 3. Astro Constellation (with probe scoping)
            dd_results["astro_dd_constellation"] = await run_astro_dd_constellation(
                query, company, constellation_id="const-dd-001"
            )
        else:
            # Just run Astro constellation
            dd_results["astro_dd_constellation"] = await run_astro_dd_constellation(
                query, company, constellation_id="const-dd-001"
            )

        # Run evaluations
        if args.dd_evaluate or args.evaluate_quality:
            print("\n" + "=" * 60)
            print("RUNNING DD EVALUATIONS")
            print("=" * 60)

            for name, result in dd_results.items():
                print(f"\n  Evaluating {name}...")

                # Quality score
                print(f"    - Quality scoring...")
                result.quality_score = await evaluate_quality(
                    result.output, result.query, model
                )

                # DD-specific metrics
                print(f"    - DD metrics...")
                node_outputs = result.metadata.get("node_info", {})
                result.dd_metrics = await evaluate_dd_metrics(
                    result.output,
                    result.query,
                    model,
                    node_outputs=node_outputs,
                    expected_branches=expected_branches,
                )

        # Print DD comparison
        print_dd_comparison(dd_results)

        # Save results
        save_multi_results(dd_results, args.output_dir)

        return

    # =========================================================================
    # ORIGINAL BENCHMARK MODE (Market Research)
    # =========================================================================
    print("\n" + "🚀" * 30)
    print("ORCHESTRATION BENCHMARK")
    print("🚀" * 30)
    print(f"\nQuery: {args.query}")
    print(f"Model: {model}")
    if args.include_multi_agent:
        print("Including: Zero-Shot, Astro, Multi Agent Research")
    else:
        print("Including: Zero-Shot, Astro")

    zero_shot_result = None
    astro_result = None
    multi_agent_result = None

    if not args.astro_only and not args.multi_agent_only:
        zero_shot_result = await run_zero_shot(args.query, model)

    if not args.zero_shot_only and not args.multi_agent_only:
        astro_result = await run_astro_constellation(
            args.query,
            constellation_id=args.constellation,
        )

    if args.include_multi_agent:
        multi_agent_result = await run_multi_agent_research(args.query, model)

    # Collect all results
    all_results = {
        "zero_shot": zero_shot_result,
        "astro": astro_result,
        "multi_agent": multi_agent_result,
    }
    active_results = {k: v for k, v in all_results.items() if v is not None}

    # Run quality evaluations if requested
    if args.evaluate_quality or args.check_facts:
        print("\n" + "=" * 60)
        print("RUNNING QUALITY EVALUATIONS")
        print("=" * 60)

    if args.evaluate_quality:
        print("\n📊 Evaluating output quality...")
        for name, result in active_results.items():
            print(f"  Scoring {name} output...")
            result.quality_score = await evaluate_quality(
                result.output, result.query, model
            )

    if args.check_facts:
        print("\n🔍 Checking factual accuracy...")
        for name, result in active_results.items():
            print(f"  Fact-checking {name} output...")
            result.factual_accuracy = await check_factual_accuracy(
                result.output, result.query, model
            )

    # Head-to-head comparison (pairwise for all combinations)
    head_to_head = {}
    if len(active_results) >= 2 and (args.evaluate_quality or args.check_facts):
        print("\n⚔️ Running head-to-head comparisons...")
        result_items = list(active_results.items())
        for i in range(len(result_items)):
            for j in range(i + 1, len(result_items)):
                name_a, result_a = result_items[i]
                name_b, result_b = result_items[j]
                comparison_key = f"{name_a}_vs_{name_b}"
                print(f"  Comparing {name_a} vs {name_b}...")
                head_to_head[comparison_key] = await compare_outputs(
                    result_a.output,
                    result_b.output,
                    result_a.query,
                    model,
                )

    # Print and save results
    if len(active_results) >= 2:
        print_multi_comparison(active_results, head_to_head)
        save_multi_results(active_results, args.output_dir, head_to_head)
    elif len(active_results) == 1:
        name, result = list(active_results.items())[0]
        print(f"\n📊 {name.upper()} RESULTS")
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
