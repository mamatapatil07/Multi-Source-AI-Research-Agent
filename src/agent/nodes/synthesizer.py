"""
Synthesizer Node — drafts a structured research report from source materials.
"""

import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.llm import get_llm, MODEL_LARGE
from src.agent.prompts.templates import SYNTHESIZER_SYSTEM_PROMPT, SYNTHESIZER_USER_PROMPT
from src.utils.output_parser import parse_json_response
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


async def synthesizer_node(state: AgentState) -> dict:
    """
    Synthesize all source results into a structured report with citations.
    """
    query = state["query"]
    source_results = state.get("source_results", [])
    logs = list(state.get("agent_logs", []))

    logs.append("✍️ **Synthesizer**: Drafting research report...")

    if not source_results:
        logs.append("⚠️ No source results available. Cannot generate report.")
        return {
            "report_sections": [{
                "heading": "No Results Found",
                "content": "The research agent could not find relevant information for this query. "
                           "Please try rephrasing your question or providing more context.",
                "citation_ids": [],
            }],
            "citations": [],
            "agent_logs": logs,
        }

    # Format sources for the prompt
    sources_text = _format_sources(source_results)

    user_msg = SYNTHESIZER_USER_PROMPT.format(
        query=query,
        sources_text=sources_text,
    )

    llm = get_llm(model=MODEL_LARGE, temperature=0.4)
    rate_limiter.wait_sync()

    try:
        response = llm.invoke([
            SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        parsed = parse_json_response(response.content)

        if "error" in parsed:
            logger.warning("Synthesizer JSON parse failed, using raw response")
            report_sections = [{
                "heading": "Research Findings",
                "content": response.content[:3000],
                "citation_ids": [],
            }]
            citations = []
        else:
            report_sections = parsed.get("sections", [])
            citations = parsed.get("citations", [])

            # Ensure citations have accessed_date
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            for cit in citations:
                if "accessed_date" not in cit:
                    cit["accessed_date"] = today

        section_count = len(report_sections)
        citation_count = len(citations)
        logs.append(
            f"📄 **Report drafted**: {section_count} sections, "
            f"{citation_count} citations"
        )

        return {
            "report_sections": report_sections,
            "citations": citations,
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.error("Synthesizer node failed: %s", exc)
        logs.append(f"⚠️ **Synthesizer** failed: {str(exc)[:100]}")
        return {
            "report_sections": [{
                "heading": "Error",
                "content": f"Report generation failed: {str(exc)[:200]}",
                "citation_ids": [],
            }],
            "citations": [],
            "agent_logs": logs,
        }


def _format_sources(source_results: list[dict]) -> str:
    """Format source results into a numbered text block for the prompt."""
    parts: list[str] = []
    for i, sr in enumerate(source_results, 1):
        source_type = sr.get("source_type", "unknown")
        title = sr.get("source_title", "Untitled")
        url = sr.get("source_url", "")
        content = sr.get("content", "")
        parts.append(
            f"[Source {i}] ({source_type}) {title}\n"
            f"URL: {url}\n"
            f"Content: {content}\n"
        )
    return "\n".join(parts)
