"""
Shared LLM client helpers for ResearchFlow.
Provides configured ChatGroq instances for different model tiers.
"""

import os
import logging

from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

# Model identifiers on Groq
MODEL_LARGE = "llama-3.3-70b-versatile"  # Planning, synthesis, critique
MODEL_SMALL = "llama-3.1-8b-instant"     # Summarization


def get_llm(model: str = MODEL_LARGE, temperature: float = 0.3) -> ChatGroq:
    """Return a configured ChatGroq instance."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
    )
