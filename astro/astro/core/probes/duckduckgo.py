"""DuckDuckGo search probes for web and news search.

Provides probes for searching the web via DuckDuckGo:
- General web search with region and time filters
- Company-focused research search
- News-specific search

No API key required. Uses the duckduckgo-search package.
"""

import time
from typing import Any

from astro.core.probes.decorator import probe

# Rate limiting
_last_call_time = 0.0


def _rate_limit() -> None:
    """Enforce 1 second delay between DuckDuckGo API calls."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_call_time = time.time()


@probe
def search_web(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
    time_filter: str = "",
) -> dict[str, Any]:
    """Perform a web search using DuckDuckGo and return titles, URLs, and snippets.

    Searches across the entire web (not just news) for matching pages. Useful for finding
    Wikipedia pages, company profiles, press releases, SEC filings, investor relations pages,
    and other authoritative sources. Supports region filtering and time-based filtering.

    Args:
        query: The search query string. Supports standard search operators.
        max_results: Number of results to return (1-20, default 10).
        region: Region code for results (default "wt-wt" for worldwide).
                Common values: "us-en" (US), "uk-en" (UK), "de-de" (Germany).
        time_filter: Optional time filter. Values: "d" (past day), "w" (past week),
                     "m" (past month), "y" (past year), "" (any time, default).

    Returns:
        Dictionary with search results containing title, link/URL, and snippet for each result.
    """
    _rate_limit()
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    max_results=min(max_results, 20),
                    region=region,
                    timelimit=time_filter or None,
                )
            )

        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "link": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
            })

        return {"results": formatted, "count": len(formatted), "query": query}
    except Exception as e:
        return {"results": [], "count": 0, "query": query, "error": str(e)}


@probe
def search_web_by_company(
    company_name: str, topic: str = "", max_results: int = 10
) -> dict[str, Any]:
    """Search the web for company-specific information using DuckDuckGo.

    Optimized for company research by combining the company name with an optional topic
    for targeted results. Useful topics include: "acquisitions", "mergers history",
    "divestitures", "corporate timeline", "SEC filings", "investor relations",
    "annual report", "subsidiaries".

    Args:
        company_name: The name of the company to research.
        topic: Optional topic to focus the search (e.g. "acquisitions", "SEC filings").
               If empty, searches for the company name alone.
        max_results: Number of results to return (1-20, default 10).

    Returns:
        Dictionary with search results containing title, link/URL, and snippet for each result.
    """
    if topic:
        query = f"{company_name} {topic}"
    else:
        query = company_name

    return search_web(query, max_results=max_results)


@probe
def search_news_ddg(
    query: str, max_results: int = 15, time_filter: str = ""
) -> dict[str, Any]:
    """Search news sources via DuckDuckGo for recent articles and press coverage.

    Searches specifically across news sources (not general web), complementing Google News
    with potentially different source coverage. Returns news articles with titles, links,
    snippets, source names, and publication dates.

    Args:
        query: The news search query string.
        max_results: Number of results to return (1-25, default 15).
        time_filter: Optional time filter. Values: "d" (past day), "w" (past week),
                     "m" (past month), "" (any time, default).

    Returns:
        Dictionary with news results containing title, link, snippet, source, and date.
    """
    _rate_limit()
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.news(
                    query,
                    max_results=min(max_results, 25),
                    timelimit=time_filter or None,
                )
            )

        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "link": r.get("url", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
                "source": r.get("source", ""),
                "date": r.get("date", ""),
            })

        return {"results": formatted, "count": len(formatted), "query": query}
    except Exception as e:
        return {"results": [], "count": 0, "query": query, "error": str(e)}
