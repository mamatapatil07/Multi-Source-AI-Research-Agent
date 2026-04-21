"""
Wikipedia Search Tool for ResearchFlow.
Uses the wikipedia library directly (no API key needed).
"""

import logging

import wikipedia

logger = logging.getLogger(__name__)

_MAX_CHARS = 2000  # ≈ 650 tokens


def wiki_search(query: str) -> dict:
    """
    Search Wikipedia and return the top article summary.

    Returns a dict with keys: title, url, content.
    On any failure returns a dict with empty strings (never raises).
    """
    empty = {"title": "", "url": "", "content": ""}

    try:
        # Search for matching page titles
        search_results = wikipedia.search(query, results=3)
        if not search_results:
            logger.info("wiki_search(%s) → no results", query)
            return empty

        # Try each result until one works (handles disambiguation)
        for page_title in search_results:
            try:
                page = wikipedia.page(page_title, auto_suggest=False)
                content = page.summary
                if len(content) > _MAX_CHARS:
                    content = content[:_MAX_CHARS] + "…"

                result = {
                    "title": page.title,
                    "url": page.url,
                    "content": content,
                }
                logger.info("wiki_search(%s) → %s", query, page.title)
                return result

            except wikipedia.DisambiguationError as de:
                # Pick the first option from the disambiguation list
                if de.options:
                    try:
                        page = wikipedia.page(de.options[0], auto_suggest=False)
                        content = page.summary
                        if len(content) > _MAX_CHARS:
                            content = content[:_MAX_CHARS] + "…"
                        return {
                            "title": page.title,
                            "url": page.url,
                            "content": content,
                        }
                    except Exception:
                        continue
            except wikipedia.PageError:
                continue

        logger.info("wiki_search(%s) → all results failed", query)
        return empty

    except Exception as exc:
        logger.error("wiki_search failed: %s", exc)
        return empty
