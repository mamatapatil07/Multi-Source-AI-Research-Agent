"""
Planner Node — breaks the user's query into a research plan.
"""

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.llm import get_llm, MODEL_LARGE
from src.agent.prompts.templates import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from src.utils.output_parser import parse_json_response
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


async def planner_node(state: AgentState) -> dict:
    """
    Break the user's query into 3-5 research sub-questions.
    Each sub-question is assigned a tool and search query.
    """
    query = state["query"]
    pdf_available = len(state.get("pdf_texts", [])) > 0

    logs = list(state.get("agent_logs", []))
    logs.append("🔍 **Planner**: Analyzing query and creating research plan...")

    # Build the prompt
    user_msg = PLANNER_USER_PROMPT.format(
        query=query,
        pdf_available=str(pdf_available).lower(),
    )

    # Call LLM
    llm = get_llm(model=MODEL_LARGE, temperature=0.3)
    rate_limiter.wait_sync()

    try:
        response = llm.invoke([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        parsed = parse_json_response(response.content)

        if "error" in parsed:
            logger.warning("Planner JSON parse failed, using fallback plan")
            research_plan = _fallback_plan(query, pdf_available)
        else:
            research_plan = parsed.get("research_plan", [])

        # Validate plan has at least 2 different tools
        tools_used = {item.get("tool", "") for item in research_plan}
        if len(tools_used) < 2 and not pdf_available:
            # Add a Wikipedia search if only web_search was planned
            if "wikipedia_search" not in tools_used:
                research_plan.append({
                    "sub_question": f"Background information about {query}",
                    "tool": "wikipedia_search",
                    "search_query": query,
                    "reasoning": "Added for source diversity",
                })

        plan_summary = "\n".join(
            f"  {i+1}. [{item.get('tool', '?')}] {item.get('sub_question', '?')}"
            for i, item in enumerate(research_plan)
        )
        logs.append(f"📋 **Plan created** ({len(research_plan)} steps):\n{plan_summary}")

        return {
            "research_plan": research_plan,
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.error("Planner node failed: %s", exc)
        research_plan = _fallback_plan(query, pdf_available)
        logs.append(f"⚠️ **Planner**: Using fallback plan due to error")
        return {
            "research_plan": research_plan,
            "agent_logs": logs,
        }


def _fallback_plan(query: str, pdf_available: bool) -> list[dict]:
    """Generate a basic research plan when LLM fails."""
    plan = [
        {
            "sub_question": f"What is {query}?",
            "tool": "wikipedia_search",
            "search_query": query,
            "reasoning": "Get background information",
        },
        {
            "sub_question": f"Latest developments in {query}",
            "tool": "web_search",
            "search_query": f"{query} latest news 2024 2025",
            "reasoning": "Get current information",
        },
        {
            "sub_question": f"Key facts and data about {query}",
            "tool": "web_search",
            "search_query": f"{query} facts statistics",
            "reasoning": "Get supporting data",
        },
    ]
    if pdf_available:
        plan.append({
            "sub_question": f"Information from uploaded documents about {query}",
            "tool": "pdf_reader",
            "search_query": query,
            "reasoning": "Check user's documents",
        })
    return plan
