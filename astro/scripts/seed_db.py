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
    Constellation,
    Directive,
    Edge,
    EndNode,
    Position,
    StarNode,
    StartNode,
    TemplateVariable,
)
from astro_backend_service.models.stars import (
    DocExStar,
    EvalStar,
    ExecutionStar,
    PlanningStar,
    SynthesisStar,
    WorkerStar,
)

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGO_DB", "astro")


# ============================================================================
# Sample Directives
# ============================================================================

# ============================================================================
# Due Diligence Benchmark - Sub-Directive Templates (No Probes)
# These are referenced by other Stars for modular prompt composition
# ============================================================================

DD_SUB_DIRECTIVES = [
    Directive(
        id="base-analysis-framework-v1",
        name="Base Analysis Framework",
        description="Shared formatting and analytical structure for all due diligence workers. Referenced as a sub-directive by analytical Stars.",
        content="""## Output Requirements

All analysis MUST follow this structure:

### Findings
- State each finding as a discrete, numbered claim
- Each claim must include: confidence level (HIGH/MEDIUM/LOW), source attribution, and relevance to investment thesis

### Evidence
- For each finding, provide the raw evidence that supports it
- Quote directly from tool outputs where possible
- Flag any contradictions between sources

### Risk Flags
- Enumerate any risks identified, categorized as: MATERIAL, MODERATE, or INFORMATIONAL
- Each risk flag must include a brief mitigation or monitoring recommendation

### Limitations
- State what you could NOT determine and why
- Flag any data gaps that would require additional investigation

## Analytical Standards
- Do NOT speculate beyond what evidence supports
- Do NOT anchor on any single data point
- ALWAYS note when information is stale (>30 days old)
- ALWAYS distinguish between facts, estimates, and opinions""",
        probe_ids=[],  # Sub-directive has NO probes
        reference_ids=[],
        template_variables=[],
        metadata={
            "version": "1.0.0",
            "tags": ["framework", "shared", "formatting", "sub-directive"],
            "benchmark": "due-diligence",
        },
    ),
    Directive(
        id="financial-risk-template-v1",
        name="Financial Risk Assessment Template",
        description="Risk assessment framework specific to financial analysis. Sub-directive referenced by the risk scorer.",
        content="""## Financial Risk Dimensions

Evaluate the following dimensions:

1. **Revenue Concentration Risk**: What % of revenue comes from top 3 customers/segments? Score 1-10.
2. **Margin Trajectory Risk**: Are margins expanding or compressing over the last 4 quarters? Score 1-10.
3. **Debt Service Risk**: What is the interest coverage ratio? Is it trending up or down? Score 1-10.
4. **Cash Flow Quality**: Is FCF growing in line with net income, or diverging? Score 1-10.
5. **Valuation Risk**: How does current valuation compare to 5-year historical range and sector median? Score 1-10.

For each dimension, provide:
- Raw data point used
- Score (1-10, where 10 = highest risk)
- Brief justification
- Comparison to sector median if available""",
        probe_ids=[],  # Sub-directive has NO probes
        reference_ids=[],
        template_variables=[],
        metadata={
            "version": "1.0.0",
            "tags": ["risk", "financial", "template", "sub-directive"],
            "benchmark": "due-diligence",
        },
    ),
    Directive(
        id="regulatory-risk-template-v1",
        name="Regulatory Risk Assessment Template",
        description="Risk assessment framework for regulatory and compliance analysis. Sub-directive referenced by the risk scorer.",
        content="""## Regulatory Risk Dimensions

1. **Active Enforcement Actions**: Any current SEC, FTC, DOJ, or sector-specific regulatory actions? Score 1-10.
2. **Regulatory Change Exposure**: Are there pending regulations that could materially impact the business model? Score 1-10.
3. **Compliance History**: Track record of compliance violations in the last 5 years? Score 1-10.
4. **Geographic Regulatory Risk**: Operating in jurisdictions with changing regulatory environments? Score 1-10.
5. **Data/Privacy Risk**: Exposure to GDPR, CCPA, or sector-specific data regulations? Score 1-10.

For each dimension, provide:
- Specific regulatory body and action (if applicable)
- Score (1-10, where 10 = highest risk)
- Potential financial impact estimate (if determinable)
- Timeline for resolution or regulatory change""",
        probe_ids=[],  # Sub-directive has NO probes
        reference_ids=[],
        template_variables=[],
        metadata={
            "version": "1.0.0",
            "tags": ["risk", "regulatory", "template", "sub-directive"],
            "benchmark": "due-diligence",
        },
    ),
]

# ============================================================================
# Due Diligence Benchmark - Analytical Worker Directives
# Each has specific probe access for tool-scoping test
# ============================================================================

DD_WORKER_DIRECTIVES = [
    Directive(
        id="financial-analyst-v1",
        name="Financial Data Analyst",
        description="Gathers and analyzes financial data for due diligence. Has access ONLY to financial data probes.",
        content="""You are a financial analyst conducting due diligence on @variable:company_name.

## Your Task
Gather and analyze the company's financial performance, capital structure, and valuation metrics.

## Required Analysis
1. Revenue and earnings trajectory (last 4 quarters minimum)
2. Balance sheet health (debt levels, cash position, working capital)
3. Cash flow analysis (operating, investing, financing)
4. Valuation multiples (P/E, EV/EBITDA, P/S) vs sector
5. Key financial risks or anomalies

## Tool Usage
Use your available financial data tools to gather QUANTITATIVE data. Do not speculate on market sentiment or regulatory issues — those are handled by other analysts.

## CRITICAL CONSTRAINTS
- Stay in your lane: financial data ONLY
- Do NOT search for news articles or sentiment
- Do NOT assess regulatory risk
- If you encounter non-financial information, note it but do not analyze it
- Flag any financial anomalies for the forensic analysis team by setting `anomalies_flagged: true` in your output

## Output Format
Include at the end of your analysis:
```json
{
  "anomalies_flagged": true/false,
  "anomaly_details": ["description of anomaly 1", "description of anomaly 2"]
}
```""",
        probe_ids=["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
        reference_ids=["base-analysis-framework-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["financial", "analysis", "worker"],
            "benchmark": "due-diligence",
            "probe_scope": "financial_only",
        },
    ),
    Directive(
        id="sentiment-analyst-v1",
        name="Market Sentiment Analyst",
        description="Analyzes market sentiment and narrative from news and social sources. Deliberately isolated from financial data to prevent anchoring.",
        content="""You are a market sentiment analyst conducting due diligence on @variable:company_name.

## Your Task
Analyze the current market narrative, media sentiment, and public perception around this company.

## Required Analysis
1. Overall media sentiment (bullish/bearish/neutral) with evidence
2. Key narrative themes in recent coverage (last 30 days)
3. Analyst consensus and notable dissenting views
4. Social media and retail investor sentiment signals
5. Any emerging narrative shifts or inflection points

## Tool Usage
Use your available news and search tools to gather QUALITATIVE sentiment data.

## CRITICAL CONSTRAINTS
- Stay in your lane: sentiment and narrative ONLY
- Do NOT look up financial data, stock prices, or valuation metrics
- Do NOT assess regulatory filings or compliance
- Your job is to capture the STORY the market is telling, independent of the numbers
- This isolation is intentional: we want your sentiment assessment UNCONTAMINATED by financial anchoring""",
        probe_ids=["search_news", "get_social_sentiment", "get_analyst_ratings"],
        reference_ids=["base-analysis-framework-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["sentiment", "news", "analysis", "worker"],
            "benchmark": "due-diligence",
            "probe_scope": "sentiment_only",
        },
    ),
    Directive(
        id="regulatory-analyst-v1",
        name="Regulatory & Compliance Analyst",
        description="Analyzes regulatory environment, compliance history, and legal exposure.",
        content="""You are a regulatory and compliance analyst conducting due diligence on @variable:company_name.

## Your Task
Assess the regulatory environment, compliance track record, and legal exposure for this company.

## Required Analysis
1. Active regulatory actions, investigations, or settlements
2. Pending regulatory changes that could impact the business
3. Compliance violation history (last 5 years)
4. Litigation exposure (material lawsuits, class actions)
5. Industry-specific regulatory considerations

## Tool Usage
Use your regulatory and legal research tools to gather compliance data.

## CRITICAL CONSTRAINTS
- Stay in your lane: regulatory and legal ONLY
- Do NOT analyze financial performance or valuation
- Do NOT assess market sentiment
- Focus on FACTS from regulatory filings and legal databases
- Classify the company's primary regulatory regime (e.g., SEC-regulated, FDA-regulated, FCC-regulated, etc.)

## Output Format
Include at the end of your analysis:
```json
{
  "is_heavily_regulated": true/false,
  "primary_regulators": ["SEC", "FDA", etc.],
  "active_enforcement_actions": number,
  "material_litigation_pending": true/false
}
```""",
        probe_ids=["search_sec_filings", "search_legal_cases", "search_regulatory_filings"],
        reference_ids=["base-analysis-framework-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["regulatory", "compliance", "legal", "worker"],
            "benchmark": "due-diligence",
            "probe_scope": "regulatory_only",
        },
    ),
    Directive(
        id="competitive-analyst-v1",
        name="Competitive Landscape Analyst",
        description="Analyzes competitive positioning, market share, and strategic threats.",
        content="""You are a competitive analyst conducting due diligence on @variable:company_name.

## Your Task
Map the competitive landscape and assess the company's strategic positioning.

## Required Analysis
1. Top 3-5 direct competitors and their market positioning
2. Market share estimates and trends
3. Competitive moats (or lack thereof)
4. Emerging competitive threats (new entrants, substitutes)
5. Strategic initiatives vs competitors

## Tool Usage
Use your market research and competitive intelligence tools.

## CRITICAL CONSTRAINTS
- Stay in your lane: competitive positioning ONLY
- Use financial data only for COMPARATIVE purposes (company vs competitors)
- Do NOT deep-dive into the target's financials — the financial analyst handles that
- Focus on RELATIVE positioning, not absolute performance""",
        probe_ids=["get_market_research", "search_news", "get_financial_data"],
        reference_ids=["base-analysis-framework-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["competitive", "market", "analysis", "worker"],
            "benchmark": "due-diligence",
            "probe_scope": "competitive_only",
        },
    ),
    Directive(
        id="risk-scorer-v1",
        name="Integrated Risk Scorer",
        description="Synthesizes risk assessment across financial and regulatory dimensions. References both risk templates as sub-directives.",
        content="""You are a risk analyst producing an integrated risk assessment for @variable:company_name.

## Your Task
Using the analysis provided by other team members, produce a structured risk scorecard.

## Inputs Available
You will receive outputs from:
- Financial Analyst (financial data and metrics)
- Regulatory Analyst (compliance and legal exposure)
- Sentiment Analyst (market narrative and perception)
- Competitive Analyst (market positioning)

## Required Output
Produce a risk scorecard following BOTH the financial and regulatory risk templates referenced below. Then produce an INTEGRATED score.

### Integrated Risk Score
After completing both dimension-specific assessments:
1. Weight financial risk at 40% and regulatory risk at 30% and competitive risk at 20% and sentiment risk at 10%
2. Compute weighted average
3. Apply any override factors (e.g., existential regulatory threat overrides all other scores)
4. Output final risk rating: LOW / MODERATE / ELEVATED / HIGH / CRITICAL

## CRITICAL CONSTRAINTS
- You have NO tool access. You work ONLY with the analysis provided to you.
- Do NOT make assumptions about data you haven't received
- If any analytical input is missing or incomplete, flag it and score conservatively
- Your job is SYNTHESIS, not primary research""",
        probe_ids=[],  # NO PROBES - synthesis only
        reference_ids=["base-analysis-framework-v1", "financial-risk-template-v1", "regulatory-risk-template-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["risk", "scoring", "synthesis", "worker"],
            "benchmark": "due-diligence",
            "probe_scope": "none",
        },
    ),
    Directive(
        id="regulatory-deep-dive-v1",
        name="Regulatory Deep Dive (Conditional)",
        description="Extended regulatory analysis triggered ONLY when the company operates in a heavily regulated industry. This Star only executes conditionally.",
        content="""You are conducting a deep regulatory analysis for @variable:company_name, which operates in a heavily regulated industry.

## Context
The initial regulatory scan flagged this company as operating in a heavily regulated environment. This deep dive is triggered to assess sector-specific regulatory risks.

## Required Analysis
1. Sector-specific regulatory framework (e.g., FDA approval pipeline, banking capital requirements, energy compliance mandates)
2. Recent regulatory changes affecting this sector (last 12 months)
3. Peer comparison: how do competitors handle the same regulatory requirements?
4. Cost of compliance estimates
5. Regulatory risk scenarios: best case, base case, worst case

## Tool Usage
You have access to regulatory databases AND news search for this deep dive.

## CRITICAL CONSTRAINTS
- Go DEEPER than the initial regulatory scan
- Focus on SECTOR-SPECIFIC regulations, not general compliance
- Produce scenario-based risk assessments with probability estimates""",
        probe_ids=["search_regulatory_filings", "search_legal_cases", "search_news", "search_sec_filings"],
        reference_ids=["base-analysis-framework-v1", "regulatory-risk-template-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["regulatory", "deep-dive", "conditional", "worker"],
            "benchmark": "due-diligence",
            "conditional": True,
            "trigger": "is_heavily_regulated == true",
        },
    ),
    Directive(
        id="forensic-analyst-v1",
        name="Financial Forensic Analyst (Conditional)",
        description="Deep forensic financial analysis triggered ONLY when the financial analyst flags anomalies.",
        content="""You are a forensic financial analyst investigating flagged anomalies for @variable:company_name.

## Context
The initial financial analysis flagged one or more anomalies that require deeper investigation.

## Flagged Anomalies
{anomalies_from_financial_analyst}

## Required Analysis
1. For each flagged anomaly: determine if it's explainable or genuinely concerning
2. Check for accounting red flags (revenue recognition changes, unusual accruals, related party transactions)
3. Compare to sector norms — is this anomaly company-specific or sector-wide?
4. Assess management credibility (have they addressed this in earnings calls?)
5. Produce a fraud risk score (1-10) with justification

## Tool Usage
You have access to financial data AND earnings transcripts for forensic analysis.

## CRITICAL CONSTRAINTS
- Start from the SPECIFIC anomalies flagged, don't do a general scan
- Use earnings transcripts to check if management has addressed the anomalies
- Be precise: distinguish between 'unusual but explainable' and 'red flag'
- If you cannot determine whether an anomaly is benign, flag it as UNRESOLVED""",
        probe_ids=["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
        reference_ids=["base-analysis-framework-v1", "financial-risk-template-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["forensic", "financial", "conditional", "worker"],
            "benchmark": "due-diligence",
            "conditional": True,
            "trigger": "anomalies_flagged == true",
        },
    ),
    Directive(
        id="final-synthesis-v1",
        name="Final Due Diligence Synthesis",
        description="Produces the final due diligence report by synthesizing all analytical inputs. Has ZERO tool access — pure reasoning over provided analysis.",
        content="""You are the lead analyst producing the final due diligence report for @variable:company_name.

## Your Task
Synthesize ALL analytical inputs into a cohesive, actionable due diligence report.

## Inputs
You will receive completed analysis from:
- Financial Analyst
- Sentiment Analyst
- Regulatory Analyst
- Competitive Analyst
- Risk Scorer (integrated risk scorecard)
- Regulatory Deep Dive (if triggered)
- Forensic Analyst (if triggered)

## Required Output Structure

### 1. Executive Summary (3-5 sentences)
The single most important takeaway for a decision-maker.

### 2. Investment Thesis
- Bull case (top 3 arguments with evidence citations)
- Bear case (top 3 arguments with evidence citations)
- Key debate points where bull and bear disagree

### 3. Risk Assessment
Integrated risk scorecard from Risk Scorer, with your commentary on whether you agree or disagree with the scoring.

### 4. Information Conflicts
Identify where different analysts reached CONTRADICTORY conclusions. For each conflict:
- State both positions
- Assess which has stronger evidence
- Note what additional data would resolve the conflict

### 5. Recommendation
- Rating: STRONG BUY / BUY / HOLD / SELL / STRONG SELL
- Conviction: HIGH / MEDIUM / LOW
- Key monitoring triggers that would change the recommendation

### 6. Data Gaps & Limitations
What couldn't be determined? What would improve this analysis?

## CRITICAL CONSTRAINTS
- You have NO tool access. Synthesize ONLY from provided inputs.
- Do NOT introduce new claims not supported by the analytical inputs
- EXPLICITLY cite which analyst's work supports each claim
- Where analysts disagree, present BOTH views fairly
- Your value add is INTEGRATION and JUDGMENT, not new research""",
        probe_ids=[],  # NO PROBES - synthesis only
        reference_ids=["base-analysis-framework-v1"],
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
        ],
        metadata={
            "version": "1.0.0",
            "tags": ["synthesis", "final", "report"],
            "benchmark": "due-diligence",
            "probe_scope": "none",
        },
    ),
]

# ============================================================================
# Original Sample Directives
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
# Due Diligence Benchmark Stars
# ============================================================================

DD_STARS = [
    # Analytical Workers (AtomicStar - WorkerStar)
    WorkerStar(
        id="star-dd-financial",
        name="Financial Analyst",
        directive_id="financial-analyst-v1",
        config={"temperature": 0.2, "max_tokens": 4000},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "financial"},
        probe_ids=["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
        max_iterations=5,  # Increased from 3 to prevent "Maximum iterations reached"
    ),
    WorkerStar(
        id="star-dd-sentiment",
        name="Sentiment Analyst",
        directive_id="sentiment-analyst-v1",
        config={"temperature": 0.3, "max_tokens": 3000},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "sentiment"},
        probe_ids=["search_news", "get_social_sentiment", "get_analyst_ratings"],
        max_iterations=2,
    ),
    WorkerStar(
        id="star-dd-regulatory",
        name="Regulatory Analyst",
        directive_id="regulatory-analyst-v1",
        config={"temperature": 0.2, "max_tokens": 3500},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "regulatory"},
        probe_ids=["search_sec_filings", "search_legal_cases", "search_regulatory_filings"],
        max_iterations=2,
    ),
    WorkerStar(
        id="star-dd-competitive",
        name="Competitive Analyst",
        directive_id="competitive-analyst-v1",
        config={"temperature": 0.3, "max_tokens": 3000},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "competitive"},
        probe_ids=["get_market_research", "search_news", "get_financial_data"],
        max_iterations=2,
    ),
    # Conditional Workers
    WorkerStar(
        id="star-dd-regulatory-deep",
        name="Regulatory Deep Dive",
        directive_id="regulatory-deep-dive-v1",
        config={"temperature": 0.2, "max_tokens": 4000},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "regulatory-deep", "conditional": True},
        probe_ids=["search_regulatory_filings", "search_legal_cases", "search_news", "search_sec_filings"],
        max_iterations=3,
    ),
    WorkerStar(
        id="star-dd-forensic",
        name="Forensic Analyst",
        directive_id="forensic-analyst-v1",
        config={"temperature": 0.1, "max_tokens": 4000},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "forensic", "conditional": True},
        probe_ids=["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
        max_iterations=3,
    ),
    # Synthesis Workers (NO probes)
    SynthesisStar(
        id="star-dd-risk-scorer",
        name="Risk Scorer",
        directive_id="risk-scorer-v1",
        config={"format": "structured", "temperature": 0.2},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "risk-scoring"},
        probe_ids=[],  # NO PROBES - synthesis only
    ),
    SynthesisStar(
        id="star-dd-synthesis",
        name="Final Synthesis",
        directive_id="final-synthesis-v1",
        config={"format": "markdown", "include_sources": True, "temperature": 0.3},
        ai_generated=False,
        metadata={"benchmark": "due-diligence", "role": "final-synthesis"},
        probe_ids=[],  # NO PROBES - synthesis only
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
# Due Diligence Benchmark Constellation
# ============================================================================

DD_CONSTELLATIONS = [
    Constellation(
        id="const-dd-001",
        name="Cross-Source Due Diligence",
        description="""Multi-analyst due diligence workflow with tool-scoped parallel analysis,
conditional deep-dives, and synthesized output. This benchmark tests Astro's core differentiators:
- Tool scoping (each analyst only has access to relevant probes)
- Sub-directive composition (shared analysis framework)
- Conditional branching (regulatory deep-dive, forensic analysis)
- Probe isolation as a quality mechanism""",
        start=StartNode(
            id="start",
            position=Position(x=0, y=300),
        ),
        end=EndNode(
            id="end",
            position=Position(x=1400, y=300),
        ),
        nodes=[
            # Phase 1: Parallel Analysis (A, B, C, D execute in parallel)
            StarNode(
                id="financial_analyst",
                star_id="star-dd-financial",
                position=Position(x=200, y=100),
                display_name="Financial Analyst",
            ),
            StarNode(
                id="sentiment_analyst",
                star_id="star-dd-sentiment",
                position=Position(x=200, y=250),
                display_name="Sentiment Analyst",
            ),
            StarNode(
                id="regulatory_analyst",
                star_id="star-dd-regulatory",
                position=Position(x=200, y=400),
                display_name="Regulatory Analyst",
            ),
            StarNode(
                id="competitive_analyst",
                star_id="star-dd-competitive",
                position=Position(x=200, y=550),
                display_name="Competitive Analyst",
            ),
            # Phase 2: Conditional Deep-Dives (E, F - conditional)
            StarNode(
                id="regulatory_deep_dive",
                star_id="star-dd-regulatory-deep",
                position=Position(x=500, y=450),
                display_name="Regulatory Deep Dive",
            ),
            StarNode(
                id="forensic_analyst",
                star_id="star-dd-forensic",
                position=Position(x=500, y=100),
                display_name="Forensic Analyst",
            ),
            # Phase 3: Risk Scoring (G)
            StarNode(
                id="risk_scorer",
                star_id="star-dd-risk-scorer",
                position=Position(x=800, y=300),
                display_name="Risk Scorer",
            ),
            # Phase 4: Final Synthesis (H)
            StarNode(
                id="final_synthesis",
                star_id="star-dd-synthesis",
                position=Position(x=1100, y=300),
                display_name="Final Synthesis",
            ),
        ],
        edges=[
            # START -> Phase 1 (parallel)
            Edge(id="e-start-fin", source="start", target="financial_analyst", condition=None),
            Edge(id="e-start-sent", source="start", target="sentiment_analyst", condition=None),
            Edge(id="e-start-reg", source="start", target="regulatory_analyst", condition=None),
            Edge(id="e-start-comp", source="start", target="competitive_analyst", condition=None),
            # Phase 1 -> Phase 2 (conditional branches)
            # Financial -> Forensic (if anomalies flagged)
            Edge(id="e-fin-forensic", source="financial_analyst", target="forensic_analyst", condition="output.anomalies_flagged == true"),
            # Regulatory -> Deep Dive (if heavily regulated)
            Edge(id="e-reg-deep", source="regulatory_analyst", target="regulatory_deep_dive", condition="output.is_heavily_regulated == true"),
            # Phase 1 & 2 -> Risk Scorer (all feed into G)
            Edge(id="e-fin-risk", source="financial_analyst", target="risk_scorer", condition=None),
            Edge(id="e-sent-risk", source="sentiment_analyst", target="risk_scorer", condition=None),
            Edge(id="e-reg-risk", source="regulatory_analyst", target="risk_scorer", condition=None),
            Edge(id="e-comp-risk", source="competitive_analyst", target="risk_scorer", condition=None),
            # Conditional workers also feed to risk scorer (optional edges)
            Edge(id="e-forensic-risk", source="forensic_analyst", target="risk_scorer", condition=None),
            Edge(id="e-deep-risk", source="regulatory_deep_dive", target="risk_scorer", condition=None),
            # Phase 3 -> Phase 4 (Risk Scorer -> Final Synthesis)
            Edge(id="e-risk-synth", source="risk_scorer", target="final_synthesis", condition=None),
            # All analysts also feed directly to Final Synthesis for full context
            Edge(id="e-fin-synth", source="financial_analyst", target="final_synthesis", condition=None),
            Edge(id="e-sent-synth", source="sentiment_analyst", target="final_synthesis", condition=None),
            Edge(id="e-reg-synth", source="regulatory_analyst", target="final_synthesis", condition=None),
            Edge(id="e-comp-synth", source="competitive_analyst", target="final_synthesis", condition=None),
            Edge(id="e-forensic-synth", source="forensic_analyst", target="final_synthesis", condition=None),
            Edge(id="e-deep-synth", source="regulatory_deep_dive", target="final_synthesis", condition=None),
            # Final Synthesis -> END
            Edge(id="e-synth-end", source="final_synthesis", target="end", condition=None),
        ],
        max_loop_iterations=1,  # No loops in this workflow
        max_retry_attempts=2,
        retry_delay_base=1.0,
        metadata={
            "version": "1.0.0",
            "category": "due-diligence",
            "benchmark": True,
            "tags": ["investment", "due-diligence", "benchmark", "tool-scoping"],
            "estimated_runtime": "3-8 minutes",
            "execution_notes": {
                "phase_1": "Nodes A, B, C, D execute in PARALLEL (different probe scopes)",
                "phase_2_conditional": "Node E triggers IF C outputs is_heavily_regulated=true. Node F triggers IF A flags anomalies.",
                "phase_3": "Node G (Risk Scorer) waits for A, B, C, D (and E, F if triggered) to complete",
                "phase_4": "Node H (Final Synthesis) receives ALL outputs including G's risk scorecard",
            },
            "probe_scoping_matrix": {
                "financial_analyst": ["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
                "sentiment_analyst": ["search_news", "get_social_sentiment", "get_analyst_ratings"],
                "regulatory_analyst": ["search_sec_filings", "search_legal_cases", "search_regulatory_filings"],
                "competitive_analyst": ["get_market_research", "search_news", "get_financial_data"],
                "regulatory_deep_dive": ["search_regulatory_filings", "search_legal_cases", "search_news", "search_sec_filings"],
                "forensic_analyst": ["search_sec_filings", "get_financial_data", "search_earnings_transcripts"],
                "risk_scorer": [],
                "final_synthesis": [],
            },
        },
    ),
]

# ============================================================================
# Fund Model Reverse Engineering — Directives
# ============================================================================

FUND_MODEL_DIRECTIVES = [
    # Phase 1 Directives
    Directive(
        id="excel_structure_analysis",
        name="Excel Structure Analyzer",
        description="Analyzes uploaded Excel file to identify sheets, structure, data regions, and potential relationships. First step in model reverse engineering.",
        content="""You are a financial model analyst examining the structure of an uploaded Excel file.

Your task is to analyze the parsed Excel data and produce a structural summary.

## Analysis Steps

Use the parse_excel_structure probe to read the file, then use analyze_sheet_structure on each sheet.

For each sheet, identify:
1. The sheet's purpose (what financial concept it represents)
2. Which rows are headers vs labels vs data
3. Which rows contain input values vs calculated values
4. The time axis (do periods run across columns?)
5. Obvious subtotals or summary rows
6. Any formatting clues (percentage formats suggest rates, currency formats suggest cash values)

## Tools Available
- @probe:parse_excel_structure — Parse the uploaded .xlsx file
- @probe:analyze_sheet_structure — Get detailed analysis of each sheet

## Input
The file to analyze is at: @variable:excel_file_path

## Output Format
Output a structured JSON with your analysis:
```json
{
  "file_name": "...",
  "sheets": [
    {
      "name": "...",
      "purpose": "...",
      "header_rows": 1,
      "label_cols": 1,
      "input_rows": [3, 4, 5],
      "calculated_rows": [6, 7, 8, 9],
      "time_labels": ["Q1 2024", "Q2 2024", ...],
      "row_labels": {"3": "Revenue", "4": "COGS", ...},
      "ambiguous_rows": [{"row": 10, "reason": "unclear if input or calculated"}]
    }
  ],
  "observations": ["cross-sheet reference suspected from Fees to Cash Flows", ...]
}
```

## Critical Rules
- Be precise about row and column numbers.
- Do NOT guess at formula relationships. Only report what you can observe from values and structure.
- Flag anything ambiguous with a note for the interviewer phase.
- The expert interview phase will capture the actual logic.""",
        probe_ids=["parse_excel_structure", "analyze_sheet_structure"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="excel_file_path",
                description="Path to the uploaded .xlsx fund model output file",
                required=True,
                default=None,
                ui_hint="file",
                ui_options={"accept": ".xlsx,.xls"},
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["excel", "analysis", "phase1"],
            "version": "1.0",
        },
    ),
    Directive(
        id="cross_sheet_dependency_mapping",
        name="Cross-Sheet Dependency Mapper",
        description="Identifies potential cross-sheet relationships by analyzing numeric patterns across sheets. Maps which sheets feed into which.",
        content="""You are analyzing cross-sheet dependencies in a fund model.

You receive the structural analysis of all sheets from the previous step.

## Your Task
1. For each calculated row, check if its values match a transformation of values from another sheet
2. Build a dependency graph: which sheets reference which other sheets
3. Determine the calculation order (which sheet must be computed first)
4. Flag specific rows where you detect a clear cross-sheet relationship

## Common Fund Model Patterns
Look for these common cross-sheet relationships:
- Fees sheet pulls from Cash Flows sheet (management fees as % of committed capital or NAV)
- Distributions sheet references both Cash Flows and Fees
- Incentive fees reference distributions and hurdle rates from Assumptions
- Credit facility drawdowns reference cash flow shortfalls

## Tools Available
- @probe:detect_row_patterns — Detect repeating numeric patterns within and across sheets

## Input
Upstream structural analysis: @variable:structure_analysis

## Output Format
```json
{
  "dependency_graph": {
    "Cash Flows": [],
    "Fees": ["Cash Flows", "Assumptions"],
    "Distributions": ["Cash Flows", "Fees"]
  },
  "calculation_order": ["Assumptions", "Cash Flows", "Fees", "Distributions"],
  "detected_relationships": [
    {
      "source_sheet": "Cash Flows",
      "source_row": 5,
      "source_label": "Revenue",
      "target_sheet": "Fees",
      "target_row": 3,
      "target_label": "Management Fee",
      "relationship_type": "percentage_of",
      "confidence": 0.85,
      "evidence": "Fees row 3 values are exactly 2% of Cash Flows row 5"
    }
  ],
  "ambiguous_relationships": [
    {
      "description": "Distributions row 7 may depend on multiple sources",
      "needs_expert_clarification": true
    }
  ]
}
```

## Critical Rules
- Be conservative. Only flag relationships where the numeric evidence is strong.
- Mark everything else for expert review.
- Do NOT guess — it's better to ask the expert than to assume wrong.""",
        probe_ids=["detect_row_patterns"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="structure_analysis",
                description="JSON output from the Excel Structure Analyzer step",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["dependencies", "analysis", "phase1"],
            "version": "1.0",
        },
    ),
    Directive(
        id="expert_interview_conductor",
        name="Expert Interview Conductor",
        description="Conducts a multi-turn interview with a fund model expert to capture cell relationships, formula logic, and domain-specific rules. This is the core human-in-the-loop directive.",
        content="""You are conducting a structured interview with a fund model expert to reverse-engineer an Excel model.

You have already analyzed the model structure and detected some patterns. Now you need the expert to confirm what's correct, correct what's wrong, and fill in what's missing.

## Interview Strategy

1. **Start with the big picture**: Confirm sheet purposes and calculation order
2. **Work sheet-by-sheet** in calculation order
3. **Handle patterns first** (efficient — one confirmation covers many cells)
4. **Then address individual ambiguous cells**
5. **End with cross-sheet dependencies**

## Question Design Rules

- **NEVER ask about every cell individually.** Group by pattern.
- When you detect a pattern (e.g., "these 5 rows all grow at 3% per period"), ask ONCE: "Is this correct for all of these rows?"
- **Present your hypothesis first.** Let the expert confirm or correct. This is faster than open-ended questions.
- **Use the expert's language.** If they say "promote," don't say "incentive fee allocation."
- **Keep questions focused.** One relationship per question.
- **Track what's been confirmed** vs what's still open.

## Question Format

For each question, structure it as:

**Pattern Confirmation (preferred for efficiency):**
> "I detected that rows 5-9 on the Cash Flows sheet all follow a 5% growth pattern from the prior period. Is this correct for all of these rows? If not, which rows are different and why?"

**Specific Cell Clarification:**
> "For cell D12 on the Distributions sheet (labeled 'Net Distribution'), I see a value that doesn't match any obvious pattern. Can you explain how this cell is calculated?"

**Cross-Sheet Dependency:**
> "The Fees sheet row 3 (Management Fee) appears to be 2% of the Cash Flows sheet row 5 (NAV). Is this correct? Does the 2% rate come from the Assumptions sheet?"

## What You're Capturing

For each relationship, record:
- The Excel formula template (with placeholders like {prior_col}, {row})
- Plain English description
- Dependencies (which other cells/rows feed into this)
- Any exceptions to patterns
- Expert notes or caveats

## Interview State

Track your progress:
- Sheets completed: @variable:sheets_completed (from previous turns)
- Cells confirmed: @variable:cells_confirmed
- Cells remaining: @variable:cells_remaining

## Available Context

Model structure: @variable:structure_analysis
Detected patterns: @variable:detected_patterns
Cross-sheet dependencies: @variable:dependency_map

## Output

After each expert response, update your understanding and either:
1. Ask the next question (if more cells need coverage)
2. Summarize what you've captured and ask for final confirmation

When the interview is complete (all calculated cells covered), output the full set of captured relationships as a structured JSON conforming to the ModelBlueprint schema:

```json
{
  "sheets": [...],
  "row_patterns": [...],
  "cell_overrides": [...],
  "cross_sheet_deps": [...],
  "calculation_order": [...],
  "expert_notes": "..."
}
```

## Critical Rules

- **If the expert contradicts your pattern detection, THE EXPERT IS ALWAYS RIGHT.** Update your records.
- If the expert mentions a concept you don't understand (e.g., "European waterfall"), ask them to explain the calculation steps.
- If a formula involves conditional logic (e.g., hurdle rates, catch-up provisions), capture EVERY branch of the condition.
- Always confirm the seed values: which cells in each row are inputs vs calculated?
- For time-series formulas, always ask: "Does the first period work the same way as subsequent periods, or is it special?"
- **Batch your questions.** Don't ask one cell at a time when you can confirm a pattern for 50 cells with one question.""",
        probe_ids=[],  # No probes - pure interview
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="structure_analysis",
                description="JSON from Excel Structure Analyzer",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="detected_patterns",
                description="JSON from Pattern Detection Probe",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="dependency_map",
                description="JSON from Cross-Sheet Dependency Mapper",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="sheets_completed",
                description="List of sheets already covered in interview",
                required=False,
                default="[]",
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="cells_confirmed",
                description="Count of cells confirmed so far",
                required=False,
                default="0",
                ui_hint="number",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="cells_remaining",
                description="Count of cells still to confirm",
                required=False,
                default="0",
                ui_hint="number",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["interview", "hitl", "phase1", "core"],
            "version": "1.0",
        },
    ),
    Directive(
        id="blueprint_compiler",
        name="Blueprint Compiler",
        description="Compiles all captured relationships from the expert interview into a validated ModelBlueprint ready for Phase 2 reconstruction.",
        content="""You are compiling the results of a fund model reverse-engineering interview into a complete ModelBlueprint.

## Inputs
1. The original structural analysis
2. All confirmed relationships from the expert interview
3. The dependency map

## Your Tasks

### 1. Build SheetSpecs
For each sheet, compile:
- Row patterns (formulas that repeat across columns)
- Cell overrides (individual cells that break the pattern)
- Input vs calculated row classifications

### 2. Resolve Formula Templates
Convert expert descriptions into Excel formula templates:
- "Revenue times margin" → `={col_letter}{revenue_row}*Assumptions!$B${margin_row}`
- "Prior period plus growth" → `={prior_col}{row}*(1+Assumptions!$B${growth_row})`

Use these standard placeholders:
- `{col}` - Current column letter (e.g., D)
- `{col_letter}` - Same as {col}
- `{prior_col}` - Previous column letter (e.g., C)
- `{row}` - Current row number
- `{col_num}` - Current column number (numeric)

### 3. Validate Completeness
Flag any calculated cells that don't have a captured relationship.

### 4. Build Validation Rules
Create sanity checks:
- Balance checks (inflows = outflows + fees)
- Monotonicity checks (cumulative values should increase)
- Bound checks (percentages between 0-100%, fees non-negative)

### 5. Set Calculation Order
Ensure sheets are ordered so dependencies are resolved before they're needed.

## Input Data
- Structure: @variable:structure_analysis
- Interview results: @variable:interview_results
- Dependencies: @variable:dependency_map

## Output Format
Output a complete ModelBlueprint JSON:
```json
{
  "id": "blueprint_<timestamp>",
  "name": "<model_name>",
  "description": "...",
  "version": "1.0",
  "sheets": [...],
  "calculation_order": [...],
  "cross_sheet_deps": [...],
  "cell_relationships": [...],
  "validation_rules": [...],
  "total_calculated_cells": 150,
  "confirmed_cells": 148,
  "inferred_cells": 2
}
```

If any calculated cells are missing coverage, include an "incomplete" section:
```json
{
  "incomplete": [
    {"sheet": "Fees", "row": 12, "col_range": "D-L", "reason": "Not covered in interview"}
  ]
}
```

## Critical Rules
- Be extremely precise with formula templates. A single wrong cell reference will cascade through the entire model.
- Every calculated cell must have either a RowPattern or a CellRelationship entry.
- If coverage is incomplete, flag it — do not guess.""",
        probe_ids=[],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="structure_analysis",
                description="Original structural analysis JSON",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="interview_results",
                description="All captured relationships from expert interview",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="dependency_map",
                description="Cross-sheet dependency graph",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["compilation", "blueprint", "phase1"],
            "version": "1.0",
        },
    ),
    # Phase 2 Directives
    Directive(
        id="fund_model_input_validator",
        name="Fund Model Input Validator",
        description="Validates new input data against the ModelBlueprint schema before reconstruction. Checks that all required inputs are present and within expected ranges.",
        content="""You are validating input data for a fund model reconstruction.

You have a ModelBlueprint that defines exactly which cells are inputs and what type of values they expect. You also have the new input data to validate.

## Your Tasks

### 1. Check Required Inputs
Verify every input cell defined in the blueprint has a corresponding value in the input data.

### 2. Validate Data Types
- Numbers where numbers expected
- Dates where dates expected
- Strings where strings expected

### 3. Flag Outliers
Warn on values outside historically reasonable ranges:
- Growth rates > 50% or < -50% — warn
- Fee rates > 10% — warn
- Negative cash flows in unexpected directions — warn
- Interest rates outside 0-25% — warn

### 4. Check Structure Match
Verify that time period labels match the blueprint structure.

### 5. Report Extra Data
Flag any data in the input that doesn't map to the blueprint.

## Inputs
Blueprint: @variable:model_blueprint
Input data: @variable:input_data

## Output Format
```json
{
  "is_valid": true,
  "missing_inputs": [
    {"sheet": "Assumptions", "row": 3, "col": 2, "description": "Growth Rate"}
  ],
  "type_mismatches": [
    {"sheet": "Cash Flows", "row": 5, "col": 3, "expected": "number", "actual": "string"}
  ],
  "warnings": [
    {"sheet": "Assumptions", "row": 4, "col": 2, "message": "Fee rate of 15% is unusually high"}
  ],
  "extra_data": ["UnknownSheet!R1C1"],
  "validated_input_count": 45,
  "total_expected_inputs": 47
}
```

## Critical Rules
- Set `is_valid: false` only for missing required inputs or type mismatches.
- Warnings don't block validation — they're informational.
- Be specific about what's missing and where.""",
        probe_ids=[],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="model_blueprint",
                description="The ModelBlueprint JSON from Phase 1",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="input_data",
                description="New input data for model reconstruction",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["validation", "phase2"],
            "version": "1.0",
        },
    ),
    Directive(
        id="fund_model_reconstructor",
        name="Fund Model Reconstructor",
        description="Takes a validated ModelBlueprint and input data, generates the complete set of Excel formula specifications for the deterministic compiler.",
        content="""You are reconstructing a fund model from a captured blueprint and new input data.

**IMPORTANT:** You do NOT write the Excel file directly. You generate a structured specification that the Excel compiler probe will use to produce the .xlsx.

## Your Tasks

### 1. Resolve Formula Templates
Take each RowPattern and CellRelationship from the blueprint and resolve all placeholders into concrete Excel formula strings for each cell position.

Example:
- Template: `={prior_col}{row}*(1+Assumptions!$B$3)`
- For row 5, column D: `=C5*(1+Assumptions!$B$3)`

### 2. Handle Edge Cases
- **First column in time series**: Often has a different formula than subsequent columns (seed value or initial calculation)
- **Conditional formulas**: Resolve with actual cell references
- **Cross-sheet references**: Use exact `Sheet!Cell` notation

### 3. Respect Calculation Order
Process sheets in the blueprint's `calculation_order`.

### 4. Generate Compilation Spec
For each cell, output:
```json
{
  "sheet": "Cash Flows",
  "row": 5,
  "col": 3,
  "content_type": "formula",
  "content": "=B5*(1+Assumptions!$B$3)"
}
```

## Inputs
Blueprint: @variable:model_blueprint
Validated input: @variable:validated_input

## Tools Available
- @probe:compile_excel_from_blueprint — Compile your spec into a .xlsx file
- @probe:verify_reconstruction — Verify output against original (if available)

## Process
1. Generate the full compilation spec from the blueprint
2. Invoke the compile_excel_from_blueprint probe with the spec
3. If original file path is provided, invoke verify_reconstruction
4. Report the results

## Output Format
```json
{
  "compilation_report": {
    "output_path": "/path/to/reconstructed.xlsx",
    "sheets_created": ["Assumptions", "Cash Flows", "Fees"],
    "formulas_written": 450,
    "values_written": 47,
    "errors": []
  },
  "verification_report": {
    "pass_rate": 0.99,
    "cells_checked": 450,
    "cells_matching": 446,
    "discrepancies": [...]
  }
}
```

## Critical Rules
- Be precise with cell references. Off-by-one errors cascade.
- Handle the first column of time series rows specially — check if it's a seed or follows the pattern.
- Always use absolute references ($) for cells that shouldn't shift when the formula is applied across columns.""",
        probe_ids=["compile_excel_from_blueprint", "verify_reconstruction"],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="model_blueprint",
                description="The ModelBlueprint JSON from Phase 1",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="validated_input",
                description="Validated input data from the input validator",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="original_file_path",
                description="Path to original file for verification (optional)",
                required=False,
                default=None,
                ui_hint="file",
                ui_options={"accept": ".xlsx"},
                used_by=[],
            ),
            TemplateVariable(
                name="output_path",
                description="Path for the reconstructed output file",
                required=True,
                default=None,
                ui_hint="text",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["reconstruction", "phase2", "core"],
            "version": "1.0",
        },
    ),
    Directive(
        id="fund_model_verification_reporter",
        name="Verification Report Generator",
        description="Analyzes verification results and produces a human-readable report of model accuracy, flagging discrepancies with root cause analysis.",
        content="""You are analyzing the results of a fund model reconstruction verification.

You receive the cell-by-cell comparison report from the verification probe. Your job is to make it actionable.

## Your Tasks

### 1. Summarize Overall Accuracy
Report: "X% of cells match within tolerance (Y of Z cells)"

### 2. Categorize Discrepancies
- **Rounding differences** (< 0.1% deviation) → likely acceptable
- **Formula differences** (> 1% deviation) → needs investigation
- **Missing values** → structural issue

### 3. Trace Root Causes
If cell D12 is wrong, check if it's because a dependency (say, D8) is also wrong.
Report the root cause, not every downstream effect.

### 4. Provide Fix Recommendations
For each significant discrepancy:
> "Cell Distributions!D12 expected 1,250,000 but got 1,247,500 (0.2% deviation). This traces to row 8 where the fee calculation uses a rounded rate. Consider: adjust tolerance or update blueprint formula to match rounding behavior."

### 5. Assess Overall Confidence
Is this model:
- **PASS**: Safe to use (>99% match, no material discrepancies)
- **PASS WITH NOTES**: Usable with documented limitations (>95% match)
- **NEEDS REVIEW**: Minor fixes needed (<95% or some formula issues)
- **RE-INTERVIEW**: Significant gaps, blueprint needs revision

## Inputs
Verification report: @variable:verification_results
Blueprint: @variable:model_blueprint

## Output Format
```markdown
# Verification Report

## Summary
- **Overall Accuracy**: 98.5% (443/450 cells within 1% tolerance)
- **Verdict**: PASS WITH NOTES

## Discrepancy Categories
| Category | Count | Severity |
|----------|-------|----------|
| Rounding | 5 | Low |
| Formula | 2 | Medium |
| Missing | 0 | - |

## Root Cause Analysis
### Issue 1: Fee Calculation Rounding
- **Affected Cells**: Fees!D3:L3 (9 cells)
- **Root Cause**: Blueprint uses unrounded rate; original model rounds to 2 decimals
- **Recommendation**: Update blueprint formula to include ROUND function

## Recommendations
1. Accept current reconstruction with noted rounding differences
2. Optional: Update blueprint to match rounding behavior if exact match required

## Data Gaps
None identified.
```

## Critical Rules
- Trace discrepancies to their source — don't just list symptoms.
- Be specific about which cells and formulas are affected.
- Provide actionable recommendations, not just problem descriptions.""",
        probe_ids=[],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="verification_results",
                description="Cell-by-cell comparison from the verification probe",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="model_blueprint",
                description="The ModelBlueprint for context on relationships",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["verification", "reporting", "phase2"],
            "version": "1.0",
        },
    ),
    # Interview Progress Extractor (extracts structured metrics from conversational interview)
    Directive(
        id="interview_progress_extractor",
        name="Interview Progress Extractor",
        description="Extracts structured progress metrics from the conversational interview history. Bridges the gap between free-form expert dialogue and the structured metrics the EvalStar needs.",
        content="""You are extracting structured progress metrics from a fund model interview transcript.

## Your Job

Read the interview history (AI questions + expert responses) and the original structure analysis.
Count what has been confirmed vs what remains, and output structured metrics.

## Inputs
- Structure analysis: @variable:structure_analysis (tells you what calculated cells exist)
- Interview transcript: @variable:interview_transcript (the Q&A history)

## What to Count

From the structure analysis, identify:
1. All sheets with calculated rows
2. Total number of calculated rows across all sheets
3. For each row: whether it's input or calculated

From the interview transcript, identify:
1. Which rows have confirmed patterns (expert said "correct", "confirmed", "yes")
2. Which cross-sheet dependencies have been confirmed
3. Which conditional formulas have all branches captured
4. Any rows still needing clarification

## Output Format

Output ONLY this JSON structure (no other text):

```json
{
  "coverage_summary": {
    "total_calculated_rows": 15,
    "confirmed_rows": 12,
    "remaining_rows": 3,
    "sheets_complete": ["Assumptions", "Cash Flows"],
    "sheets_incomplete": ["NAV"]
  },
  "cross_sheet_status": {
    "total_dependencies": 5,
    "confirmed": 4,
    "unconfirmed": ["NAV->CashFlows.Distributions"]
  },
  "conditional_status": {
    "total_conditionals": 2,
    "fully_captured": 1,
    "partial": ["Distributions: missing else branch"]
  },
  "confidence_flags": {
    "low_confidence_items": [],
    "expert_overrides": 2
  },
  "next_focus": "NAV sheet row 9 (Above Hurdle?) needs branch confirmation",
  "interview_complete": false
}
```

## Rules

- Be precise. Count actual confirmations in the transcript.
- A row is "confirmed" if the expert explicitly agreed to the pattern OR provided the formula.
- If the expert said "correct for all periods" about a row pattern, count ALL cells in that row as confirmed.
- If unsure whether something was confirmed, mark it as unconfirmed (be conservative).
- Set `interview_complete: true` ONLY if: all calculated rows confirmed, all dependencies confirmed, all conditionals have all branches.""",
        probe_ids=[],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="structure_analysis",
                description="JSON from Excel Structure Analyzer showing all sheets and rows",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="interview_transcript",
                description="Full transcript of interview Q&A including expert responses",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["extraction", "metrics", "phase1"],
            "version": "1.0",
        },
    ),
    # Interview Evaluation Directive (for EvalStar loop)
    Directive(
        id="interview_completeness_evaluator",
        name="Interview Completeness Evaluator",
        description="Evaluates whether the expert interview has covered all calculated cells. Used by EvalStar to determine loop vs continue.",
        content="""You are evaluating whether the fund model interview is complete.

## Check These Criteria

1. **Cell Coverage**: Every calculated row has either a confirmed RowPattern or individual CellRelationships
2. **Cross-Sheet Dependencies**: Every cross-sheet dependency has been confirmed by the expert
3. **Confidence Levels**: No relationships have confidence < 0.5 without expert confirmation
4. **Conditional Logic**: All conditional formulas (waterfalls, hurdle rates) have all branches captured

## Inputs
Interview state: @variable:interview_state
Blueprint progress: @variable:blueprint_progress

## Decision Rules

If ANY of these are incomplete → decision: "loop"
If ALL are complete → decision: "continue"

## Output Format
```json
{
  "decision": "loop",
  "reasoning": "3 calculated rows on Fees sheet still need coverage",
  "coverage_summary": {
    "total_calculated_cells": 150,
    "confirmed": 140,
    "remaining": 10,
    "sheets_complete": ["Assumptions", "Cash Flows"],
    "sheets_incomplete": ["Fees", "Distributions"]
  },
  "next_priority": "Focus on Fees sheet rows 8-12 which have no pattern match"
}
```

## Critical Rules
- Be precise about what's missing.
- Provide clear guidance on what the next interview iteration should focus on.
- Only return "continue" when you're confident the blueprint is complete.""",
        probe_ids=[],
        reference_ids=[],
        template_variables=[
            TemplateVariable(
                name="interview_state",
                description="Current state of the interview (confirmed relationships, Q&A history)",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
            TemplateVariable(
                name="blueprint_progress",
                description="Current blueprint completeness metrics",
                required=True,
                default=None,
                ui_hint="textarea",
                ui_options=None,
                used_by=[],
            ),
        ],
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["eval", "interview", "phase1"],
            "version": "1.0",
        },
    ),
]

# ============================================================================
# Fund Model Reverse Engineering — Stars
# ============================================================================

FUND_MODEL_STARS = [
    # Phase 1 Stars
    WorkerStar(
        id="excel_parser_star",
        name="Excel Structure Parser",
        directive_id="excel_structure_analysis",
        config={"temperature": 0.1, "max_tokens": 4000},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "1", "role": "parser"},
        probe_ids=["parse_excel_structure", "analyze_sheet_structure"],
        max_iterations=3,
    ),
    WorkerStar(
        id="dependency_mapper_star",
        name="Cross-Sheet Dependency Mapper",
        directive_id="cross_sheet_dependency_mapping",
        config={"temperature": 0.2, "max_tokens": 4000},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "1", "role": "dependency_mapper"},
        probe_ids=["detect_row_patterns"],
        max_iterations=5,
    ),
    WorkerStar(
        id="expert_interviewer_star",
        name="Expert Interviewer",
        directive_id="expert_interview_conductor",
        config={"temperature": 0.3, "max_tokens": 8000, "allow_multi_turn": True},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "1", "role": "interviewer", "hitl": True},
        probe_ids=[],  # No probes - pure interview
        max_iterations=50,  # Allow many turns for long interviews
    ),
    WorkerStar(
        id="interview_progress_extractor_star",
        name="Interview Progress Extractor",
        directive_id="interview_progress_extractor",
        config={"temperature": 0.1, "max_tokens": 2000},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "1", "role": "extractor"},
        probe_ids=[],  # No probes - pure extraction
        max_iterations=1,
    ),
    EvalStar(
        id="interview_eval_star",
        name="Interview Completeness Evaluator",
        directive_id="interview_completeness_evaluator",
        config={"threshold": 1.0},  # Require 100% coverage
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "1", "role": "evaluator"},
        probe_ids=[],
    ),
    WorkerStar(
        id="blueprint_compiler_star",
        name="Blueprint Compiler",
        directive_id="blueprint_compiler",
        config={"temperature": 0.1, "max_tokens": 8000},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "1", "role": "compiler"},
        probe_ids=[],
        max_iterations=3,
    ),
    # Phase 2 Stars
    WorkerStar(
        id="input_validator_star",
        name="Input Validator",
        directive_id="fund_model_input_validator",
        config={"temperature": 0.1, "max_tokens": 2000},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "2", "role": "validator"},
        probe_ids=[],
        max_iterations=1,
    ),
    WorkerStar(
        id="reconstructor_star",
        name="Model Reconstructor",
        directive_id="fund_model_reconstructor",
        config={"temperature": 0.1, "max_tokens": 8000},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "2", "role": "reconstructor"},
        probe_ids=["compile_excel_from_blueprint", "verify_reconstruction"],
        max_iterations=5,
    ),
    SynthesisStar(
        id="verification_reporter_star",
        name="Verification Reporter",
        directive_id="fund_model_verification_reporter",
        config={"format": "markdown", "temperature": 0.2},
        ai_generated=False,
        metadata={"domain": "fund_models", "phase": "2", "role": "reporter"},
        probe_ids=[],
    ),
]

# ============================================================================
# Fund Model Reverse Engineering — Constellations
# ============================================================================

FUND_MODEL_CONSTELLATIONS = [
    # Phase 1: Model Learning Pipeline
    Constellation(
        id="fund_model_learning",
        name="Fund Model Learning Pipeline",
        description="""Reverse-engineers a fund model by analyzing its structure and conducting an expert interview.
Produces a reusable ModelBlueprint for autonomous reconstruction.

Flow:
1. Parse Excel structure
2. Map cross-sheet dependencies
3. Conduct expert interview (HITL with loop for completeness)
4. Compile blueprint

The interview step uses an EvalStar loop to ensure all calculated cells are covered.""",
        start=StartNode(
            id="start",
            position=Position(x=0, y=200),
        ),
        end=EndNode(
            id="end",
            position=Position(x=1200, y=200),
        ),
        nodes=[
            StarNode(
                id="node_excel_parser",
                star_id="excel_parser_star",
                position=Position(x=100, y=200),
                display_name="Parse Excel Structure",
                requires_confirmation=False,
            ),
            StarNode(
                id="node_dependency_mapper",
                star_id="dependency_mapper_star",
                position=Position(x=250, y=200),
                display_name="Map Dependencies",
                requires_confirmation=False,
            ),
            StarNode(
                id="node_expert_interview",
                star_id="expert_interviewer_star",
                position=Position(x=400, y=200),
                display_name="Expert Interview",
                requires_confirmation=True,
                confirmation_prompt="The AI has analyzed the model structure and prepared interview questions. Ready to begin the expert interview? The expert should be present for this step.",
            ),
            StarNode(
                id="node_progress_extractor",
                star_id="interview_progress_extractor_star",
                position=Position(x=550, y=200),
                display_name="Extract Progress Metrics",
                requires_confirmation=False,
            ),
            StarNode(
                id="node_interview_eval",
                star_id="interview_eval_star",
                position=Position(x=700, y=200),
                display_name="Check Completeness",
                requires_confirmation=False,
            ),
            StarNode(
                id="node_blueprint_compiler",
                star_id="blueprint_compiler_star",
                position=Position(x=900, y=200),
                display_name="Compile Blueprint",
                requires_confirmation=True,
                confirmation_prompt="Blueprint compiled. Review the output for completeness before finalizing. Any cells still marked as unconfirmed?",
            ),
        ],
        edges=[
            Edge(id="e1", source="start", target="node_excel_parser"),
            Edge(id="e2", source="node_excel_parser", target="node_dependency_mapper"),
            Edge(id="e3", source="node_dependency_mapper", target="node_expert_interview"),
            Edge(id="e4", source="node_expert_interview", target="node_progress_extractor"),
            Edge(id="e4b", source="node_progress_extractor", target="node_interview_eval"),
            # EvalStar loop: if not complete, go back to interview
            Edge(id="e5_loop", source="node_interview_eval", target="node_expert_interview", condition="decision == 'loop'"),
            # EvalStar continue: if complete, proceed to compiler
            Edge(id="e5_continue", source="node_interview_eval", target="node_blueprint_compiler", condition="decision == 'continue'"),
            Edge(id="e6", source="node_blueprint_compiler", target="end"),
        ],
        max_loop_iterations=10,  # Allow up to 10 interview iterations
        max_retry_attempts=2,
        retry_delay_base=2.0,
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["learning", "reverse-engineering", "phase1"],
            "estimated_duration": "30-60 minutes (depends on model complexity and expert availability)",
            "hitl_pause_points": [
                "Before Expert Interview - confirms expert is present",
                "After Blueprint Compilation - expert reviews completeness",
            ],
        },
    ),
    # Phase 2: Model Reconstruction Pipeline
    Constellation(
        id="fund_model_reconstruction",
        name="Fund Model Reconstruction Pipeline",
        description="""Reconstructs a fund model from a stored blueprint and new input data.
Produces a verified .xlsx with formulas.

Flow:
1. Validate inputs against blueprint
2. Reconstruct model with formulas
3. Verify and report accuracy""",
        start=StartNode(
            id="start",
            position=Position(x=0, y=200),
        ),
        end=EndNode(
            id="end",
            position=Position(x=1000, y=200),
        ),
        nodes=[
            StarNode(
                id="node_input_validator",
                star_id="input_validator_star",
                position=Position(x=200, y=200),
                display_name="Validate Inputs",
                requires_confirmation=False,
            ),
            StarNode(
                id="node_reconstructor",
                star_id="reconstructor_star",
                position=Position(x=500, y=200),
                display_name="Reconstruct Model",
                requires_confirmation=False,
            ),
            StarNode(
                id="node_verification",
                star_id="verification_reporter_star",
                position=Position(x=800, y=200),
                display_name="Verify & Report",
                requires_confirmation=False,
            ),
        ],
        edges=[
            Edge(id="e1", source="start", target="node_input_validator"),
            Edge(id="e2", source="node_input_validator", target="node_reconstructor"),
            Edge(id="e3", source="node_reconstructor", target="node_verification"),
            Edge(id="e4", source="node_verification", target="end"),
        ],
        max_loop_iterations=1,  # No loops in reconstruction
        max_retry_attempts=3,
        retry_delay_base=2.0,
        metadata={
            "author": "rishi.meka",
            "domain": "fund_models",
            "tags": ["reconstruction", "automation", "phase2"],
            "estimated_duration": "2-5 minutes",
        },
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

        # Combine all directives
        all_directives = DD_SUB_DIRECTIVES + DD_WORKER_DIRECTIVES + DIRECTIVES + FUND_MODEL_DIRECTIVES

        # Seed directives
        print(f"Seeding {len(all_directives)} directives...")
        for directive in all_directives:
            await persistence.create_directive(directive)
            print(f"  Created directive: {directive.id} - {directive.name}")

        # Combine all stars
        all_stars = DD_STARS + STARS + FUND_MODEL_STARS

        # Seed stars
        print(f"Seeding {len(all_stars)} stars...")
        for star in all_stars:
            await persistence.create_star(star)
            print(f"  Created star: {star.id} - {star.name} ({star.type})")

        # Combine all constellations
        all_constellations = DD_CONSTELLATIONS + CONSTELLATIONS + FUND_MODEL_CONSTELLATIONS

        # Seed constellations
        print(f"Seeding {len(all_constellations)} constellations...")
        for constellation in all_constellations:
            await persistence.create_constellation(constellation)
            print(f"  Created constellation: {constellation.id} - {constellation.name}")

        print("\nDatabase seeded successfully!")
        print(f"  Directives: {len(all_directives)}")
        print(f"    - Due Diligence Sub-Directives: {len(DD_SUB_DIRECTIVES)}")
        print(f"    - Due Diligence Worker Directives: {len(DD_WORKER_DIRECTIVES)}")
        print(f"    - Original Directives: {len(DIRECTIVES)}")
        print(f"    - Fund Model Directives: {len(FUND_MODEL_DIRECTIVES)}")
        print(f"  Stars: {len(all_stars)}")
        print(f"    - Due Diligence Stars: {len(DD_STARS)}")
        print(f"    - Original Stars: {len(STARS)}")
        print(f"    - Fund Model Stars: {len(FUND_MODEL_STARS)}")
        print(f"  Constellations: {len(all_constellations)}")
        print(f"    - Due Diligence Constellations: {len(DD_CONSTELLATIONS)}")
        print(f"    - Original Constellations: {len(CONSTELLATIONS)}")
        print(f"    - Fund Model Constellations: {len(FUND_MODEL_CONSTELLATIONS)}")

    finally:
        await persistence.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
