"""
Web Search Tool — Tavily API wrapper for ResearchFlow.
"""

import logging
import os

from tavily import TavilyClient

logger = logging.getLogger(__name__)

# Max characters kept per individual search result
_MAX_CONTENT_CHARS = 1500  # ≈ 500 tokens


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web via Tavily and return cleaned results.

    Returns a list of dicts with keys: title, url, content.
    On any failure the function returns an empty list (never raises).
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("TAVILY_API_KEY not set — skipping web search")
        return []

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

        results: list[dict] = []
        for item in response.get("results", []):
            content = item.get("content", "")
            # Truncate long content
            if len(content) > _MAX_CONTENT_CHARS:
                content = content[:_MAX_CONTENT_CHARS] + "…"

            results.append(
                {
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "content": content,
                }
            )

        logger.info("web_search(%s) → %d results", query, len(results))
        return results

    except Exception as exc:
        logger.error("web_search failed: %s", exc)
        return []
