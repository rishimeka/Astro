"""Wikipedia probes for searching and fetching article content.

Provides probes for accessing Wikipedia's free API:
- Search for articles by keyword
- Fetch full or section-filtered article content
- Company-focused research with automatic section extraction

No API key required. Uses Wikipedia's public REST API.
"""

import re
import time
from typing import Any
from urllib.parse import quote

import requests

from astro.core.probes.decorator import probe

# Wikipedia API base URLs
SEARCH_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "Astro/1.0 (AI Research Platform)"}

# Rate limiting
_last_call_time = 0.0


def _rate_limit() -> None:
    """Enforce 0.5 second delay between Wikipedia API calls."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < 0.5:
        time.sleep(0.5 - elapsed)
    _last_call_time = time.time()


def _clean_wikitext(wikitext: str) -> str:
    """Strip wikitext markup to produce clean readable text.

    Args:
        wikitext: Raw wikitext content from Wikipedia API.

    Returns:
        Cleaned plain text.
    """
    text = wikitext

    # Remove ref tags and contents
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^/>]*/>", "", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove template syntax {{ ... }}
    # Handle nested templates by iterating
    depth = 0
    for _ in range(10):
        cleaned = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if cleaned == text:
            break
        text = cleaned
        depth += 1

    # Convert [[link|display]] to display, [[link]] to link
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)

    # Remove [external links]
    text = re.sub(r"\[https?://[^\]]*\]", "", text)

    # Remove file/image references
    text = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", text, flags=re.IGNORECASE)

    # Convert table rows: keep pipe-separated
    text = re.sub(r"\{\|[^\n]*\n", "", text)
    text = re.sub(r"\|\}", "", text)
    text = re.sub(r"^\|-.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^!(.*)$", r"\1", text, flags=re.MULTILINE)

    # Clean up bold/italic markup
    text = re.sub(r"'{2,5}", "", text)

    # Remove category links
    text = re.sub(r"\[\[Category:[^\]]*\]\]", "", text, flags=re.IGNORECASE)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _extract_sections(wikitext: str, section_names: list[str]) -> dict[str, str]:
    """Extract named sections from wikitext, including all subsections.

    When a level-2 heading (==Foo==) matches, captures everything up to the
    next same-level-or-higher heading, so subsections are included.

    Args:
        wikitext: Raw wikitext content.
        section_names: List of section names to extract (case-insensitive).

    Returns:
        Dict mapping found section names to their cleaned text content.
    """
    section_pattern = re.compile(r"^(={2,})\s*(.+?)\s*\1\s*$", re.MULTILINE)
    matches = list(section_pattern.finditer(wikitext))

    sections: dict[str, str] = {}
    target_names = [s.strip().lower() for s in section_names]

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        if heading.lower() in target_names:
            level = len(match.group(1))  # number of '=' signs
            start = match.end()
            # Find the next heading at the same or higher (fewer =) level
            end = len(wikitext)
            for j in range(i + 1, len(matches)):
                next_level = len(matches[j].group(1))
                if next_level <= level:
                    end = matches[j].start()
                    break
            content = _clean_wikitext(wikitext[start:end])
            if content.strip():
                sections[heading] = content.strip()

    return sections


def _is_disambiguation(wikitext: str) -> list[str]:
    """Check if page is a disambiguation page and extract options.

    Args:
        wikitext: Raw wikitext content.

    Returns:
        List of page title options if disambiguation, empty list otherwise.
    """
    if "{{disambiguation}}" in wikitext.lower() or "{{disambig" in wikitext.lower():
        # Extract linked page titles
        links = re.findall(r"\[\[([^|\]]+?)(?:\|[^\]]+?)?\]\]", wikitext)
        # Filter out non-article links
        filtered = [
            l for l in links
            if not l.startswith(("File:", "Image:", "Category:", "Wikipedia:"))
        ]
        return filtered[:20]
    return []


def _search_wikipedia(query: str, max_results: int = 5) -> dict[str, Any]:
    """Raw implementation of Wikipedia search (callable internally)."""
    _rate_limit()
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": min(max_results, 20),
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("query", {}).get("search", []):
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            results.append({
                "title": item.get("title", ""),
                "snippet": snippet,
                "pageid": item.get("pageid"),
                "wordcount": item.get("wordcount", 0),
            })

        return {
            "results": results,
            "count": len(results),
            "query": query,
        }
    except Exception as e:
        return {"results": [], "count": 0, "query": query, "error": str(e)}


@probe
def search_wikipedia(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search Wikipedia for articles matching a query and return page titles, descriptions, and IDs.

    Useful for finding relevant Wikipedia pages before fetching their full content.
    Returns a list of matching articles with titles and snippets.

    Args:
        query: The search query to find Wikipedia articles.
        max_results: Maximum number of results to return (1-20, default 5).

    Returns:
        Dictionary with search results including titles, snippets, and page IDs.
    """
    return _search_wikipedia(query, max_results)


def _get_wikipedia_page(title: str, sections: str = "") -> dict[str, Any]:
    """Raw implementation of Wikipedia page fetch (callable internally)."""
    _rate_limit()
    try:
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            return {
                "title": title,
                "content": "",
                "error": data["error"].get("info", "Page not found"),
                "url": f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
            }

        parse_data = data.get("parse", {})
        page_title = parse_data.get("title", title)
        wikitext = parse_data.get("wikitext", {}).get("*", "")

        # Check for disambiguation
        disambig_options = _is_disambiguation(wikitext)
        if disambig_options:
            return {
                "title": page_title,
                "content": "",
                "disambiguation": True,
                "options": disambig_options,
                "url": f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}",
            }

        url = f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}"

        # Extract specific sections or full content
        if sections:
            section_names = [s.strip() for s in sections.split(",")]
            extracted = _extract_sections(wikitext, section_names)
            if extracted:
                content = "\n\n".join(
                    f"## {name}\n{text}" for name, text in extracted.items()
                )
                truncated = len(content) > 15000
                return {
                    "title": page_title,
                    "content": content[:15000],
                    "sections_found": list(extracted.keys()),
                    "sections_requested": section_names,
                    "url": url,
                    "truncated": truncated,
                }
            # Sections not found, fall through to full content

        # Full page content
        content = _clean_wikitext(wikitext)
        truncated = len(content) > 15000

        # Extract section headings for reference
        section_headings = re.findall(
            r"^={2}\s*(.+?)\s*={2}\s*$", wikitext, re.MULTILINE
        )

        return {
            "title": page_title,
            "content": content[:15000],
            "sections_found": section_headings,
            "url": url,
            "truncated": truncated,
        }
    except Exception as e:
        return {
            "title": title,
            "content": "",
            "error": str(e),
            "url": f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
        }


@probe
def get_wikipedia_page(title: str, sections: str = "") -> dict[str, Any]:
    """Fetch the content of a Wikipedia page by title with optional section filtering.

    Retrieves full article content or specific sections. Useful for getting comprehensive
    company histories, acquisition lists, and corporate event timelines. Content is cleaned
    of wiki markup and truncated to 15,000 characters to manage context size.

    If sections parameter is provided (comma-separated section names like
    "Acquisitions,History,Mergers"), only those sections are extracted and returned.

    Args:
        title: The exact Wikipedia page title to fetch.
        sections: Optional comma-separated section names to extract (e.g. "History,Acquisitions").
                  If empty, returns full page content.

    Returns:
        Dictionary with page title, cleaned text content, URL, sections found,
        and whether content was truncated.
    """
    return _get_wikipedia_page(title, sections)


# Business-relevant sections to look for in company pages
_BUSINESS_SECTIONS = [
    "History",
    "Acquisitions",
    "Mergers and acquisitions",
    "Mergers",
    "Corporate affairs",
    "Subsidiaries",
    "Divestitures",
    "Divestments",
    "Investments",
    "Products and services",
    "Products",
    "Services",
    "Operations",
    "Corporate history",
    "Key acquisitions",
    "Financing and acquisitions",
    "Subsidiaries, products, services",
]


@probe
def get_wikipedia_company_info(company_name: str) -> dict[str, Any]:
    """Fetch business-relevant information from a company's Wikipedia page.

    Optimized for corporate research: automatically searches for the company, finds the
    best matching Wikipedia page, and extracts business-relevant sections including
    acquisition history, mergers, divestitures, subsidiaries, and corporate timeline.

    If specific business sections aren't found, falls back to returning the full page
    content (truncated to 15,000 characters).

    Args:
        company_name: The name of the company to research (e.g. "Square Inc", "Microsoft").

    Returns:
        Dictionary with company name matched, page URL, extracted business sections,
        and any acquisition/merger content found.
    """
    # First search for the company (use raw function, not the StructuredTool)
    search_result = _search_wikipedia(company_name, max_results=3)
    if search_result.get("error") or not search_result.get("results"):
        return {
            "company_name": company_name,
            "error": search_result.get("error", "No Wikipedia pages found"),
            "results": [],
        }

    # Use the first result
    best_match = search_result["results"][0]["title"]

    # Try fetching business-relevant sections
    sections_str = ",".join(_BUSINESS_SECTIONS)
    page_result = _get_wikipedia_page(best_match, sections=sections_str)

    # If disambiguation, return options
    if page_result.get("disambiguation"):
        return {
            "company_name": company_name,
            "disambiguation": True,
            "options": page_result.get("options", []),
            "url": page_result.get("url", ""),
        }

    # If we got sections, great
    if page_result.get("sections_found"):
        return {
            "company_name": company_name,
            "matched_title": page_result.get("title", best_match),
            "url": page_result.get("url", ""),
            "sections": page_result.get("sections_found", []),
            "content": page_result.get("content", ""),
            "truncated": page_result.get("truncated", False),
            "search_results": [r["title"] for r in search_result["results"]],
        }

    # Fallback: get full page
    full_page = _get_wikipedia_page(best_match)
    return {
        "company_name": company_name,
        "matched_title": full_page.get("title", best_match),
        "url": full_page.get("url", ""),
        "sections": full_page.get("sections_found", []),
        "content": full_page.get("content", ""),
        "truncated": full_page.get("truncated", False),
        "note": "Business-specific sections not found, returning full page content",
        "search_results": [r["title"] for r in search_result["results"]],
    }
