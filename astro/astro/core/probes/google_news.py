"""Google News RSS feed probes for fetching and searching news articles.

Provides probes for accessing Google News via RSS feeds:
- Top headlines by country/language
- Headlines by topic (BUSINESS, TECHNOLOGY, etc.)
- Headlines by location (city, state, country)
- Advanced search with keywords, time ranges, and filters

Based on community-discovered Google News RSS API patterns.
See: https://www.newscatcherapi.com/blog-posts/google-news-rss-search-parameters-the-missing-documentaiton

IMPORTANT LIMITATIONS:
- All feeds return a maximum of 100 articles per request
- No official Google documentation exists for these endpoints
- Rate limiting may apply for excessive requests
- Article links are Google redirect URLs, not direct source URLs
"""

import asyncio
from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from astro.core.probes.decorator import probe

# Google News RSS base URL
BASE_URL = "https://news.google.com/rss"

# Supported standard topics (8 core topics)
VALID_TOPICS = [
    "WORLD",
    "NATION",
    "BUSINESS",
    "TECHNOLOGY",
    "ENTERTAINMENT",
    "SCIENCE",
    "SPORTS",
    "HEALTH",
]

# Maximum articles per request (Google News limit)
MAX_ARTICLES_LIMIT = 100

# Default timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 30.0


def _build_locale_params(language: str = "en", country: str = "US") -> str:
    """Build the locale query parameters for Google News RSS.

    Args:
        language: Language code (e.g., 'en', 'fr', 'de', 'zh')
        country: Country code (e.g., 'US', 'GB', 'FR', 'DE', 'JP')

    Returns:
        Query string with hl (language), gl (country), and ceid (country:language) parameters

    Examples:
        _build_locale_params("en", "US") → "hl=en-US&gl=US&ceid=US:en"
        _build_locale_params("fr", "FR") → "hl=fr&gl=FR&ceid=FR:fr"
        _build_locale_params("zh", "CN") → "hl=zh-CN&gl=CN&ceid=CN:zh"

    Note:
        For most single-language countries (e.g., France, Germany), the format is simplified.
        For multi-language countries (e.g., US, GB), hl uses language-country format.
    """
    # For multi-language countries, use language-country format for hl
    # For single-language countries, use just the language code
    if country in ["US", "GB", "CA", "AU"]:
        hl = f"{language}-{country}"
    else:
        hl = language

    return f"hl={hl}&gl={country}&ceid={country}:{language}"


def _parse_rss_items(xml_content: str) -> list[dict[str, Any]]:
    """Parse RSS XML content and extract article items.

    Args:
        xml_content: Raw XML string from Google News RSS feed

    Returns:
        List of article dictionaries with title, link, published, source
    """
    soup = BeautifulSoup(xml_content, "xml")
    items = soup.find_all("item")

    articles = []
    for item in items:
        article = {
            "title": item.title.text if item.title else None,
            "link": item.link.text if item.link else None,
            "published": item.pubDate.text if item.pubDate else None,
            "description": item.description.text if item.description else None,
            "source": None,
        }

        # Extract source from <source> tag
        source_tag = item.find("source")
        if source_tag:
            article["source"] = source_tag.text
            article["source_url"] = source_tag.get("url")

        articles.append(article)

    return articles


def _fetch_rss_sync(url: str) -> str:
    """Fetch RSS feed content from URL synchronously.

    Args:
        url: Full URL to Google News RSS feed

    Returns:
        Raw XML content as string

    Raises:
        httpx.HTTPError: If request fails
    """
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


async def _fetch_rss_async(url: str) -> str:
    """Fetch RSS feed content from URL asynchronously.

    Args:
        url: Full URL to Google News RSS feed

    Returns:
        Raw XML content as string

    Raises:
        httpx.HTTPError: If request fails
    """
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT, follow_redirects=True
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _fetch_rss(url: str) -> str:
    """Fetch RSS feed, handling both sync and async contexts.

    Args:
        url: Full URL to Google News RSS feed

    Returns:
        Raw XML content as string
    """
    try:
        # Check if we're in an async context
        asyncio.get_running_loop()
        # If we get here, we're in an async context - use sync client to avoid nesting
        return _fetch_rss_sync(url)
    except RuntimeError:
        # No running loop, safe to use sync client
        return _fetch_rss_sync(url)


@probe
def fetch_google_news_headlines(
    language: str = "en",
    country: str = "US",
    max_results: int = 100,
) -> dict[str, Any]:
    """Fetch top news headlines from Google News RSS feed.

    Retrieves the latest trending news headlines for a specified country
    and language combination.

    Args:
        language: Language code (e.g., 'en', 'es', 'fr'). Default: 'en'
        country: Country code (e.g., 'US', 'GB', 'DE'). Default: 'US'
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - feed_url: The RSS feed URL used
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}?{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "feed_url": url,
            "error": str(e),
        }


@probe
def fetch_google_news_by_topic(
    topic: str,
    language: str = "en",
    country: str = "US",
    max_results: int = 100,
) -> dict[str, Any]:
    """Fetch news headlines for a specific topic from Google News.

    Retrieves topic-oriented news headlines. Valid topics are:
    WORLD, NATION, BUSINESS, TECHNOLOGY, ENTERTAINMENT, SCIENCE, SPORTS, HEALTH.

    Args:
        topic: Topic category (e.g., 'BUSINESS', 'TECHNOLOGY')
        language: Language code (e.g., 'en', 'es'). Default: 'en'
        country: Country code (e.g., 'US', 'GB'). Default: 'US'
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - topic: The topic requested
        - feed_url: The RSS feed URL used
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    # Validate and normalize topic
    topic_upper = topic.upper()
    if topic_upper not in VALID_TOPICS:
        return {
            "articles": [],
            "count": 0,
            "topic": topic,
            "error": f"Invalid topic. Must be one of: {', '.join(VALID_TOPICS)}",
        }

    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}/headlines/section/topic/{topic_upper}?{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "topic": topic_upper,
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "topic": topic_upper,
            "feed_url": url,
            "error": str(e),
        }


@probe
def fetch_google_news_by_location(
    location: str,
    language: str = "en",
    country: str = "US",
    max_results: int = 100,
) -> dict[str, Any]:
    """Fetch news headlines for a specific geographic location.

    Retrieves location-oriented news headlines. Accepts city names,
    state/region names, or country names. Flexible - abbreviations and
    full names both work (e.g., 'NY', 'New York', 'NewYork').

    Args:
        location: Geographic location (e.g., 'New York', 'California', 'London')
        language: Language code (e.g., 'en', 'es'). Default: 'en'
        country: Country code for locale (e.g., 'US', 'GB'). Default: 'US'
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - location: The location requested
        - feed_url: The RSS feed URL used
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    encoded_location = quote_plus(location)
    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}/headlines/section/geo/{encoded_location}?{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "location": location,
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "location": location,
            "feed_url": url,
            "error": str(e),
        }


@probe
def search_google_news(
    query: str,
    language: str = "en",
    country: str = "US",
    when: str | None = None,
    after: str | None = None,
    before: str | None = None,
    site: str | None = None,
    intitle: str | None = None,
    allintitle: str | None = None,
    allintext: str | None = None,
    inurl: str | None = None,
    allinurl: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search Google News with advanced query options and operators.

    Performs a search query on Google News using the full Google search engine syntax
    for news articles. Supports time filtering, site restrictions, title/text/URL matching,
    and boolean operators.

    Args:
        query: Base search keywords. Supports:
               - AND (default): "Elon Musk" searches for articles with both words
               - OR: "SpaceX OR Boeing" matches either term
               - Exact match: '"Goldman Sachs"' matches exact phrase
               - Exclude: "Apple -fruit" excludes articles mentioning "fruit"
               - Required: "+tesla" must include the term
        language: Language code (e.g., 'en', 'es', 'fr', 'de', 'zh'). Default: 'en'
        country: Country code (e.g., 'US', 'GB', 'FR', 'DE', 'JP'). Default: 'US'
        when: Relative time filter. Format: {N}h, {N}d, {N}m (hours, days, months)
              Examples: '1h', '12h', '7d', '30d', '2m'
              Tested ranges: up to ~101h, standard days, up to ~48m. Optional.
        after: Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Optional.
        before: End date in YYYY-MM-DD format (e.g., '2024-01-31'). Optional.
        site: Restrict to specific domain (e.g., 'reuters.com', 'bloomberg.com'). Optional.
        intitle: Require word in article title (e.g., 'earnings'). Optional.
        allintitle: All words must appear in title (e.g., 'Goldman Sachs earnings'). Optional.
        allintext: All words must appear in article body text. Optional.
        inurl: Word must appear in article URL (useful for filtering by source). Optional.
        allinurl: All words must appear in URL. Optional.
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - query: The full search query used (with all operators)
        - feed_url: The RSS feed URL used

    Query Operator Examples:
        Basic search:
            search_google_news("artificial intelligence")

        Time-based searches:
            search_google_news("AAPL", when="1h")  # Last hour
            search_google_news("Tesla", when="7d")  # Last 7 days
            search_google_news("earnings", after="2024-01-01", before="2024-01-31")

        Boolean operators:
            search_google_news("SpaceX OR Blue Origin")  # Either company
            search_google_news("Apple -fruit")  # Exclude fruit references
            search_google_news('"Federal Reserve"')  # Exact phrase

        Site/source filtering:
            search_google_news("AI", site="reuters.com")  # Reuters only
            search_google_news("technology", inurl="bloomberg.com")  # Bloomberg articles

        Title/text requirements:
            search_google_news("TSLA", intitle="earnings")  # "earnings" in title
            search_google_news("", allintitle="Goldman Sachs quarterly report")
            search_google_news("finance", allintext="interest rate hike")

        Combined operators:
            search_google_news(
                "Tesla",
                when="7d",
                site="reuters.com",
                intitle="earnings"
            )
            # Articles from Reuters in last 7 days with "Tesla" and "earnings" in title

        Advanced multi-source:
            search_google_news(
                '"earnings report"',
                inurl="reuters.com OR bloomberg.com",
                when="12h"
            )
            # Earnings reports from Reuters or Bloomberg in last 12 hours

    Note:
        - Maximum 100 articles per request (Google News limit)
        - Article links are Google redirect URLs, not direct source URLs
        - when: parameter ranges based on community testing (may vary)
        - Excessive requests may trigger rate limiting
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    # Build the query string with advanced operators
    query_parts = []

    # Add base query if provided
    if query:
        query_parts.append(query)

    # Add advanced operators
    if allintitle:
        query_parts.append(f"allintitle:{allintitle}")
    elif intitle:
        query_parts.append(f"intitle:{intitle}")

    if allintext:
        query_parts.append(f"allintext:{allintext}")

    if allinurl:
        query_parts.append(f"allinurl:{allinurl}")
    elif inurl:
        query_parts.append(f"inurl:{inurl}")
    elif site:
        # site: is a convenience alias for inurl:
        query_parts.append(f"inurl:{site}")

    # Add time filters
    if when:
        query_parts.append(f"when:{when}")
    if after:
        query_parts.append(f"after:{after}")
    if before:
        query_parts.append(f"before:{before}")

    full_query = " ".join(query_parts)
    encoded_query = quote_plus(full_query)

    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}/search?q={encoded_query}&{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "query": full_query,
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "query": full_query,
            "feed_url": url,
            "error": str(e),
        }


@probe
def search_google_news_by_company(
    company_name: str,
    ticker: str | None = None,
    language: str = "en",
    country: str = "US",
    when: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search Google News for company-specific news.

    Specialized search for company news, combining company name and optional
    ticker symbol for comprehensive coverage.

    Args:
        company_name: Company name (e.g., 'Apple', 'Microsoft')
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT'). Optional.
        language: Language code (e.g., 'en'). Default: 'en'
        country: Country code (e.g., 'US'). Default: 'US'
        when: Relative time filter (e.g., '1h', '7d'). Optional.
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - company: The company searched
        - query: The search query used
        - feed_url: The RSS feed URL used
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    # Build query with company name and optional ticker
    if ticker:
        query = f'"{company_name}" OR {ticker}'
    else:
        query = f'"{company_name}"'

    query_parts = [query]
    if when:
        query_parts.append(f"when:{when}")

    full_query = " ".join(query_parts)
    encoded_query = quote_plus(full_query)

    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}/search?q={encoded_query}&{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "company": company_name,
            "ticker": ticker,
            "query": full_query,
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "company": company_name,
            "ticker": ticker,
            "query": full_query,
            "feed_url": url,
            "error": str(e),
        }


@probe
def fetch_google_news_by_topic_hash(
    topic_hash: str,
    language: str = "en",
    country: str = "US",
    max_results: int = 100,
) -> dict[str, Any]:
    """Fetch news headlines using a custom Google News topic hash.

    Google internally represents topics as Base64-encoded hash strings. These can be
    discovered by visiting topic pages in the Google News UI and extracting the hash
    from the redirected URL.

    This allows access to specialized topics beyond the 8 standard categories
    (e.g., "US Elections", "Artificial Intelligence", "Climate Change").

    Args:
        topic_hash: Base64-encoded topic hash from Google News
                   Example: "CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx6TVdZU0JXVnVMVlZUR2dKVlV5Z0FQAQ"
        language: Language code (e.g., 'en', 'es'). Default: 'en'
        country: Country code (e.g., 'US', 'GB'). Default: 'US'
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - topic_hash: The topic hash used
        - feed_url: The RSS feed URL used

    How to find topic hashes:
        1. Go to https://news.google.com/
        2. Search for or navigate to a topic (e.g., "Artificial Intelligence")
        3. The URL will redirect to a format like:
           https://news.google.com/topics/CAAqKggKI...?hl=en-US&gl=US&ceid=US:en
        4. Copy the hash string between /topics/ and the ?
        5. Use it with this probe

    Examples:
        # Fetch AI news using discovered topic hash
        fetch_google_news_by_topic_hash(
            topic_hash="CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx6TVdZU0JXVnVMVlZUR2dKVlV5Z0FQAQ"
        )
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}/topics/{topic_hash}?{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "topic_hash": topic_hash,
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "topic_hash": topic_hash,
            "feed_url": url,
            "error": str(e),
        }


@probe
def search_google_news_multi_source(
    query: str,
    sources: list[str],
    language: str = "en",
    country: str = "US",
    when: str | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search Google News across multiple specific news sources.

    Convenience probe for searching across multiple trusted sources simultaneously.
    Useful for financial news aggregation, fact-checking, or multi-perspective analysis.

    Args:
        query: Search keywords
        sources: List of domain names to search (e.g., ['reuters.com', 'bloomberg.com'])
        language: Language code (e.g., 'en'). Default: 'en'
        country: Country code (e.g., 'US'). Default: 'US'
        when: Relative time filter (e.g., '1h', '7d'). Optional.
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - query: The search query used
        - sources: List of sources searched
        - feed_url: The RSS feed URL used

    Examples:
        # Search for AI news from Reuters and Bloomberg
        search_google_news_multi_source(
            query="artificial intelligence",
            sources=["reuters.com", "bloomberg.com"],
            when="7d"
        )

        # Earnings reports from financial news sources
        search_google_news_multi_source(
            query='"earnings report"',
            sources=["reuters.com", "bloomberg.com", "wsj.com", "ft.com"],
            when="1d"
        )

        # Tech news from tech-focused publications
        search_google_news_multi_source(
            query="Apple",
            sources=["techcrunch.com", "theverge.com", "arstechnica.com"],
            when="12h"
        )
    """
    # Validate max_results
    if max_results > MAX_ARTICLES_LIMIT:
        max_results = MAX_ARTICLES_LIMIT

    # Build OR query for multiple sources using inurl:
    source_query = " OR ".join([f"inurl:{source}" for source in sources])

    # Combine with main query
    query_parts = [query, f"({source_query})"]

    if when:
        query_parts.append(f"when:{when}")

    full_query = " ".join(query_parts)
    encoded_query = quote_plus(full_query)

    locale_params = _build_locale_params(language, country)
    url = f"{BASE_URL}/search?q={encoded_query}&{locale_params}"

    try:
        xml_content = _fetch_rss(url)
        articles = _parse_rss_items(xml_content)
        articles = articles[:max_results]

        return {
            "articles": articles,
            "count": len(articles),
            "query": full_query,
            "sources": sources,
            "feed_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "articles": [],
            "count": 0,
            "query": full_query,
            "sources": sources,
            "feed_url": url,
            "error": str(e),
        }
