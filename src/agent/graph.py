"""
ResearchFlow Graph — LangGraph state graph assembly.
Wires together all agent nodes with conditional edges.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState, make_initial_state, format_report
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.synthesizer import synthesizer_node
from src.agent.nodes.critic import critic_node
from src.agent.nodes.reviser import reviser_node

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional edge: should we revise or finish?
# ---------------------------------------------------------------------------

def should_revise(state: AgentState) -> Literal["reviser", "end"]:
    """
    Decide whether to revise the report or finish.
    Revise only if:
      - The critic said 'needs_revision'
      - We haven't already revised (max 1 revision)
    """
    critique = state.get("critique")
    revision_count = state.get("revision_count", 0)

    if critique is None:
        return "end"

    quality = critique.get("overall_quality", "good")

    if quality == "needs_revision" and revision_count < 1:
        logger.info("Routing to reviser (quality=%s, revision_count=%d)", quality, revision_count)
        return "reviser"

    logger.info("Routing to end (quality=%s, revision_count=%d)", quality, revision_count)
    return "end"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct and compile the ResearchFlow agent graph."""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("reviser", reviser_node)

    # Add edges
    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "synthesizer")
    graph.add_edge("synthesizer", "critic")

    # Conditional edge after critic
    graph.add_conditional_edges(
        "critic",
        should_revise,
        {
            "reviser": "reviser",
            "end": END,
        },
    )

    # Reviser always goes to END
    graph.add_edge("reviser", END)

    compiled = graph.compile()
    logger.info("ResearchFlow graph compiled successfully")
    return compiled


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Compile once at module level
_compiled_graph = None


def get_graph():
    """Get or create the compiled graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


async def run_agent(
    query: str,
    pdf_texts: list[str] | None = None,
    pdf_filenames: list[str] | None = None,
) -> AgentState:
    """
    Run the full research agent pipeline.

    Args:
        query: The user's research topic or question.
        pdf_texts: Optional list of extracted PDF text strings.
        pdf_filenames: Optional list of PDF filenames.

    Returns:
        The final AgentState with report, citations, and logs.
    """
    graph = get_graph()
    initial_state = make_initial_state(query, pdf_texts, pdf_filenames)

    logger.info("Starting ResearchFlow agent for query: %s", query[:100])

    final_state = await graph.ainvoke(initial_state)

    logger.info(
        "Agent completed. Sections: %d, Citations: %d, Revisions: %d",
        len(final_state.get("report_sections", [])),
        len(final_state.get("citations", [])),
        final_state.get("revision_count", 0),
    )

    return final_state


def run_agent_sync(
    query: str,
    pdf_texts: list[str] | None = None,
    pdf_filenames: list[str] | None = None,
) -> AgentState:
    """Synchronous wrapper for run_agent."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an existing event loop (e.g., Streamlit)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    run_agent(query, pdf_texts, pdf_filenames),
                ).result()
            return result
        else:
            return loop.run_until_complete(
                run_agent(query, pdf_texts, pdf_filenames)
            )
    except RuntimeError:
        return asyncio.run(run_agent(query, pdf_texts, pdf_filenames))
