"""Due Diligence probes for investment research benchmark.

Provides probes for the Cross-Source Investment Due Diligence benchmark:
- SEC Filings Search
- Financial Data API
- Earnings Call Transcripts
- News Search
- Social Sentiment Analysis
- Analyst Ratings
- Legal Case Database
- Regulatory Filings Search
- Market Research Database

These probes are designed to test Astro's tool-scoping capabilities where
different Stars have access to different subsets of probes.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from astro.core.probes.decorator import probe


# =============================================================================
# Realistic Company Data for Benchmark
# =============================================================================

# Real financial data for benchmark companies (as of late 2024)
# This ensures the benchmark tests orchestration quality, not random data generation

COMPANY_FINANCIALS = {
    # Airbnb - the primary benchmark company
    "airbnb": {
        "ticker": "ABNB",
        "quarterly": {
            "revenue": 3_730_000_000,  # Q3 2024: $3.73B
            "net_income": 1_370_000_000,  # Q3 2024: $1.37B
            "eps": 2.13,
            "gross_margin": "82.5%",
            "operating_margin": "18.2%",
            "free_cash_flow": 1_100_000_000,
        },
        "annual": {
            "revenue": 10_500_000_000,  # ~$10.5B TTM
            "net_income": 2_800_000_000,  # ~$2.8B TTM
            "eps": 4.35,
            "gross_margin": "82.1%",
            "operating_margin": "15.8%",
            "free_cash_flow": 3_800_000_000,
        },
        "ratios": {
            "pe_ratio": 22.5,
            "ev_ebitda": 18.2,
            "debt_to_equity": 0.42,
            "current_ratio": 1.85,
            "price_to_sales": 8.5,
            "return_on_equity": "45.2%",
        },
        "stock": {
            "price": 135.50,
            "market_cap": 87_000_000_000,
            "shares_outstanding": 642_000_000,
        },
    },
    # Tesla - high growth, high valuation
    "tesla": {
        "ticker": "TSLA",
        "quarterly": {
            "revenue": 25_180_000_000,  # Q3 2024: $25.18B
            "net_income": 2_170_000_000,  # Q3 2024: $2.17B
            "eps": 0.68,
            "gross_margin": "19.8%",
            "operating_margin": "10.8%",
            "free_cash_flow": 2_740_000_000,
        },
        "annual": {
            "revenue": 96_770_000_000,  # FY2023: $96.77B
            "net_income": 14_970_000_000,
            "eps": 4.31,
            "gross_margin": "18.2%",
            "operating_margin": "9.2%",
            "free_cash_flow": 4_360_000_000,
        },
        "ratios": {
            "pe_ratio": 72.5,
            "ev_ebitda": 48.3,
            "debt_to_equity": 0.11,
            "current_ratio": 1.73,
            "price_to_sales": 8.2,
            "return_on_equity": "22.5%",
        },
        "stock": {
            "price": 248.50,
            "market_cap": 792_000_000_000,
            "shares_outstanding": 3_190_000_000,
        },
    },
    # Apple - mega cap, steady performer
    "apple": {
        "ticker": "AAPL",
        "quarterly": {
            "revenue": 94_930_000_000,  # Q4 FY2024: $94.93B
            "net_income": 23_960_000_000,
            "eps": 1.57,
            "gross_margin": "46.2%",
            "operating_margin": "30.7%",
            "free_cash_flow": 26_810_000_000,
        },
        "annual": {
            "revenue": 383_290_000_000,  # FY2024
            "net_income": 97_000_000_000,
            "eps": 6.42,
            "gross_margin": "45.9%",
            "operating_margin": "30.1%",
            "free_cash_flow": 108_800_000_000,
        },
        "ratios": {
            "pe_ratio": 31.2,
            "ev_ebitda": 24.5,
            "debt_to_equity": 1.87,
            "current_ratio": 0.99,
            "price_to_sales": 7.8,
            "return_on_equity": "157.4%",
        },
        "stock": {
            "price": 225.30,
            "market_cap": 3_450_000_000_000,
            "shares_outstanding": 15_330_000_000,
        },
    },
    # Meta - advertising giant, AI pivot
    "meta": {
        "ticker": "META",
        "quarterly": {
            "revenue": 40_590_000_000,  # Q3 2024: $40.59B
            "net_income": 15_690_000_000,
            "eps": 6.03,
            "gross_margin": "81.8%",
            "operating_margin": "43.0%",
            "free_cash_flow": 15_520_000_000,
        },
        "annual": {
            "revenue": 149_780_000_000,  # TTM
            "net_income": 52_120_000_000,
            "eps": 20.01,
            "gross_margin": "80.7%",
            "operating_margin": "38.5%",
            "free_cash_flow": 52_100_000_000,
        },
        "ratios": {
            "pe_ratio": 28.5,
            "ev_ebitda": 17.8,
            "debt_to_equity": 0.30,
            "current_ratio": 2.68,
            "price_to_sales": 9.2,
            "return_on_equity": "35.4%",
        },
        "stock": {
            "price": 567.80,
            "market_cap": 1_440_000_000_000,
            "shares_outstanding": 2_540_000_000,
        },
    },
}

# Real analyst ratings and targets
COMPANY_ANALYST_DATA = {
    "airbnb": {
        "consensus_rating": "buy",
        "price_target_avg": 155.00,
        "price_target_low": 120.00,
        "price_target_high": 200.00,
        "analyst_count": 42,
        "ratings": {"strong_buy": 8, "buy": 18, "hold": 14, "sell": 2, "strong_sell": 0},
        "eps_current_year": 4.55,
        "eps_next_year": 5.20,
    },
    "tesla": {
        "consensus_rating": "hold",
        "price_target_avg": 225.00,
        "price_target_low": 85.00,
        "price_target_high": 400.00,
        "analyst_count": 52,
        "ratings": {"strong_buy": 6, "buy": 12, "hold": 22, "sell": 8, "strong_sell": 4},
        "eps_current_year": 2.45,
        "eps_next_year": 3.10,
    },
    "apple": {
        "consensus_rating": "buy",
        "price_target_avg": 245.00,
        "price_target_low": 180.00,
        "price_target_high": 300.00,
        "analyst_count": 48,
        "ratings": {"strong_buy": 12, "buy": 22, "hold": 12, "sell": 2, "strong_sell": 0},
        "eps_current_year": 6.75,
        "eps_next_year": 7.35,
    },
    "meta": {
        "consensus_rating": "buy",
        "price_target_avg": 625.00,
        "price_target_low": 480.00,
        "price_target_high": 750.00,
        "analyst_count": 58,
        "ratings": {"strong_buy": 18, "buy": 28, "hold": 10, "sell": 2, "strong_sell": 0},
        "eps_current_year": 21.50,
        "eps_next_year": 25.80,
    },
}

# Real legal/regulatory issues
COMPANY_LEGAL_DATA = {
    "airbnb": [
        {
            "case_type": "regulatory",
            "title": "NYC Short-Term Rental Registration Law",
            "status": "active",
            "filed_date": "2023-09-05",
            "court": "NYC Department of Buildings",
            "amount": None,
            "summary": "NYC Local Law 18 requires hosts to register with the city and be present during stays. Airbnb sued to block but lost. Has significantly reduced NYC listings.",
        },
        {
            "case_type": "class_action",
            "title": "Airbnb Host Fee Antitrust Litigation",
            "status": "active",
            "filed_date": "2023-03-15",
            "court": "US District Court, Northern District of California",
            "amount": "$250M",
            "summary": "Class action alleging Airbnb's fee structure and price parity clauses violate antitrust laws.",
        },
        {
            "case_type": "regulatory",
            "title": "EU Digital Services Act Compliance",
            "status": "pending",
            "filed_date": "2024-02-17",
            "court": "European Commission",
            "amount": None,
            "summary": "Investigation into Airbnb's compliance with DSA transparency and content moderation requirements.",
        },
    ],
    "tesla": [
        {
            "case_type": "regulatory",
            "title": "NHTSA Autopilot Investigation",
            "status": "active",
            "filed_date": "2021-08-16",
            "court": "NHTSA",
            "amount": None,
            "summary": "Ongoing investigation into Tesla Autopilot crashes involving emergency vehicles. Multiple recalls issued.",
        },
        {
            "case_type": "class_action",
            "title": "Tesla Racial Discrimination Class Action",
            "status": "active",
            "filed_date": "2022-06-02",
            "court": "US District Court, Northern District of California",
            "amount": "$1B+",
            "summary": "Class action lawsuit alleging widespread racial discrimination at Fremont factory.",
        },
        {
            "case_type": "regulatory",
            "title": "SEC Investigation - Musk Tweets",
            "status": "settled",
            "filed_date": "2018-09-27",
            "court": "SEC",
            "amount": "$40M",
            "summary": "Settlement over Musk's 'funding secured' tweets. Musk and Tesla each paid $20M. Musk stepped down as chairman.",
        },
    ],
    "apple": [
        {
            "case_type": "regulatory",
            "title": "DOJ Antitrust Lawsuit",
            "status": "active",
            "filed_date": "2024-03-21",
            "court": "US District Court, District of New Jersey",
            "amount": None,
            "summary": "DOJ alleges Apple maintains illegal monopoly over smartphone market through App Store restrictions, messaging lock-in, and accessory limitations.",
        },
        {
            "case_type": "lawsuit",
            "title": "Epic Games v. Apple",
            "status": "active",
            "filed_date": "2020-08-13",
            "court": "Ninth Circuit Court of Appeals",
            "amount": None,
            "summary": "Epic challenged Apple's App Store policies. Apple won most claims but must allow alternative payment links. Appeals ongoing.",
        },
        {
            "case_type": "regulatory",
            "title": "EU Digital Markets Act - App Store",
            "status": "active",
            "filed_date": "2024-06-24",
            "court": "European Commission",
            "amount": "€500M+",
            "summary": "EU preliminary finding that Apple's App Store rules violate DMA by preventing app developers from steering users to alternative offers.",
        },
    ],
    "meta": [
        {
            "case_type": "regulatory",
            "title": "FTC Antitrust Lawsuit",
            "status": "active",
            "filed_date": "2020-12-09",
            "court": "US District Court, District of Columbia",
            "amount": None,
            "summary": "FTC alleges Meta maintains illegal monopoly through acquisitions of Instagram and WhatsApp. Seeking divestiture.",
        },
        {
            "case_type": "settlement",
            "title": "Cambridge Analytica Privacy Settlement",
            "status": "settled",
            "filed_date": "2019-07-24",
            "court": "FTC",
            "amount": "$5B",
            "summary": "Record-setting FTC settlement over privacy violations related to Cambridge Analytica data sharing.",
        },
        {
            "case_type": "regulatory",
            "title": "EU GDPR Violations - Behavioral Advertising",
            "status": "settled",
            "filed_date": "2023-01-04",
            "court": "Irish Data Protection Commission",
            "amount": "€390M",
            "summary": "Fine for forcing users to accept personalized ads as condition of using Facebook and Instagram.",
        },
    ],
}

# Real news themes for each company
COMPANY_NEWS_THEMES = {
    "airbnb": {
        "positive": [
            "Airbnb reports record Q3 bookings, gross booking value up 10% YoY",
            "Airbnb expands Icons experiences program with celebrity-hosted stays",
            "Airbnb stock rises on strong travel demand outlook for 2025",
        ],
        "negative": [
            "NYC listings drop 80% after short-term rental law enforcement begins",
            "Barcelona bans short-term tourist rentals, Airbnb faces European pressure",
            "Airbnb faces antitrust scrutiny over host fee structure",
        ],
        "neutral": [
            "Airbnb launches Co-Host Network to help hosts manage properties",
            "Airbnb CEO Brian Chesky discusses AI integration plans at conference",
            "Travel industry analysts compare Airbnb, Booking Holdings strategies",
        ],
    },
    "tesla": {
        "positive": [
            "Tesla Cybertruck deliveries ramp up, production exceeds expectations",
            "Tesla FSD v12 shows significant improvement in real-world testing",
            "Tesla Megapack orders surge as utility-scale storage demand grows",
        ],
        "negative": [
            "Tesla recalls 2 million vehicles over Autopilot safety concerns",
            "Tesla faces renewed NHTSA scrutiny after fatal Autopilot crashes",
            "Tesla China sales decline amid BYD and local EV competition",
        ],
        "neutral": [
            "Tesla unveils refreshed Model Y at Los Angeles Auto Show",
            "Elon Musk discusses Tesla's robotaxi timeline at shareholder meeting",
            "Analysts debate Tesla valuation amid EV market maturation",
        ],
    },
    "apple": {
        "positive": [
            "Apple Intelligence drives strong iPhone 16 Pro demand",
            "Apple Services revenue hits record $25B in Q4",
            "Apple Vision Pro enterprise adoption exceeds expectations",
        ],
        "negative": [
            "DOJ antitrust lawsuit poses existential threat to App Store model",
            "Apple faces €500M EU fine over App Store anti-steering rules",
            "iPhone sales decline in China as Huawei gains market share",
        ],
        "neutral": [
            "Apple announces M4 MacBook Pro with enhanced AI capabilities",
            "Apple delays smart home display launch to 2025",
            "Tim Cook discusses Apple's approach to generative AI",
        ],
    },
    "meta": {
        "positive": [
            "Meta ad revenue surges 23% as Reels monetization improves",
            "Meta AI assistant reaches 500 million monthly users",
            "Meta Reality Labs losses narrow as Quest 3 sales grow",
        ],
        "negative": [
            "FTC antitrust trial threatens Instagram, WhatsApp divestiture",
            "Meta faces EU investigation over election misinformation policies",
            "Meta layoffs continue as efficiency drive enters third year",
        ],
        "neutral": [
            "Meta unveils Orion AR glasses prototype at Connect conference",
            "Zuckerberg outlines Meta's AI infrastructure investments",
            "Meta Threads reaches 200 million monthly active users",
        ],
    },
}


def _normalize_company_name(company: str) -> str:
    """Normalize company name to match our data keys."""
    normalized = company.lower().strip()
    # Handle common variations
    variations = {
        "abnb": "airbnb",
        "tsla": "tesla",
        "aapl": "apple",
        "meta platforms": "meta",
        "facebook": "meta",
        "fb": "meta",
    }
    return variations.get(normalized, normalized)


def _get_company_data(company: str, data_dict: dict, default_generator=None):
    """Get company data from dict, or generate if not found."""
    normalized = _normalize_company_name(company)
    if normalized in data_dict:
        return data_dict[normalized], True
    elif default_generator:
        return default_generator(company), False
    return None, False


def _generate_fallback_financial_data(company: str) -> Dict[str, Any]:
    """Generate plausible financial data for unknown companies."""
    # Use more reasonable ranges for unknown companies
    base_revenue = random.randint(1, 20) * 1_000_000_000  # $1B-$20B
    margin = random.uniform(0.05, 0.15)

    return {
        "company": company,
        "quarterly": {
            "revenue": int(base_revenue / 4),
            "net_income": int(base_revenue / 4 * margin),
            "eps": round(random.uniform(0.5, 5), 2),
            "gross_margin": f"{random.uniform(30, 60):.1f}%",
            "operating_margin": f"{random.uniform(5, 25):.1f}%",
            "free_cash_flow": int(base_revenue / 4 * 0.1),
        },
        "annual": {
            "revenue": base_revenue,
            "net_income": int(base_revenue * margin),
            "eps": round(random.uniform(2, 15), 2),
            "gross_margin": f"{random.uniform(30, 60):.1f}%",
            "operating_margin": f"{random.uniform(5, 25):.1f}%",
            "free_cash_flow": int(base_revenue * 0.08),
        },
        "ratios": {
            "pe_ratio": round(random.uniform(12, 35), 1),
            "ev_ebitda": round(random.uniform(8, 20), 1),
            "debt_to_equity": round(random.uniform(0.3, 1.5), 2),
            "current_ratio": round(random.uniform(1.0, 2.5), 2),
            "price_to_sales": round(random.uniform(1, 5), 1),
            "return_on_equity": f"{random.uniform(10, 25):.1f}%",
        },
        "stock": {
            "price": round(random.uniform(20, 200), 2),
            "market_cap": base_revenue * random.randint(2, 8),
            "shares_outstanding": random.randint(100, 500) * 1_000_000,
        },
        "_generated": True,  # Flag that this is not real data
    }


def _generate_sec_filing(
    company: str, filing_type: str, days_ago: int = None
) -> Dict[str, Any]:
    """Generate SEC filing data."""
    if days_ago is None:
        days_ago = random.randint(1, 90)
    filing_date = datetime.now() - timedelta(days=days_ago)

    # Use real CIKs for known companies
    cik_map = {
        "airbnb": "1559720",
        "tesla": "1318605",
        "apple": "320193",
        "meta": "1326801",
    }
    normalized = _normalize_company_name(company)
    cik = cik_map.get(normalized, f"{random.randint(1000000, 9999999)}")

    return {
        "company": company,
        "filing_type": filing_type,
        "filing_date": filing_date.strftime("%Y-%m-%d"),
        "accession_number": f"0001{cik[:6]}-24-{random.randint(100000, 999999):06d}",
        "cik": cik,
        "form_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type}",
        "summary": f"This {filing_type} filing for {company} contains the company's quarterly/annual report with detailed financial statements, management discussion and analysis, and risk factors.",
    }


# =============================================================================
# Financial Data Probes
# =============================================================================


@probe
def search_sec_filings(
    company: str,
    filing_type: str = "10-K",
    date_range: str = "1y",
) -> Dict[str, Any]:
    """Search and retrieve SEC filings (10-K, 10-Q, 8-K, proxy statements) for a company.

    Accesses the SEC EDGAR database to retrieve regulatory filings including
    annual reports (10-K), quarterly reports (10-Q), current reports (8-K),
    and proxy statements (DEF 14A).

    Args:
        company: Company name or ticker symbol to search
        filing_type: Type of filing (10-K, 10-Q, 8-K, DEF14A). Default: 10-K
        date_range: Time range for search (1m, 3m, 6m, 1y, 3y). Default: 1y

    Returns:
        Dictionary containing:
        - filings: List of filing objects with date, type, url, summary
        - count: Number of filings found
        - company: The company searched
    """
    # Determine number of filings based on type and date range
    range_multiplier = {"1m": 1, "3m": 1, "6m": 2, "1y": 4, "3y": 12}.get(date_range, 4)
    type_multiplier = {"10-K": 1, "10-Q": 3, "8-K": 4, "DEF14A": 1}.get(filing_type, 2)

    num_filings = min(type_multiplier * (range_multiplier // 4 + 1), 10)
    num_filings = max(1, num_filings)

    # Generate filings with realistic spacing
    filings = []
    for i in range(num_filings):
        days_ago = i * (365 // type_multiplier // max(1, range_multiplier // 4))
        filings.append(_generate_sec_filing(company, filing_type, days_ago + random.randint(0, 30)))

    return {
        "filings": filings,
        "count": len(filings),
        "company": company,
        "filing_type": filing_type,
        "date_range": date_range,
    }


@probe
def get_financial_data(
    company: str,
    metrics: Optional[List[str]] = None,
    period: str = "annual",
) -> Dict[str, Any]:
    """Retrieve quantitative financial data: revenue, earnings, balance sheet, ratios.

    Fetches structured financial metrics from financial data APIs including
    income statement, balance sheet, cash flow, and valuation metrics.

    Args:
        company: Company name or ticker symbol
        metrics: List of specific metrics to retrieve. If None, returns all.
                 Options: revenue, net_income, eps, pe_ratio, ev_ebitda,
                 debt_to_equity, current_ratio, free_cash_flow, margins
        period: Time period (annual, quarterly, ttm). Default: annual

    Returns:
        Dictionary containing:
        - data: Financial metrics object with requested data
        - company: The company queried
        - period: The time period
        - as_of_date: Data freshness date
    """
    company_data, is_known = _get_company_data(
        company, COMPANY_FINANCIALS, _generate_fallback_financial_data
    )

    # Build the response data based on period
    if period == "quarterly":
        period_data = company_data.get("quarterly", company_data.get("annual", {}))
    elif period == "ttm":
        # TTM is similar to annual for our purposes
        period_data = company_data.get("annual", {})
    else:
        period_data = company_data.get("annual", {})

    # Combine period data with ratios
    data = {"company": company}
    data.update(period_data)
    if "ratios" in company_data:
        data.update(company_data["ratios"])

    # Filter to requested metrics if specified
    if metrics:
        filtered_data = {"company": company}
        for metric in metrics:
            if metric in data:
                filtered_data[metric] = data[metric]
            elif metric == "margins":
                # Include margin-related fields
                for key in ["gross_margin", "operating_margin"]:
                    if key in data:
                        filtered_data[key] = data[key]
        data = filtered_data if len(filtered_data) > 1 else data

    result = {
        "data": data,
        "company": company,
        "period": period,
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
    }

    if not is_known:
        result["_note"] = "Data generated for unknown company - verify with primary sources"

    return result


@probe
def search_earnings_transcripts(
    company: str,
    quarter: str = "latest",
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Search and retrieve earnings call transcripts with keyword search.

    Accesses earnings call transcript database to retrieve management
    commentary, Q&A sessions, and guidance discussions.

    Args:
        company: Company name or ticker symbol
        quarter: Quarter to retrieve (Q1, Q2, Q3, Q4, or 'latest'). Default: latest
        keywords: List of keywords to highlight in transcript. Optional.

    Returns:
        Dictionary containing:
        - transcript: Full or excerpted transcript text
        - company: The company
        - quarter: The quarter
        - date: Earnings call date
        - participants: List of executives and analysts
        - key_quotes: Relevant quotes if keywords provided
    """
    call_date = datetime.now() - timedelta(days=random.randint(7, 45))

    # Generate mock transcript excerpts
    topics = [
        "revenue growth", "margin expansion", "market share", "new products",
        "competitive dynamics", "guidance", "capital allocation", "M&A"
    ]

    key_quotes = []
    if keywords:
        for kw in keywords[:3]:
            key_quotes.append({
                "keyword": kw,
                "quote": f"Regarding {kw}, we've seen positive momentum in Q4 with strong execution across all segments.",
                "speaker": random.choice(["CEO", "CFO", "COO"]),
            })

    return {
        "transcript": f"[Earnings Call Transcript for {company}]\n\nOperator: Good afternoon and welcome to {company}'s earnings call...\n\n[Management prepared remarks discussing {', '.join(random.sample(topics, 3))}]\n\n[Q&A session with analysts covering {', '.join(random.sample(topics, 2))}]",
        "company": company,
        "quarter": quarter if quarter != "latest" else "Q4 2024",
        "date": call_date.strftime("%Y-%m-%d"),
        "participants": {
            "executives": ["CEO John Smith", "CFO Jane Doe", "COO Mike Johnson"],
            "analysts": ["Goldman Sachs", "Morgan Stanley", "JP Morgan", "Bank of America"],
        },
        "key_quotes": key_quotes,
    }


# =============================================================================
# Sentiment & News Probes
# =============================================================================


@probe
def search_news(
    query: str,
    date_range: str = "7d",
    sources: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search recent news articles about a company or topic.

    Searches news aggregators for recent coverage, returning headlines,
    summaries, sentiment indicators, and source URLs.

    Args:
        query: Search query (company name, topic, or keywords)
        date_range: Time range (1d, 7d, 30d, 90d). Default: 7d
        sources: Limit to specific sources (reuters, bloomberg, wsj, ft). Optional.

    Returns:
        List of article dictionaries containing:
        - title: Article headline
        - source: Publication name
        - published: Publication date
        - summary: Article excerpt
        - url: Source URL
        - sentiment: positive/negative/neutral
    """
    all_sources = sources or ["Reuters", "Bloomberg", "Wall Street Journal", "Financial Times", "CNBC", "The Verge"]

    # Try to find company-specific news themes
    normalized = _normalize_company_name(query)
    news_themes = COMPANY_NEWS_THEMES.get(normalized)

    articles = []
    num_articles = {"1d": 3, "7d": 8, "30d": 12, "90d": 15}.get(date_range, 8)

    if news_themes:
        # Use realistic headlines for known companies
        sentiments = ["positive", "negative", "neutral"]
        # Mix of sentiments - slightly more neutral
        sentiment_distribution = [0.35, 0.30, 0.35]

        for i in range(num_articles):
            sentiment = random.choices(sentiments, sentiment_distribution)[0]
            headlines = news_themes.get(sentiment, news_themes["neutral"])
            headline = random.choice(headlines)

            # Vary the date based on article index
            days_ago = int(i * ({"1d": 0.3, "7d": 0.8, "30d": 3, "90d": 8}.get(date_range, 1)))
            pub_date = datetime.now() - timedelta(days=days_ago + random.randint(0, 2))

            articles.append({
                "title": headline,
                "source": random.choice(all_sources),
                "published": pub_date.strftime("%Y-%m-%d"),
                "summary": f"Coverage of {query}'s recent developments and market dynamics.",
                "url": f"https://news.example.com/{normalized}/{pub_date.strftime('%Y%m%d')}-{i}",
                "sentiment": sentiment,
            })
    else:
        # Generic headlines for unknown companies
        sentiments = ["positive", "negative", "neutral"]

        for i in range(num_articles):
            pub_date = datetime.now() - timedelta(days=random.randint(0, 30))
            sentiment = random.choice(sentiments)

            generic_headlines = {
                "positive": [f"{query} Reports Quarterly Results", f"Analysts Review {query} Outlook"],
                "negative": [f"{query} Faces Market Challenges", f"Industry Headwinds Impact {query}"],
                "neutral": [f"{query} Market Update", f"Sector Analysis: {query} Position"],
            }

            articles.append({
                "title": random.choice(generic_headlines[sentiment]),
                "source": random.choice(all_sources),
                "published": pub_date.strftime("%Y-%m-%d"),
                "summary": f"Coverage of {query}'s market position.",
                "url": f"https://news.example.com/{query.lower().replace(' ', '-')}-{i}",
                "sentiment": sentiment,
                "_note": "Generic coverage - verify with primary sources",
            })

    return articles


# Realistic social sentiment profiles for known companies
COMPANY_SENTIMENT_PROFILES = {
    "airbnb": {
        "base_sentiment": 0.15,  # Slightly positive
        "volatility": 0.1,
        "topics": ["travel recovery", "host experience", "regulations", "competition", "pricing"],
        "reddit_bias": -0.1,  # Reddit slightly more skeptical
    },
    "tesla": {
        "base_sentiment": 0.25,  # More polarized positive
        "volatility": 0.3,  # Very volatile sentiment
        "topics": ["FSD", "Cybertruck", "Elon Musk", "EV competition", "robotaxi"],
        "reddit_bias": 0.2,  # Reddit loves Tesla
    },
    "apple": {
        "base_sentiment": 0.20,  # Steadily positive
        "volatility": 0.05,  # Low volatility
        "topics": ["iPhone", "Apple Intelligence", "Services", "Vision Pro", "China sales"],
        "reddit_bias": 0.0,
    },
    "meta": {
        "base_sentiment": 0.10,  # Mixed sentiment
        "volatility": 0.15,
        "topics": ["AI", "Reels", "metaverse", "privacy", "ad revenue"],
        "reddit_bias": -0.15,  # Reddit skeptical of Meta
    },
}


@probe
def get_social_sentiment(
    company: str,
    platforms: Optional[List[str]] = None,
    date_range: str = "7d",
) -> Dict[str, Any]:
    """Analyze social media sentiment from Twitter/X, Reddit, StockTwits.

    Aggregates social media discussions and sentiment indicators from
    retail investor platforms and social networks.

    Args:
        company: Company name or ticker symbol
        platforms: Platforms to analyze (twitter, reddit, stocktwits). Default: all
        date_range: Time range (1d, 7d, 30d). Default: 7d

    Returns:
        Dictionary containing:
        - overall_sentiment: Aggregate sentiment score (-1 to 1)
        - sentiment_label: bullish/bearish/neutral
        - mention_count: Total mentions across platforms
        - platform_breakdown: Sentiment by platform
        - trending_topics: Key discussion themes
        - notable_posts: High-engagement posts
    """
    platforms = platforms or ["twitter", "reddit", "stocktwits"]
    normalized = _normalize_company_name(company)
    profile = COMPANY_SENTIMENT_PROFILES.get(normalized)

    if profile:
        base_sentiment = profile["base_sentiment"]
        volatility = profile["volatility"]
        topics = profile["topics"]
        reddit_bias = profile.get("reddit_bias", 0)

        # Add some randomness within the company's typical range
        sentiment_score = base_sentiment + random.uniform(-volatility, volatility)
    else:
        sentiment_score = random.uniform(-0.3, 0.4)
        topics = ["earnings", "competition", "valuation", "growth", "management"]
        reddit_bias = 0

    platform_data = {}
    for platform in platforms:
        # Each platform has slightly different sentiment
        platform_adjustment = reddit_bias if platform == "reddit" else random.uniform(-0.1, 0.1)
        platform_sentiment = sentiment_score + platform_adjustment

        # Scale mention counts by company size/popularity
        base_mentions = {"tesla": 15000, "apple": 12000, "meta": 8000, "airbnb": 4000}.get(normalized, 2000)
        mention_multiplier = {"1d": 0.15, "7d": 1, "30d": 4}.get(date_range, 1)

        platform_data[platform] = {
            "sentiment_score": round(max(-1, min(1, platform_sentiment)), 2),
            "mention_count": int(base_mentions * mention_multiplier * random.uniform(0.8, 1.2)),
            "engagement": int(base_mentions * 20 * mention_multiplier * random.uniform(0.7, 1.3)),
        }

    sentiment_label = "neutral"
    if sentiment_score > 0.15:
        sentiment_label = "bullish"
    elif sentiment_score < -0.15:
        sentiment_label = "bearish"

    return {
        "company": company,
        "overall_sentiment": round(sentiment_score, 2),
        "sentiment_label": sentiment_label,
        "mention_count": sum(p["mention_count"] for p in platform_data.values()),
        "platform_breakdown": platform_data,
        "trending_topics": topics[:4] if profile else random.sample(topics, 4),
        "notable_posts": [
            {"platform": "reddit", "summary": f"DD post analyzing {company}'s competitive moat", "engagement": random.randint(1000, 5000)},
            {"platform": "twitter", "summary": f"Analyst thread on {company}'s outlook", "engagement": random.randint(500, 3000)},
        ],
        "date_range": date_range,
    }


@probe
def get_analyst_ratings(
    company: str,
) -> Dict[str, Any]:
    """Retrieve sell-side analyst ratings, price targets, and consensus estimates.

    Aggregates analyst recommendations, price targets, and earnings
    estimates from major investment banks and research firms.

    Args:
        company: Company name or ticker symbol

    Returns:
        Dictionary containing:
        - consensus_rating: buy/hold/sell
        - average_price_target: Consensus price target
        - price_target_range: Low to high targets
        - analyst_count: Number of analysts covering
        - ratings_breakdown: Count by rating category
        - recent_changes: Recent rating changes
        - eps_estimates: Consensus EPS estimates
    """
    normalized = _normalize_company_name(company)
    analyst_data = COMPANY_ANALYST_DATA.get(normalized)
    financials = COMPANY_FINANCIALS.get(normalized)

    if analyst_data and financials:
        current_price = financials["stock"]["price"]
        eps_current = analyst_data["eps_current_year"]
        eps_next = analyst_data["eps_next_year"]
        growth_rate = ((eps_next - eps_current) / eps_current * 100) if eps_current else 15.0

        return {
            "company": company,
            "consensus_rating": analyst_data["consensus_rating"],
            "current_price": current_price,
            "average_price_target": analyst_data["price_target_avg"],
            "price_target_range": {
                "low": analyst_data["price_target_low"],
                "high": analyst_data["price_target_high"],
            },
            "analyst_count": analyst_data["analyst_count"],
            "ratings_breakdown": analyst_data["ratings"],
            "recent_changes": [
                {"firm": "Goldman Sachs", "action": "upgraded", "from": "hold", "to": "buy", "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")},
                {"firm": "Morgan Stanley", "action": "maintained", "rating": analyst_data["consensus_rating"], "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d")},
                {"firm": "JP Morgan", "action": "initiated", "rating": "overweight", "date": (datetime.now() - timedelta(days=21)).strftime("%Y-%m-%d")},
            ],
            "eps_estimates": {
                "current_year": eps_current,
                "next_year": eps_next,
                "growth_rate": f"{growth_rate:.1f}%",
            },
        }

    # Fallback for unknown companies
    current_price = random.uniform(30, 200)
    avg_target = current_price * random.uniform(1.05, 1.25)

    ratings = {
        "strong_buy": random.randint(1, 5),
        "buy": random.randint(3, 10),
        "hold": random.randint(2, 8),
        "sell": random.randint(0, 3),
        "strong_sell": random.randint(0, 1),
    }

    return {
        "company": company,
        "consensus_rating": "hold",
        "current_price": round(current_price, 2),
        "average_price_target": round(avg_target, 2),
        "price_target_range": {
            "low": round(current_price * 0.85, 2),
            "high": round(current_price * 1.35, 2),
        },
        "analyst_count": sum(ratings.values()),
        "ratings_breakdown": ratings,
        "recent_changes": [],
        "eps_estimates": {
            "current_year": round(random.uniform(2, 10), 2),
            "next_year": round(random.uniform(2.5, 12), 2),
            "growth_rate": f"{random.uniform(5, 20):.1f}%",
        },
        "_note": "Data generated for unknown company - verify with primary sources",
    }


# =============================================================================
# Legal & Regulatory Probes
# =============================================================================


@probe
def search_legal_cases(
    company: str,
    case_type: str = "all",
    status: str = "all",
) -> List[Dict[str, Any]]:
    """Search for active litigation, settlements, class actions, and regulatory actions.

    Queries legal databases for lawsuits, regulatory enforcement actions,
    settlements, and compliance matters involving the company.

    Args:
        company: Company name to search
        case_type: Type filter (lawsuit, class_action, regulatory, settlement, all). Default: all
        status: Status filter (active, settled, dismissed, all). Default: all

    Returns:
        List of case dictionaries containing:
        - case_id: Unique case identifier
        - case_type: Type of legal matter
        - title: Case title/description
        - status: Current status
        - filed_date: Date filed
        - court: Court/agency
        - amount: Claimed/settled amount if known
        - summary: Brief description
    """
    normalized = _normalize_company_name(company)
    known_cases = COMPANY_LEGAL_DATA.get(normalized, [])

    if known_cases:
        # Filter known cases by type and status
        cases = []
        for i, case in enumerate(known_cases):
            if case_type != "all" and case["case_type"] != case_type:
                continue
            if status != "all" and case["status"] != status:
                continue
            cases.append({
                "case_id": f"CASE-{normalized.upper()[:3]}-{i+1:04d}",
                **case,
            })
        return cases if cases else known_cases[:2]  # Return at least some data

    # Fallback for unknown companies
    case_types_list = ["lawsuit", "class_action", "regulatory", "settlement"]
    if case_type != "all":
        case_types_list = [case_type]

    statuses = ["active", "settled", "dismissed", "pending"]
    if status != "all":
        statuses = [status]

    cases = []
    num_cases = random.randint(1, 3)

    for i in range(num_cases):
        ct = random.choice(case_types_list)
        st = random.choice(statuses)
        filed_date = datetime.now() - timedelta(days=random.randint(90, 730))

        case_titles = {
            "lawsuit": f"Doe v. {company} - Employment Matter",
            "class_action": f"In re {company} Securities Litigation",
            "regulatory": f"Regulatory Investigation - {company}",
            "settlement": f"{company} Settlement Agreement",
        }

        cases.append({
            "case_id": f"CASE-{random.randint(10000, 99999)}",
            "case_type": ct,
            "title": case_titles.get(ct, f"Legal Matter - {company}"),
            "status": st,
            "filed_date": filed_date.strftime("%Y-%m-%d"),
            "court": random.choice(["US District Court", "State Court", "SEC", "FTC"]),
            "amount": f"${random.randint(5, 100)}M" if st in ["settled", "active"] else None,
            "summary": f"Legal proceeding involving {company}.",
            "_note": "Generated data - verify with primary sources",
        })

    return cases


@probe
def search_regulatory_filings(
    company: str,
    regulatory_body: str = "all",
    date_range: str = "1y",
) -> List[Dict[str, Any]]:
    """Search filings from regulatory bodies (FDA, FCC, FERC, etc.).

    Queries regulatory databases for filings, approvals, denials,
    and pending matters with sector-specific regulators.

    Args:
        company: Company name to search
        regulatory_body: Regulator filter (SEC, FDA, FCC, FERC, EPA, FTC, all). Default: all
        date_range: Time range (6m, 1y, 3y). Default: 1y

    Returns:
        List of filing dictionaries containing:
        - filing_id: Unique identifier
        - regulatory_body: Issuing regulator
        - filing_type: Type of regulatory action
        - date: Filing/action date
        - status: approved/pending/denied/under_review
        - summary: Description of the filing
        - impact: Assessed business impact
    """
    regulators = ["SEC", "FDA", "FCC", "FERC", "EPA", "FTC", "DOJ"]
    if regulatory_body != "all":
        regulators = [regulatory_body]

    filings = []
    num_filings = random.randint(3, 8)

    filing_types = {
        "SEC": ["10-K Filing", "8-K Disclosure", "Proxy Statement", "Registration Statement"],
        "FDA": ["Drug Approval Application", "510(k) Clearance", "Clinical Trial Authorization", "Warning Letter"],
        "FCC": ["Spectrum License", "Equipment Authorization", "Merger Review"],
        "FERC": ["Rate Filing", "Pipeline Certificate", "Market Authorization"],
        "EPA": ["Environmental Permit", "Compliance Report", "Emissions Data"],
        "FTC": ["Merger Notification", "Consumer Protection Filing", "Antitrust Review"],
        "DOJ": ["Antitrust Filing", "FCPA Disclosure", "Settlement Agreement"],
    }

    for i in range(num_filings):
        reg = random.choice(regulators)
        filing_date = datetime.now() - timedelta(days=random.randint(1, 365))
        status = random.choice(["approved", "pending", "under_review", "denied"])

        filings.append({
            "filing_id": f"REG-{reg}-{random.randint(10000, 99999)}",
            "regulatory_body": reg,
            "filing_type": random.choice(filing_types.get(reg, ["General Filing"])),
            "date": filing_date.strftime("%Y-%m-%d"),
            "status": status,
            "summary": f"Regulatory filing with {reg} regarding {company}'s operations and compliance.",
            "impact": random.choice(["material", "moderate", "minimal"]),
        })

    return filings


# =============================================================================
# Market Research Probe
# =============================================================================


# Realistic industry/market research data
INDUSTRY_DATA = {
    "short-term rental": {
        "market_size": 125_000_000_000,  # $125B global vacation rental market
        "cagr": 11.2,
        "market_share": {
            "Airbnb": "22%",
            "Booking Holdings (Booking.com)": "28%",
            "Expedia (Vrbo)": "15%",
            "Trip.com": "8%",
            "Regional players": "27%",
        },
        "trends": [
            "Regulatory tightening in major cities (NYC, Barcelona, Amsterdam)",
            "Shift toward longer stays and remote work accommodations",
            "Professionalization of hosting (property management companies)",
            "Experience-based travel growth",
            "Sustainability and eco-tourism demand",
        ],
        "segments": {
            "Urban apartments": "35%",
            "Vacation homes": "30%",
            "Unique stays (treehouses, boats)": "10%",
            "Rural/nature properties": "15%",
            "Luxury rentals": "10%",
        },
    },
    "electric vehicles": {
        "market_size": 500_000_000_000,  # $500B global EV market
        "cagr": 17.8,
        "market_share": {
            "Tesla": "18%",
            "BYD": "16%",
            "Volkswagen Group": "8%",
            "GM/Ford": "7%",
            "Hyundai/Kia": "9%",
            "Chinese EVs (NIO, XPeng, Li Auto)": "12%",
            "Others": "30%",
        },
        "trends": [
            "Battery cost decline enabling price parity with ICE",
            "Charging infrastructure expansion",
            "Government incentives and ICE bans",
            "Solid-state battery development",
            "Autonomous driving integration",
        ],
        "segments": {
            "Passenger cars": "75%",
            "Commercial vehicles": "15%",
            "Two/three wheelers": "8%",
            "Buses": "2%",
        },
    },
    "consumer electronics": {
        "market_size": 1_100_000_000_000,  # $1.1T global consumer electronics
        "cagr": 5.5,
        "market_share": {
            "Apple": "17%",
            "Samsung": "15%",
            "Xiaomi": "7%",
            "Huawei": "5%",
            "Dell/HP/Lenovo": "12%",
            "Others": "44%",
        },
        "trends": [
            "AI integration in devices",
            "Foldable and flexible displays",
            "Wearables growth (smartwatches, AR glasses)",
            "Sustainability and right-to-repair",
            "5G device proliferation",
        ],
        "segments": {
            "Smartphones": "40%",
            "PCs/Laptops": "20%",
            "TVs/Displays": "15%",
            "Wearables": "10%",
            "Audio": "8%",
            "Other": "7%",
        },
    },
    "digital advertising": {
        "market_size": 680_000_000_000,  # $680B global digital ad market
        "cagr": 10.5,
        "market_share": {
            "Google": "28%",
            "Meta (Facebook/Instagram)": "21%",
            "Amazon": "12%",
            "TikTok/ByteDance": "8%",
            "Microsoft": "4%",
            "Others": "27%",
        },
        "trends": [
            "Privacy changes impacting targeting (iOS ATT, cookie deprecation)",
            "AI-powered ad creation and optimization",
            "Retail media network growth",
            "Connected TV advertising surge",
            "Short-form video dominance",
        ],
        "segments": {
            "Search": "35%",
            "Social media": "30%",
            "Display/programmatic": "18%",
            "Video": "12%",
            "Other": "5%",
        },
    },
}


def _match_industry(query: str) -> tuple:
    """Match query to known industry data."""
    query_lower = query.lower()

    # Direct matches
    if "rental" in query_lower or "airbnb" in query_lower or "vacation" in query_lower:
        return "short-term rental", INDUSTRY_DATA["short-term rental"]
    if "ev" in query_lower or "electric vehicle" in query_lower or "tesla" in query_lower:
        return "electric vehicles", INDUSTRY_DATA["electric vehicles"]
    if "smartphone" in query_lower or "consumer electronics" in query_lower or "apple" in query_lower:
        return "consumer electronics", INDUSTRY_DATA["consumer electronics"]
    if "advertising" in query_lower or "ad" in query_lower or "meta" in query_lower or "facebook" in query_lower:
        return "digital advertising", INDUSTRY_DATA["digital advertising"]

    return None, None


@probe
def get_market_research(
    industry: str,
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Access market size, growth rates, market share data, and industry reports.

    Retrieves industry-level data including total addressable market,
    growth projections, competitive landscape, and market share estimates.

    Args:
        industry: Industry or sector name (e.g., 'cloud computing', 'electric vehicles')
        metrics: Specific metrics to retrieve. If None, returns all.
                 Options: market_size, growth_rate, market_share, trends, segments

    Returns:
        Dictionary containing:
        - industry: The industry queried
        - market_size: Total market size with currency
        - growth_rate: CAGR projections
        - market_share: Top players and their shares
        - key_trends: Major industry trends
        - segments: Market breakdown by segment
        - outlook: Industry outlook summary
    """
    matched_name, industry_data = _match_industry(industry)

    if industry_data:
        market_size = industry_data["market_size"]
        cagr = industry_data["cagr"]
        projected = market_size * (1 + cagr / 100) ** 5

        return {
            "industry": matched_name,
            "query": industry,
            "market_size": {
                "value": market_size,
                "formatted": f"${market_size / 1_000_000_000:.1f}B",
                "year": 2024,
            },
            "growth_rate": {
                "cagr_5yr": f"{cagr}%",
                "projected_2029": f"${projected / 1_000_000_000:.1f}B",
            },
            "market_share": industry_data["market_share"],
            "key_trends": industry_data["trends"],
            "segments": industry_data["segments"],
            "outlook": f"The {matched_name} market shows strong fundamentals with {cagr}% CAGR through 2029, driven by key trends including {industry_data['trends'][0].lower()} and {industry_data['trends'][1].lower()}.",
        }

    # Fallback for unknown industries
    base_market_size = random.randint(50, 300) * 1_000_000_000
    growth_rate = random.uniform(0.05, 0.15)

    return {
        "industry": industry,
        "market_size": {
            "value": base_market_size,
            "formatted": f"${base_market_size / 1_000_000_000:.1f}B",
            "year": 2024,
        },
        "growth_rate": {
            "cagr_5yr": f"{growth_rate * 100:.1f}%",
            "projected_2029": f"${base_market_size * (1 + growth_rate) ** 5 / 1_000_000_000:.1f}B",
        },
        "market_share": {
            "Leader": f"{random.randint(15, 30)}%",
            "Challenger 1": f"{random.randint(10, 20)}%",
            "Challenger 2": f"{random.randint(8, 15)}%",
            "Others": f"{random.randint(35, 55)}%",
        },
        "key_trends": [
            "Digital transformation",
            "Sustainability focus",
            "AI/automation adoption",
            "Regulatory evolution",
        ],
        "segments": {
            "Primary segment": f"{random.randint(40, 55)}%",
            "Secondary segment": f"{random.randint(25, 35)}%",
            "Emerging segment": f"{random.randint(10, 20)}%",
        },
        "outlook": "Market shows moderate growth potential with evolving competitive dynamics.",
        "_note": "Estimated data - verify with industry reports",
    }
