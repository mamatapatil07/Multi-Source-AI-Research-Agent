"""
Researcher Node — executes the research plan by calling tools
and summarizing results with the small model.
"""

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.llm import get_llm, MODEL_SMALL
from src.agent.prompts.templates import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_PROMPT
from src.tools.web_search import web_search
from src.tools.wiki_search import wiki_search
from src.tools.pdf_reader import search_pdf_text
from src.utils.output_parser import parse_json_response
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


async def researcher_node(state: AgentState) -> dict:
    """
    Execute each step of the research plan using the assigned tools.
    Summarize each result with the small model for token efficiency.
    """
    research_plan = state.get("research_plan", [])
    pdf_texts = state.get("pdf_texts", [])
    pdf_filenames = state.get("pdf_filenames", [])
    logs = list(state.get("agent_logs", []))
    source_results: list[dict] = list(state.get("source_results", []))

    logs.append(f"🔬 **Researcher**: Executing {len(research_plan)} research steps...")

    summarizer_llm = get_llm(model=MODEL_SMALL, temperature=0.1)

    for i, step in enumerate(research_plan):
        tool = step.get("tool", "web_search")
        search_query = step.get("search_query", "")
        sub_question = step.get("sub_question", search_query)

        logs.append(f"  📡 Step {i+1}: [{tool}] \"{search_query}\"")

        try:
            if tool == "web_search":
                results = web_search(search_query, max_results=3)
                for result in results:
                    # Summarize each web result
                    summary = await _summarize_result(
                        summarizer_llm, sub_question,
                        result["title"], result["content"],
                    )
                    if summary != "NOT_RELEVANT":
                        source_results.append({
                            "content": summary,
                            "source_type": "web",
                            "source_url": result["url"],
                            "source_title": result["title"],
                            "relevance_score": 0.8,
                        })

            elif tool == "wikipedia_search":
                result = wiki_search(search_query)
                if result["content"]:
                    summary = await _summarize_result(
                        summarizer_llm, sub_question,
                        result["title"], result["content"],
                    )
                    if summary != "NOT_RELEVANT":
                        source_results.append({
                            "content": summary,
                            "source_type": "wikipedia",
                            "source_url": result["url"],
                            "source_title": result["title"],
                            "relevance_score": 0.9,
                        })

            elif tool == "pdf_reader":
                for j, pdf_text in enumerate(pdf_texts):
                    filename = pdf_filenames[j] if j < len(pdf_filenames) else f"document_{j+1}.pdf"
                    pdf_result = search_pdf_text(pdf_text, sub_question, filename)
                    if pdf_result["relevant_text"]:
                        summary = await _summarize_result(
                            summarizer_llm, sub_question,
                            filename, pdf_result["relevant_text"],
                        )
                        if summary != "NOT_RELEVANT":
                            source_results.append({
                                "content": summary,
                                "source_type": "pdf",
                                "source_url": filename,
                                "source_title": filename,
                                "relevance_score": 0.85,
                            })

        except Exception as exc:
            logger.error("Research step %d failed: %s", i + 1, exc)
            logs.append(f"  ⚠️ Step {i+1} failed: {str(exc)[:100]}")

    # Deduplicate by source_url
    seen_urls: set[str] = set()
    unique_results: list[dict] = []
    for sr in source_results:
        url = sr.get("source_url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(sr)

    logs.append(f"✅ **Research complete**: Gathered {len(unique_results)} unique sources")

    return {
        "source_results": unique_results,
        "agent_logs": logs,
    }


async def _summarize_result(llm, question: str, title: str, content: str) -> str:
    """Summarize a single search result using the small model."""
    user_msg = SUMMARIZER_USER_PROMPT.format(
        question=question,
        source_title=title,
        raw_content=content[:1500],  # Hard truncate before sending
    )

    rate_limiter.wait_sync()

    try:
        response = llm.invoke([
            SystemMessage(content=SUMMARIZER_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])
        return response.content.strip()
    except Exception as exc:
        logger.error("Summarization failed: %s", exc)
        # Fallback: return truncated raw content
        return content[:500]
