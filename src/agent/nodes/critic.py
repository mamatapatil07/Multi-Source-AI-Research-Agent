"""
Critic Node — reviews the report for quality, gaps, and unsupported claims.
"""

import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.llm import get_llm, MODEL_LARGE
from src.agent.prompts.templates import CRITIC_SYSTEM_PROMPT, CRITIC_USER_PROMPT
from src.utils.output_parser import parse_json_response
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


async def critic_node(state: AgentState) -> dict:
    """
    Review the drafted report and produce a structured critique.
    """
    query = state["query"]
    report_sections = state.get("report_sections", [])
    citations = state.get("citations", [])
    logs = list(state.get("agent_logs", []))

    logs.append("🔎 **Critic**: Reviewing report quality...")

    # Format report for the prompt
    report_text = _format_report_for_review(report_sections)
    citations_text = _format_citations_for_review(citations)

    user_msg = CRITIC_USER_PROMPT.format(
        query=query,
        report_text=report_text,
        citations_text=citations_text,
    )

    llm = get_llm(model=MODEL_LARGE, temperature=0.2)
    rate_limiter.wait_sync()

    try:
        response = llm.invoke([
            SystemMessage(content=CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        parsed = parse_json_response(response.content)

        if "error" in parsed:
            logger.warning("Critic JSON parse failed, assuming report is good")
            critique = _default_critique("good")
        else:
            critique = {
                "overall_quality": parsed.get("overall_quality", "good"),
                "gaps": parsed.get("gaps", []),
                "unsupported_claims": parsed.get("unsupported_claims", []),
                "suggestions": parsed.get("suggestions", []),
                "additional_searches": parsed.get("additional_searches", []),
            }

        quality = critique["overall_quality"]
        gap_count = len(critique.get("gaps", []))
        suggestion_count = len(critique.get("suggestions", []))

        if quality == "needs_revision":
            logs.append(
                f"📝 **Critique result**: Needs revision — "
                f"{gap_count} gaps, {suggestion_count} suggestions"
            )
            for gap in critique.get("gaps", [])[:3]:
                logs.append(f"  • Gap: {gap}")
            for sug in critique.get("suggestions", [])[:3]:
                logs.append(f"  • Suggestion: {sug}")
        else:
            logs.append("✅ **Critique result**: Report quality is good!")

        return {
            "critique": critique,
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.error("Critic node failed: %s", exc)
        logs.append("⚠️ **Critic** failed — proceeding with current report")
        return {
            "critique": _default_critique("good"),
            "agent_logs": logs,
        }


def _default_critique(quality: str = "good") -> dict:
    """Return a default critique when parsing fails."""
    return {
        "overall_quality": quality,
        "gaps": [],
        "unsupported_claims": [],
        "suggestions": [],
        "additional_searches": [],
    }


def _format_report_for_review(sections: list[dict]) -> str:
    """Format report sections as readable text for the critic."""
    parts: list[str] = []
    for sec in sections:
        heading = sec.get("heading", "Untitled")
        content = sec.get("content", "")
        parts.append(f"## {heading}\n{content}")
    return "\n\n".join(parts)


def _format_citations_for_review(citations: list[dict]) -> str:
    """Format citations as a numbered list for the critic."""
    parts: list[str] = []
    for cit in citations:
        cid = cit.get("id", "?")
        title = cit.get("source_title", "Unknown")
        stype = cit.get("source_type", "")
        url = cit.get("source_url", "")
        parts.append(f"[{cid}] {title} ({stype}) — {url}")
    return "\n".join(parts)
