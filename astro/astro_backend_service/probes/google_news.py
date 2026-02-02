"""Google News RSS feed probes for fetching and searching news articles.

Provides probes for accessing Google News via RSS feeds:
- Top headlines by country/language
- Headlines by topic (BUSINESS, TECHNOLOGY, etc.)
- Headlines by location (city, state, country)
- Advanced search with keywords, time ranges, and filters
"""

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from astro_backend_service.probes.decorator import probe


# Google News RSS base URL
BASE_URL = "https://news.google.com/rss"

# Supported topics
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

# Default timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 30.0


def _build_locale_params(language: str = "en", country: str = "US") -> str:
    """Build the locale query parameters for Google News RSS."""
    return f"hl={language}-{country}&gl={country}&ceid={country}:{language}"


def _parse_rss_items(xml_content: str) -> List[Dict[str, Any]]:
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
    """Fetch news headlines for a specific geographic location.

    Retrieves location-oriented news headlines. Accepts city names,
    state/region names, or country names.

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
    when: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    site: Optional[str] = None,
    intitle: Optional[str] = None,
    max_results: int = 100,
) -> Dict[str, Any]:
    """Search Google News with advanced query options.

    Performs a search query on Google News with support for time filtering,
    site restrictions, and title matching.

    Args:
        query: Search keywords (supports OR, quotes for exact match, -term to exclude)
        language: Language code (e.g., 'en', 'es'). Default: 'en'
        country: Country code (e.g., 'US', 'GB'). Default: 'US'
        when: Relative time filter (e.g., '1h', '12h', '7d', '1m'). Optional.
        after: Start date in YYYY-MM-DD format. Optional.
        before: End date in YYYY-MM-DD format. Optional.
        site: Restrict to specific domain (e.g., 'reuters.com'). Optional.
        intitle: Require word in article title. Optional.
        max_results: Maximum number of articles to return (max 100). Default: 100

    Returns:
        Dictionary containing:
        - articles: List of article objects with title, link, published, source
        - count: Number of articles returned
        - query: The search query used
        - feed_url: The RSS feed URL used

    Examples:
        Search for Tesla news from last hour:
            search_google_news("Tesla", when="1h")

        Search Reuters for Boeing news:
            search_google_news("Boeing", site="reuters.com")

        Search for SpaceX or Blue Origin:
            search_google_news("SpaceX OR Blue Origin")

        Search with date range:
            search_google_news("earnings", after="2024-01-01", before="2024-01-31")
    """
    # Build the query string with advanced operators
    query_parts = [query]

    if when:
        query_parts.append(f"when:{when}")
    if after:
        query_parts.append(f"after:{after}")
    if before:
        query_parts.append(f"before:{before}")
    if site:
        query_parts.append(f"site:{site}")
    if intitle:
        query_parts.append(f"intitle:{intitle}")

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
    ticker: Optional[str] = None,
    language: str = "en",
    country: str = "US",
    when: Optional[str] = None,
    max_results: int = 100,
) -> Dict[str, Any]:
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
