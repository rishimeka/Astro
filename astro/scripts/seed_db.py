#!/usr/bin/env python3
"""
Seed MongoDB with sample data for development.

Usage:
    cd /Users/rishimeka/Documents/Code/astrix-labs/astro
    PYTHONPATH=. python scripts/seed_db.py

Requires MongoDB running locally on default port (27017).
"""

import asyncio
import os

from astro_backend_service.foundry.persistence import FoundryPersistence
from astro_backend_service.models import (
    Directive,
    TemplateVariable,
    Constellation,
    StartNode,
    EndNode,
    StarNode,
    Edge,
    Position,
)
from astro_backend_service.models.stars import (
    WorkerStar,
    PlanningStar,
    EvalStar,
    SynthesisStar,
    ExecutionStar,
    DocExStar,
)


# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGO_DB", "astro")


# ============================================================================
# Sample Directives
# ============================================================================

DIRECTIVES = [
    Directive(
        id="dir-001",
        name="Financial Analysis",
        description="Comprehensive financial analysis directive for PE due diligence",
        content="""## Role
You are a financial analyst specializing in private equity due diligence with expertise in financial statement analysis, valuation, and investment memo preparation.

## Task Spec
Analyze financial documents for @variable:company_name for fiscal year @variable:fiscal_year and produce a structured due diligence report.

**Expected Output Format:**
- Executive Summary (2-3 paragraphs)
- Key Metrics Table (Revenue, EBITDA, margins, growth rates)
- Detailed Analysis by Section
- Risk Factors and Red Flags
- Investment Recommendation

**Success Criteria:**
- All key financial metrics extracted and validated
- Year-over-year trends identified
- Material risks flagged with supporting evidence
- Output suitable for investment committee review

## Context
This analysis supports PE investment decisions. Prior outputs from document ingestion provide the raw financial data. Focus on metrics relevant to LBO modeling and value creation opportunities.

## Constraints
- Only analyze data from provided documents; do not fabricate figures
- Limit analysis to the specified fiscal year and two prior years for trends
- Do not make buy/sell recommendations; present findings objectively
- Maximum output: 2000 words

## Tools
- @probe:extract_financial_metrics — Extract structured financial data from documents
- @probe:summarize_document — Generate summaries of lengthy sections

## Error Handling
- If key financial statements are missing, flag as "Incomplete Data" and list what's missing
- If figures are ambiguous or conflicting, report both values with source references
- If unable to calculate a metric, explain why and suggest alternative approaches""",
        probe_ids=["extract_financial_metrics", "summarize_document"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Name of the target company",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="fiscal_year",
                description="Fiscal year to analyze",
                required=True,
                default="2024",
                ui_hint="select",
                ui_options={"options": ["2022", "2023", "2024"]},
                used_by=[],
            ),
        ],
        metadata={
            "version": "2.0",
            "author": "system",
            "tags": ["finance", "due-diligence", "pe"],
        },
    ),
    Directive(
        id="dir-002",
        name="Market Research",
        description="Deep market research and competitive analysis",
        content="""## Role
You are a market research analyst with expertise in competitive intelligence, industry analysis, and strategic consulting.

## Task Spec
Conduct comprehensive market analysis for the @variable:industry industry.

**Expected Output Format:**
1. Market Overview (size, growth rate, key segments)
2. Competitive Landscape (top 5-10 players with market share)
3. Industry Dynamics (Porter's Five Forces analysis)
4. Regulatory Environment Summary
5. Key Trends and Outlook

**Success Criteria:**
- Market size quantified with credible sources
- At least 5 key competitors profiled
- Clear identification of industry tailwinds/headwinds
- Actionable insights for strategic positioning

## Context
This research informs investment thesis development and competitive positioning analysis. Output will be used alongside financial due diligence.

## Constraints
- Use only provided source documents and reference materials
- Do not speculate on future M&A activity
- Focus on the primary geographic market unless otherwise specified
- Maximum output: 1500 words

## Tools
- @probe:analyze_market_trends — Gather and structure market intelligence data

## Error Handling
- If market size data is unavailable, provide range estimates with methodology
- If competitor information is limited, note data gaps explicitly
- For emerging markets with sparse data, flag uncertainty levels""",
        probe_ids=["analyze_market_trends"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="industry",
                description="Target industry for research",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={"version": "2.0", "tags": ["research", "market", "competitive"]},
    ),
    Directive(
        id="dir-003",
        name="Document Summary",
        description="Generate executive summaries from lengthy documents",
        content="""## Role
You are an executive communications specialist skilled at distilling complex documents into clear, actionable summaries for senior leadership.

## Task Spec
Generate a concise executive summary of the provided document.

**Expected Output Format:**
- One-paragraph overview
- Key Findings (bullet points)
- Action Items (if any)
- Risks/Concerns (if any)
- Recommended Next Steps

**Success Criteria:**
- Summary captures all material points from source
- No longer than @variable:max_length words
- Suitable for C-suite audience with limited time
- Self-contained (reader needs no additional context)

## Context
Summaries are used for rapid decision-making by executives who may not read the full document. Prioritize clarity and actionability over comprehensiveness.

## Constraints
- Do not introduce information not present in the source document
- Maintain neutral tone; avoid editorializing
- Preserve critical nuances even when condensing
- Maximum length: @variable:max_length words

## Tools
- @probe:summarize_document — Extract and condense key points from documents

## Error Handling
- If document is too short to summarize, return it with minimal restructuring
- If document contains conflicting information, note the discrepancy
- If document is corrupted or unreadable, report failure with specifics""",
        probe_ids=["summarize_document"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="max_length",
                description="Maximum summary length in words",
                required=False,
                default="500",
                ui_hint="number",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={"version": "2.0", "tags": ["summary", "documents"]},
    ),
    Directive(
        id="dir-004",
        name="Risk Assessment",
        description="Evaluate and categorize business risks",
        content="""## Role
You are a risk management consultant with expertise in enterprise risk assessment, due diligence, and regulatory compliance.

## Task Spec
Conduct a comprehensive risk assessment for @variable:entity_name.

**Expected Output Format:**
| Risk Category | Risk Description | Severity | Likelihood | Mitigation |
|---------------|------------------|----------|------------|------------|
| Financial     | ...              | H/M/L    | H/M/L      | ...        |

Plus narrative analysis for each high-severity risk.

**Success Criteria:**
- All five risk categories addressed (Financial, Operational, Market, Regulatory, Technology)
- Each risk rated with clear rationale
- Mitigation recommendations are actionable
- No material risks overlooked from source documents

## Context
This assessment supports investment decision-making and post-acquisition planning. Findings inform deal structuring and 100-day plans.

## Constraints
- Base all findings on provided documents; do not assume undisclosed risks
- Rate risks relative to typical industry baseline
- Focus on risks material to enterprise value
- Do not provide legal advice

## Tools
- @probe:extract_entities — Identify risk factors, parties, and obligations from documents

## Error Handling
- If a risk category has no identified risks, explicitly state "No material risks identified"
- If risk severity is ambiguous, default to higher rating and note uncertainty
- If documents lack sufficient detail for assessment, list information gaps""",
        probe_ids=["extract_entities"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="entity_name",
                description="Entity to assess",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "version": "2.0",
            "category": "compliance",
            "tags": ["risk", "compliance", "due-diligence"],
        },
    ),
    Directive(
        id="dir-005",
        name="Entity Extraction",
        description="Extract and classify named entities from unstructured text",
        content="""## Role
You are an NLP specialist focused on named entity recognition and information extraction from unstructured business documents.

## Task Spec
Extract and classify all named entities from the provided text.

**Expected Output Format:**
```json
{
  "entities": [
    {
      "text": "Acme Corp",
      "type": "ORGANIZATION",
      "confidence": 0.95,
      "context": "acquiring party in merger"
    }
  ],
  "summary": {
    "organizations": 12,
    "people": 8,
    "locations": 3,
    "dates": 15,
    "financial_figures": 22
  }
}
```

**Success Criteria:**
- All entity types extracted: Organizations, People, Locations, Dates, Financial Figures
- Confidence scores provided for each entity
- No false positives above 0.7 confidence threshold
- Entities deduplicated (same entity mentioned multiple times = one entry)

## Context
Extracted entities feed downstream analysis including relationship mapping, timeline construction, and financial modeling.

## Constraints
- Extract only from provided text; do not infer entities
- Maintain original text spans exactly as they appear
- Confidence threshold for inclusion: 0.5 minimum
- Do not resolve ambiguous references (e.g., "the Company") without clear antecedent

## Tools
- @probe:extract_entities — Perform named entity recognition on text

## Error Handling
- If text is too short for meaningful extraction, return empty results with explanation
- If entity type is ambiguous, include in most likely category with reduced confidence
- If text encoding issues prevent extraction, report specific errors""",
        probe_ids=["extract_entities"],
        reference_ids=[],
        template_variables=[],
        metadata={"version": "2.0", "tags": ["nlp", "extraction"]},
    ),
    # -------------------------------------------------------------------------
    # Google News Market Research Directives
    # -------------------------------------------------------------------------
    Directive(
        id="dir-006",
        name="Company News Gathering",
        description="Gather recent news articles about a company from Google News",
        content="""## Role
You are a news research analyst specializing in corporate intelligence and media monitoring.

## Task Spec
Gather and organize recent news coverage for @variable:company_name using Google News RSS feeds.

**Expected Output Format:**
```json
{
  "company": "<company_name>",
  "ticker": "<ticker_if_provided>",
  "period": "<time_range>",
  "article_count": <number>,
  "articles": [
    {
      "title": "...",
      "source": "...",
      "published": "...",
      "summary": "...",
      "sentiment": "positive|negative|neutral",
      "relevance": "high|medium|low"
    }
  ],
  "themes": ["theme1", "theme2"],
  "notable_events": ["event1", "event2"]
}
```

**Success Criteria:**
- Minimum 10 relevant articles gathered (if available)
- Articles sorted by relevance and recency
- Key themes and events identified
- Sentiment classified for each article

## Context
This news gathering feeds into investment analysis workflows. The output will be used by downstream workers to construct bull and bear case arguments.

## Constraints
- Focus on news from the past @variable:time_range
- Prioritize reputable financial news sources (Reuters, Bloomberg, WSJ, FT)
- Exclude press releases unless material
- Maximum 50 articles to prevent information overload

## Tools
- @probe:search_google_news_by_company — Search Google News for company-specific articles
- @probe:search_google_news — Advanced search with filters for specific topics
- @probe:fetch_google_news_by_topic — Get industry-related BUSINESS news

## Error Handling
- If no articles found, expand search to broader industry terms
- If company name is ambiguous, include ticker symbol in search
- If rate limited, return partial results with warning""",
        probe_ids=[
            "search_google_news_by_company",
            "search_google_news",
            "fetch_google_news_by_topic",
        ],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Name of the company to research",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="ticker",
                description="Stock ticker symbol (optional)",
                required=False,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="time_range",
                description="Time range for news (e.g., '7d', '30d')",
                required=False,
                default="7d",
                ui_hint="select",
                ui_options={"options": ["1d", "7d", "30d", "90d"]},
                used_by=[],
            ),
        ],
        metadata={"version": "1.0", "tags": ["news", "research", "google-news"]},
    ),
    Directive(
        id="dir-007",
        name="Bull Case Analysis",
        description="Construct a bullish investment thesis from news and data",
        content="""## Role
You are an equity research analyst tasked with constructing the strongest possible bull case for an investment opportunity.

## Task Spec
Analyze news and data for @variable:company_name to build a compelling bull case thesis.

## CRITICAL: Autonomous Data Gathering
You MUST deliver a complete analysis with at least 3 concrete news citations. If the provided documents are insufficient:
1. **DO NOT** ask for permission to search - you have full authority to use your tools
2. **DO NOT** return an incomplete analysis saying you need more data
3. **IMMEDIATELY** use @probe:search_google_news to gather additional positive catalysts
4. Search for: "@variable:company_name positive news", "@variable:company_name growth catalyst", "@variable:company_name bullish"

You are an autonomous analyst. Gather what you need and deliver results.

**Expected Output Format:**
# Bull Case: @variable:company_name

## Investment Thesis (2-3 sentences)
<Core argument for why this is an attractive investment>

## Key Catalysts
1. **<Catalyst 1>**: <Evidence from news with source and date>
2. **<Catalyst 2>**: <Evidence from news with source and date>
3. **<Catalyst 3>**: <Evidence from news with source and date>

## Competitive Advantages
- <Moat 1>
- <Moat 2>

## Growth Drivers
| Driver | Evidence | Potential Impact |
|--------|----------|------------------|
| ...    | ...      | High/Medium/Low  |

## Risks to Thesis (Acknowledged)
- <Risk 1 and why it's manageable>
- <Risk 2 and why it's manageable>

## Conclusion
<Summary of bull case with confidence level: High/Medium/Low>

**Success Criteria:**
- Thesis supported by at least 3 concrete news citations (with source and date)
- All major growth catalysts identified
- Competitive moats clearly articulated
- Risks acknowledged but countered with mitigating factors

## Context
This bull case will be presented alongside a bear case for balanced investment analysis. Focus on making the strongest possible positive argument.

## Constraints
- Do not fabricate statistics or quotes
- All citations must reference real articles (from provided docs OR your searches)
- Acknowledge risks but emphasize upside
- Maximum output: 1000 words

## Tools
- @probe:search_google_news — USE THIS PROACTIVELY when you need more positive catalysts. Do not wait for permission.

## Data Gathering Strategy
1. First, review provided documents for positive signals
2. Count your potential citations - if fewer than 3 strong ones, SEARCH IMMEDIATELY
3. Use search queries like: "@variable:company_name earnings beat", "@variable:company_name product launch", "@variable:company_name market share"
4. Compile all evidence, then write your analysis

## Error Handling
- If provided data is insufficient: USE YOUR SEARCH TOOLS (do not ask permission)
- If company is in crisis: search for recovery signals, silver linings, or long-term positives
- If data is stale: search for recent news to supplement""",
        probe_ids=["search_google_news"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Name of the company to analyze",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={"version": "1.0", "tags": ["analysis", "bull-case", "investment"]},
    ),
    Directive(
        id="dir-008",
        name="Bear Case Analysis",
        description="Construct a bearish investment thesis from news and data",
        content="""## Role
You are a short-seller research analyst tasked with identifying risks and constructing the strongest possible bear case.

## Task Spec
Analyze news and data for @variable:company_name to build a comprehensive bear case thesis.

## CRITICAL: Autonomous Data Gathering
You MUST deliver a complete analysis with at least 3 concrete risk citations. If the provided documents are insufficient:
1. **DO NOT** ask for permission to search - you have full authority to use your tools
2. **DO NOT** return an incomplete analysis saying you need more data
3. **IMMEDIATELY** use @probe:search_google_news to gather additional risk signals
4. Search for: "@variable:company_name risks", "@variable:company_name concerns", "@variable:company_name challenges", "@variable:company_name competition"

You are an autonomous analyst. Gather what you need and deliver results.

**Expected Output Format:**
# Bear Case: @variable:company_name

## Investment Thesis (2-3 sentences)
<Core argument for why this investment carries significant risk>

## Key Risks
1. **<Risk 1>**: <Evidence from news with source and date>
2. **<Risk 2>**: <Evidence from news with source and date>
3. **<Risk 3>**: <Evidence from news with source and date>

## Competitive Threats
- <Threat 1>
- <Threat 2>

## Red Flags
| Concern | Evidence | Severity |
|---------|----------|----------|
| ...     | ...      | High/Medium/Low |

## Counter-Arguments (Acknowledged)
- <Bull argument 1 and why it may not hold>
- <Bull argument 2 and why it may not hold>

## Conclusion
<Summary of bear case with conviction level: High/Medium/Low>

**Success Criteria:**
- At least 3 material risks identified with news citations (source and date)
- Competitive threats clearly articulated
- Red flags quantified where possible
- Bull counter-arguments addressed

## Context
This bear case will be presented alongside a bull case for balanced investment analysis. Focus on identifying genuine risks and concerns.

## Constraints
- Do not exaggerate or sensationalize risks
- All citations must reference real articles (from provided docs OR your searches)
- Acknowledge positive factors but highlight vulnerabilities
- Maximum output: 1000 words

## Tools
- @probe:search_google_news — USE THIS PROACTIVELY when you need more risk signals. Do not wait for permission.

## Data Gathering Strategy
1. First, review provided documents for risk signals
2. Count your potential citations - if fewer than 3 strong ones, SEARCH IMMEDIATELY
3. Use search queries like: "@variable:company_name lawsuit", "@variable:company_name decline", "@variable:company_name losing market share"
4. Compile all evidence, then write your analysis

## Error Handling
- If provided data is insufficient: USE YOUR SEARCH TOOLS (do not ask permission)
- If company appears strong: search for valuation concerns, competitive threats, regulatory risks
- If data is stale: search for recent negative developments""",
        probe_ids=["search_google_news"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Name of the company to analyze",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={"version": "1.0", "tags": ["analysis", "bear-case", "investment"]},
    ),
    Directive(
        id="dir-009",
        name="Market Research Synthesis",
        description="Synthesize bull and bear cases into a balanced investment report",
        content="""## Role
You are a senior investment analyst responsible for synthesizing research into balanced, actionable investment recommendations.

## Task Spec
Combine the bull case and bear case analyses for @variable:company_name into a comprehensive investment research report.

**Expected Output Format:**
# Investment Research Report: @variable:company_name
**Date:** <current_date>
**Analyst:** AI Research Team

---

## Executive Summary
<2-3 paragraph overview of the investment opportunity>

## Company Overview
<Brief description of the company, industry, and market position>

## Bull Case Summary
<Condensed version of bull thesis - 3-4 key points>

## Bear Case Summary
<Condensed version of bear thesis - 3-4 key points>

## Key Debate Points
| Topic | Bull View | Bear View | Our Assessment |
|-------|-----------|-----------|----------------|
| ...   | ...       | ...       | ...            |

## Risk/Reward Assessment
- **Upside Scenario:** <description and probability>
- **Base Case:** <description and probability>
- **Downside Scenario:** <description and probability>

## Recommendation
**Rating:** <Buy / Hold / Sell / No Rating>
**Conviction:** <High / Medium / Low>
**Key Monitoring Points:**
1. <What to watch>
2. <What to watch>

## Appendix: News Sources
<List of articles referenced with dates>

---

**Success Criteria:**
- Both bull and bear perspectives fairly represented
- Clear recommendation with stated conviction
- Key debate points identified for ongoing monitoring
- All claims traceable to source articles

## Context
This is the final deliverable for the market research workflow. It must be suitable for presentation to investment committee or portfolio managers.

## Constraints
- Maintain objectivity; do not favor bull or bear case without justification
- Clearly state when evidence is limited or uncertain
- Maximum output: 1500 words (excluding appendix)

## Tools
- @probe:summarize_document — Condense upstream analyses if needed

## Error Handling
- If bull/bear cases are unbalanced, note the asymmetry
- If recommendation is unclear, default to "Hold" with explanation
- If critical data is missing, state "Insufficient Data" for that section""",
        probe_ids=["summarize_document"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Name of the company being researched",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={"version": "1.0", "tags": ["synthesis", "research", "investment"]},
    ),
    Directive(
        id="dir-010",
        name="Market Research Planning",
        description="Create a research plan for company market analysis",
        content="""## Role
You are a research director responsible for planning and coordinating market research workflows.

## Task Spec
Create a structured research plan for analyzing @variable:company_name.

**Expected Output Format:**
```json
{
  "research_plan": {
    "company": "<company_name>",
    "ticker": "<ticker_if_known>",
    "industry": "<industry>",
    "research_objectives": [
      "Gather recent news coverage",
      "Identify key catalysts and risks",
      "Construct bull and bear cases",
      "Synthesize into investment report"
    ],
    "data_sources": [
      "Google News - Company specific",
      "Google News - Industry (BUSINESS topic)",
      "Google News - Competitor mentions"
    ],
    "search_queries": [
      {"query": "<company_name>", "when": "7d"},
      {"query": "<company_name> earnings", "when": "30d"},
      {"query": "<company_name> OR <ticker>", "when": "7d"}
    ],
    "worker_assignments": [
      {"task": "news_gathering", "directive": "dir-006"},
      {"task": "bull_case", "directive": "dir-007"},
      {"task": "bear_case", "directive": "dir-008"},
      {"task": "synthesis", "directive": "dir-009"}
    ]
  }
}
```

**Success Criteria:**
- Clear research objectives defined
- Appropriate data sources identified
- Search queries optimized for relevant results
- Worker assignments mapped to directives

## Context
This planning step initiates the market research constellation. The plan guides downstream workers in gathering and analyzing data.

## Constraints
- Plan must be executable with available probes
- Keep search queries focused to avoid noise
- Limit to 3-5 primary research objectives

## Tools
- @probe:fetch_google_news_by_topic — Check available topic categories
- @probe:search_google_news — Validate search query syntax

## Error Handling
- If company is unknown, gather basic info first
- If industry unclear, default to BUSINESS topic
- If ticker unknown, proceed with company name only""",
        probe_ids=["fetch_google_news_by_topic", "search_google_news"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="company_name",
                description="Name of the company to research",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={"version": "1.0", "tags": ["planning", "research"]},
    ),
]


# ============================================================================
# Sample Stars
# ============================================================================

STARS = [
    WorkerStar(
        id="star-001",
        name="Financial Metrics Extractor",
        directive_id="dir-001",
        config={"temperature": 0.3, "max_tokens": 4000},
        ai_generated=False,
        metadata={"created_by": "admin"},
        probe_ids=["extract_financial_metrics"],
        max_iterations=3,
    ),
    PlanningStar(
        id="star-002",
        name="Market Analysis Planner",
        directive_id="dir-002",
        config={"planning_depth": 3},
        ai_generated=True,
        metadata={},
        probe_ids=["analyze_market_trends"],
    ),
    DocExStar(
        id="star-003",
        name="Document Processor",
        directive_id="dir-003",
        config={"chunk_size": 2000, "overlap": 200},
        ai_generated=False,
        metadata={},
    ),
    EvalStar(
        id="star-004",
        name="Quality Evaluator",
        directive_id="dir-004",
        config={"threshold": 0.8},
        ai_generated=False,
        metadata={},
        probe_ids=["extract_entities"],
    ),
    SynthesisStar(
        id="star-005",
        name="Report Synthesizer",
        directive_id="dir-001",
        config={"format": "markdown"},
        ai_generated=False,
        metadata={},
        probe_ids=["summarize_document"],
    ),
    ExecutionStar(
        id="star-006",
        name="Parallel Executor",
        directive_id="dir-002",
        config={"max_concurrent": 5},
        ai_generated=False,
        metadata={},
        parallel=True,
    ),
    # -------------------------------------------------------------------------
    # Market Research Constellation Stars
    # -------------------------------------------------------------------------
    PlanningStar(
        id="star-007",
        name="Market Research Planner",
        directive_id="dir-010",
        config={"planning_depth": 2},
        ai_generated=False,
        metadata={"workflow": "market-research"},
        probe_ids=["fetch_google_news_by_topic", "search_google_news"],
    ),
    ExecutionStar(
        id="star-008",
        name="Market Research Executor",
        directive_id="dir-010",
        config={"max_concurrent": 3},
        ai_generated=False,
        metadata={"workflow": "market-research"},
        parallel=True,
    ),
    WorkerStar(
        id="star-009",
        name="News Gatherer",
        directive_id="dir-006",
        config={"temperature": 0.2, "max_tokens": 4000},
        ai_generated=False,
        metadata={"workflow": "market-research"},
        probe_ids=[
            "search_google_news_by_company",
            "search_google_news",
            "fetch_google_news_by_topic",
        ],
        max_iterations=2,
    ),
    WorkerStar(
        id="star-010",
        name="Bull Case Analyst",
        directive_id="dir-007",
        config={"temperature": 0.4, "max_tokens": 3000},
        ai_generated=False,
        metadata={"workflow": "market-research", "perspective": "bullish"},
        probe_ids=["search_google_news"],
        max_iterations=1,
    ),
    WorkerStar(
        id="star-011",
        name="Bear Case Analyst",
        directive_id="dir-008",
        config={"temperature": 0.4, "max_tokens": 3000},
        ai_generated=False,
        metadata={"workflow": "market-research", "perspective": "bearish"},
        probe_ids=["search_google_news"],
        max_iterations=1,
    ),
    SynthesisStar(
        id="star-012",
        name="Research Report Synthesizer",
        directive_id="dir-009",
        config={"format": "markdown", "include_sources": True},
        ai_generated=False,
        metadata={"workflow": "market-research"},
        probe_ids=["summarize_document"],
    ),
]


# ============================================================================
# Sample Constellations
# ============================================================================

CONSTELLATIONS = [
    Constellation(
        id="const-001",
        name="Company Market Research",
        description="""Comprehensive market research workflow that gathers recent news about a company,
analyzes it from both bullish and bearish perspectives, and synthesizes the findings
into a balanced investment research report with bull case, bear case, and recommendation.""",
        start=StartNode(
            id="start",
            position=Position(x=0, y=200),
        ),
        end=EndNode(
            id="end",
            position=Position(x=1200, y=200),
        ),
        nodes=[
            # Planning node - creates research plan
            StarNode(
                id="planning",
                star_id="star-007",
                position=Position(x=150, y=200),
                display_name="Research Planner",
            ),
            # Execution node - spawns workers based on plan
            StarNode(
                id="execution",
                star_id="star-008",
                position=Position(x=350, y=200),
                display_name="Task Executor",
            ),
            # News gathering worker
            StarNode(
                id="news_gatherer",
                star_id="star-009",
                position=Position(x=550, y=200),
                display_name="News Gatherer",
            ),
            # Bull case analyst (parallel)
            StarNode(
                id="bull_analyst",
                star_id="star-010",
                position=Position(x=750, y=100),
                display_name="Bull Case Analyst",
            ),
            # Bear case analyst (parallel)
            StarNode(
                id="bear_analyst",
                star_id="star-011",
                position=Position(x=750, y=300),
                display_name="Bear Case Analyst",
            ),
            # Synthesis node - combines bull and bear cases
            StarNode(
                id="synthesis",
                star_id="star-012",
                position=Position(x=950, y=200),
                display_name="Report Synthesizer",
            ),
        ],
        edges=[
            # Start -> Planning
            Edge(id="e1", source="start", target="planning", condition=None),
            # Planning -> Execution
            Edge(id="e2", source="planning", target="execution", condition=None),
            # Execution -> News Gatherer
            Edge(id="e3", source="execution", target="news_gatherer", condition=None),
            # News Gatherer -> Bull Analyst (parallel branch)
            Edge(
                id="e4", source="news_gatherer", target="bull_analyst", condition=None
            ),
            # News Gatherer -> Bear Analyst (parallel branch)
            Edge(
                id="e5", source="news_gatherer", target="bear_analyst", condition=None
            ),
            # Bull Analyst -> Synthesis
            Edge(id="e6", source="bull_analyst", target="synthesis", condition=None),
            # Bear Analyst -> Synthesis
            Edge(id="e7", source="bear_analyst", target="synthesis", condition=None),
            # Synthesis -> End
            Edge(id="e8", source="synthesis", target="end", condition=None),
        ],
        max_loop_iterations=3,
        max_retry_attempts=2,
        retry_delay_base=1.0,
        metadata={
            "version": "1.0",
            "category": "market-research",
            "tags": ["investment", "research", "news", "bull-bear"],
            "estimated_runtime": "2-5 minutes",
        },
    ),
]


async def seed_database():
    """Seed the database with sample data."""
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    persistence = FoundryPersistence(MONGO_URI, DATABASE_NAME)

    try:
        # Clear existing data
        print("Clearing existing data...")
        await persistence.directives.delete_many({})
        await persistence.stars.delete_many({})
        await persistence.constellations.delete_many({})
        await persistence.runs.delete_many({})

        # Seed directives
        print(f"Seeding {len(DIRECTIVES)} directives...")
        for directive in DIRECTIVES:
            await persistence.create_directive(directive)
            print(f"  Created directive: {directive.id} - {directive.name}")

        # Seed stars
        print(f"Seeding {len(STARS)} stars...")
        for star in STARS:
            await persistence.create_star(star)
            print(f"  Created star: {star.id} - {star.name} ({star.type})")

        # Seed constellations
        print(f"Seeding {len(CONSTELLATIONS)} constellations...")
        for constellation in CONSTELLATIONS:
            await persistence.create_constellation(constellation)
            print(f"  Created constellation: {constellation.id} - {constellation.name}")

        print("\nDatabase seeded successfully!")
        print(f"  Directives: {len(DIRECTIVES)}")
        print(f"  Stars: {len(STARS)}")
        print(f"  Constellations: {len(CONSTELLATIONS)}")

    finally:
        await persistence.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
