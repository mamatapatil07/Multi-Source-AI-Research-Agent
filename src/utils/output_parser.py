"""
Output parser for LLM JSON responses.
Handles common issues: markdown fences, trailing commas, single quotes, etc.
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_json_response(text: str) -> dict:
    """
    Parse a JSON response from an LLM, handling common formatting issues.

    Returns the parsed dict on success.
    Returns {"error": "parse_failed", "raw": text} on failure.
    """
    if not text or not text.strip():
        return {"error": "empty_response", "raw": ""}

    cleaned = text.strip()

    # Step 1: Strip markdown code fences
    # Handles ```json ... ``` and ``` ... ```
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    fence_match = re.search(fence_pattern, cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Step 2: If the text doesn't start with { or [, try to find JSON in it
    if not cleaned.startswith(("{", "[")):
        json_match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(1)

    # Step 3: Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 4: Fix trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Step 5: Replace single quotes with double quotes (risky but common)
    fixed2 = cleaned.replace("'", '"')
    try:
        return json.loads(fixed2)
    except json.JSONDecodeError:
        pass

    # Step 6: Try fixing common issues together
    fixed3 = re.sub(r",\s*([}\]])", r"\1", fixed2)
    try:
        return json.loads(fixed3)
    except json.JSONDecodeError:
        pass

    logger.warning("JSON parse failed after all attempts. Raw text: %s", text[:200])
    return {"error": "parse_failed", "raw": text}


def safe_get(data: dict, key: str, default=None):
    """Safely get a nested key from a parsed JSON dict."""
    if isinstance(data, dict):
        return data.get(key, default)
    return default
