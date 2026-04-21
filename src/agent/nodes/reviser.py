"""
Reviser Node — revises the report based on the critic's feedback.
May run additional searches if the critique identifies content gaps.
"""

import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.llm import get_llm, MODEL_LARGE
from src.agent.prompts.templates import REVISER_SYSTEM_PROMPT, REVISER_USER_PROMPT
from src.tools.web_search import web_search
from src.utils.output_parser import parse_json_response
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


async def reviser_node(state: AgentState) -> dict:
    """
    Revise the report based on critique feedback.
    Optionally runs additional searches for content gaps.
    """
    query = state["query"]
    report_sections = state.get("report_sections", [])
    citations = state.get("citations", [])
    critique = state.get("critique", {})
    source_results = list(state.get("source_results", []))
    revision_count = state.get("revision_count", 0)
    logs = list(state.get("agent_logs", []))

    logs.append("🔧 **Reviser**: Improving report based on critique...")

    # Run additional searches if the critique suggested them
    additional_searches = critique.get("additional_searches", [])
    if additional_searches:
        logs.append(f"  🔍 Running {len(additional_searches)} additional searches...")
        for search_query in additional_searches[:2]:  # Max 2 additional searches
            try:
                results = web_search(search_query, max_results=2)
                for result in results:
                    source_results.append({
                        "content": result["content"][:500],
                        "source_type": "web",
                        "source_url": result["url"],
                        "source_title": result["title"],
                        "relevance_score": 0.7,
                    })
                    logs.append(f"  📡 Found: {result['title'][:60]}")
            except Exception as exc:
                logger.warning("Additional search failed: %s", exc)

    # Format everything for the revision prompt
    sources_text = _format_all_sources(source_results)

    user_msg = REVISER_USER_PROMPT.format(
        query=query,
        report_json=json.dumps({"sections": report_sections, "citations": citations}, indent=2),
        critique_json=json.dumps(critique, indent=2),
        sources_text=sources_text,
    )

    llm = get_llm(model=MODEL_LARGE, temperature=0.3)
    rate_limiter.wait_sync()

    try:
        response = llm.invoke([
            SystemMessage(content=REVISER_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        parsed = parse_json_response(response.content)

        if "error" in parsed:
            logger.warning("Reviser JSON parse failed, keeping original report")
            logs.append("⚠️ Revision parse failed — keeping original report")
            return {
                "revision_count": revision_count + 1,
                "source_results": source_results,
                "agent_logs": logs,
            }

        revised_sections = parsed.get("sections", report_sections)
        revised_citations = parsed.get("citations", citations)

        # Ensure citations have accessed_date
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        for cit in revised_citations:
            if "accessed_date" not in cit:
                cit["accessed_date"] = today

        logs.append(
            f"✅ **Revision complete**: {len(revised_sections)} sections, "
            f"{len(revised_citations)} citations"
        )

        return {
            "report_sections": revised_sections,
            "citations": revised_citations,
            "revision_count": revision_count + 1,
            "source_results": source_results,
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.error("Reviser node failed: %s", exc)
        logs.append(f"⚠️ **Reviser** failed: {str(exc)[:100]}")
        return {
            "revision_count": revision_count + 1,
            "source_results": source_results,
            "agent_logs": logs,
        }


def _format_all_sources(source_results: list[dict]) -> str:
    """Format all sources for the revision prompt."""
    parts: list[str] = []
    for i, sr in enumerate(source_results, 1):
        parts.append(
            f"[Source {i}] ({sr.get('source_type', '?')}) "
            f"{sr.get('source_title', 'Untitled')}\n"
            f"URL: {sr.get('source_url', '')}\n"
            f"Content: {sr.get('content', '')}\n"
        )
    return "\n".join(parts)
