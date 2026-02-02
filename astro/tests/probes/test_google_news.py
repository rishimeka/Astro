"""Tests for Google News RSS feed probes."""

import importlib
import pytest
from unittest.mock import patch

from astro_backend_service.probes.google_news import (
    fetch_google_news_headlines,
    fetch_google_news_by_topic,
    fetch_google_news_by_location,
    search_google_news,
    search_google_news_by_company,
    _parse_rss_items,
    _build_locale_params,
    VALID_TOPICS,
)
from astro_backend_service.probes import ProbeRegistry


@pytest.fixture
def register_google_news_probes():
    """Re-register Google News probes if registry was cleared."""
    # Clear first to avoid duplicate errors, then reload
    ProbeRegistry.clear()
    import astro_backend_service.probes.google_news

    importlib.reload(astro_backend_service.probes.google_news)
    yield


# Sample RSS XML for testing
SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>Test Article 1</title>
      <link>https://example.com/article1</link>
      <pubDate>Fri, 31 Jan 2025 12:00:00 GMT</pubDate>
      <description>Description for article 1</description>
      <source url="https://example.com">Example News</source>
    </item>
    <item>
      <title>Test Article 2</title>
      <link>https://example.com/article2</link>
      <pubDate>Fri, 31 Jan 2025 11:00:00 GMT</pubDate>
      <description>Description for article 2</description>
      <source url="https://other.com">Other News</source>
    </item>
  </channel>
</rss>
"""


class TestHelperFunctions:
    """Test helper functions."""

    def test_build_locale_params_defaults(self):
        """Test locale params with default values."""
        result = _build_locale_params()
        assert result == "hl=en-US&gl=US&ceid=US:en"

    def test_build_locale_params_custom(self):
        """Test locale params with custom values."""
        result = _build_locale_params(language="de", country="DE")
        assert result == "hl=de-DE&gl=DE&ceid=DE:de"

    def test_parse_rss_items(self):
        """Test RSS XML parsing."""
        articles = _parse_rss_items(SAMPLE_RSS_XML)

        assert len(articles) == 2

        assert articles[0]["title"] == "Test Article 1"
        assert articles[0]["link"] == "https://example.com/article1"
        assert articles[0]["source"] == "Example News"
        assert articles[0]["source_url"] == "https://example.com"
        assert "2025" in articles[0]["published"]

        assert articles[1]["title"] == "Test Article 2"
        assert articles[1]["source"] == "Other News"

    def test_parse_rss_items_empty(self):
        """Test parsing empty RSS feed."""
        empty_rss = """<?xml version="1.0"?><rss><channel></channel></rss>"""
        articles = _parse_rss_items(empty_rss)
        assert articles == []


@pytest.mark.usefixtures("register_google_news_probes")
class TestProbeRegistration:
    """Test that probes are properly registered."""

    def test_headlines_probe_registered(self):
        """Test fetch_google_news_headlines is registered."""
        probe = ProbeRegistry.get("fetch_google_news_headlines")
        assert probe is not None
        assert "headlines" in probe.description.lower()

    def test_topic_probe_registered(self):
        """Test fetch_google_news_by_topic is registered."""
        probe = ProbeRegistry.get("fetch_google_news_by_topic")
        assert probe is not None
        assert "topic" in probe.description.lower()

    def test_location_probe_registered(self):
        """Test fetch_google_news_by_location is registered."""
        probe = ProbeRegistry.get("fetch_google_news_by_location")
        assert probe is not None
        assert "location" in probe.description.lower()

    def test_search_probe_registered(self):
        """Test search_google_news is registered."""
        probe = ProbeRegistry.get("search_google_news")
        assert probe is not None
        assert "search" in probe.description.lower()

    def test_company_search_probe_registered(self):
        """Test search_google_news_by_company is registered."""
        probe = ProbeRegistry.get("search_google_news_by_company")
        assert probe is not None
        assert "company" in probe.description.lower()


class TestFetchGoogleNewsHeadlines:
    """Test fetch_google_news_headlines probe."""

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_headlines_success(self, mock_fetch):
        """Test successful headline fetch."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_headlines.invoke({})

        assert result["count"] == 2
        assert len(result["articles"]) == 2
        assert "error" not in result
        assert "feed_url" in result

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_headlines_with_locale(self, mock_fetch):
        """Test headline fetch with custom locale."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_headlines.invoke(
            {
                "language": "de",
                "country": "DE",
            }
        )

        assert "hl=de-DE" in result["feed_url"]
        assert "gl=DE" in result["feed_url"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_headlines_max_results(self, mock_fetch):
        """Test headline fetch with max_results limit."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_headlines.invoke({"max_results": 1})

        assert result["count"] == 1
        assert len(result["articles"]) == 1


class TestFetchGoogleNewsByTopic:
    """Test fetch_google_news_by_topic probe."""

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_topic_success(self, mock_fetch):
        """Test successful topic fetch."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_by_topic.invoke({"topic": "TECHNOLOGY"})

        assert result["count"] == 2
        assert result["topic"] == "TECHNOLOGY"
        assert "/topic/TECHNOLOGY" in result["feed_url"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_topic_case_insensitive(self, mock_fetch):
        """Test topic is case-insensitive."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_by_topic.invoke({"topic": "business"})

        assert result["topic"] == "BUSINESS"
        assert "/topic/BUSINESS" in result["feed_url"]

    def test_fetch_topic_invalid(self):
        """Test invalid topic returns error."""
        result = fetch_google_news_by_topic.invoke({"topic": "INVALID_TOPIC"})

        assert result["count"] == 0
        assert "error" in result
        assert "Invalid topic" in result["error"]

    def test_valid_topics_list(self):
        """Verify all valid topics are documented."""
        expected = [
            "WORLD",
            "NATION",
            "BUSINESS",
            "TECHNOLOGY",
            "ENTERTAINMENT",
            "SCIENCE",
            "SPORTS",
            "HEALTH",
        ]
        assert VALID_TOPICS == expected


class TestFetchGoogleNewsByLocation:
    """Test fetch_google_news_by_location probe."""

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_location_success(self, mock_fetch):
        """Test successful location fetch."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_by_location.invoke({"location": "New York"})

        assert result["count"] == 2
        assert result["location"] == "New York"
        assert "/geo/" in result["feed_url"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_fetch_location_url_encoded(self, mock_fetch):
        """Test location is properly URL encoded."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = fetch_google_news_by_location.invoke({"location": "San Francisco"})

        assert (
            "San+Francisco" in result["feed_url"]
            or "San%20Francisco" in result["feed_url"]
        )


class TestSearchGoogleNews:
    """Test search_google_news probe."""

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_basic(self, mock_fetch):
        """Test basic search."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news.invoke({"query": "Tesla"})

        assert result["count"] == 2
        assert result["query"] == "Tesla"
        assert "/search?" in result["feed_url"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_with_when(self, mock_fetch):
        """Test search with time filter."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news.invoke(
            {
                "query": "Tesla",
                "when": "1h",
            }
        )

        assert "when:1h" in result["query"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_with_date_range(self, mock_fetch):
        """Test search with date range."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news.invoke(
            {
                "query": "earnings",
                "after": "2024-01-01",
                "before": "2024-01-31",
            }
        )

        assert "after:2024-01-01" in result["query"]
        assert "before:2024-01-31" in result["query"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_with_site_filter(self, mock_fetch):
        """Test search restricted to specific site."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news.invoke(
            {
                "query": "Boeing",
                "site": "reuters.com",
            }
        )

        assert "site:reuters.com" in result["query"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_with_intitle(self, mock_fetch):
        """Test search with title filter."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news.invoke(
            {
                "query": "AI",
                "intitle": "OpenAI",
            }
        )

        assert "intitle:OpenAI" in result["query"]


class TestSearchGoogleNewsByCompany:
    """Test search_google_news_by_company probe."""

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_company_name_only(self, mock_fetch):
        """Test search with company name only."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news_by_company.invoke(
            {
                "company_name": "Apple",
            }
        )

        assert result["company"] == "Apple"
        assert '"Apple"' in result["query"]
        assert result["ticker"] is None

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_company_with_ticker(self, mock_fetch):
        """Test search with company name and ticker."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news_by_company.invoke(
            {
                "company_name": "Apple",
                "ticker": "AAPL",
            }
        )

        assert result["company"] == "Apple"
        assert result["ticker"] == "AAPL"
        assert '"Apple"' in result["query"]
        assert "AAPL" in result["query"]
        assert "OR" in result["query"]

    @patch("astro.probes.google_news._fetch_rss")
    def test_search_company_with_time_filter(self, mock_fetch):
        """Test company search with time filter."""
        mock_fetch.return_value = SAMPLE_RSS_XML

        result = search_google_news_by_company.invoke(
            {
                "company_name": "Microsoft",
                "when": "7d",
            }
        )

        assert "when:7d" in result["query"]


class TestErrorHandling:
    """Test error handling in probes."""

    @patch("astro.probes.google_news._fetch_rss")
    def test_http_error_handled(self, mock_fetch):
        """Test HTTP errors are handled gracefully."""
        import httpx

        mock_fetch.side_effect = httpx.HTTPError("Connection failed")

        result = fetch_google_news_headlines.invoke({})

        assert result["count"] == 0
        assert result["articles"] == []
        assert "error" in result
        assert "Connection failed" in result["error"]
