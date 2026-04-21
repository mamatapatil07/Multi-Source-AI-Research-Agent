"""
ResearchFlow Agent State
Defines all Pydantic models and the LangGraph AgentState TypedDict.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TypedDict, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic Models – used inside the state for structured data
# ---------------------------------------------------------------------------

class SourceResult(BaseModel):
    """A single piece of information retrieved from a source."""

    content: str = Field(description="The extracted/summarized information")
    source_type: str = Field(description="web | wikipedia | pdf")
    source_url: str = Field(description="URL or filename of the source")
    source_title: str = Field(description="Title of the article/page/document")
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How relevant this result is to the query",
    )

    def to_context_string(self, index: int) -> str:
        """Format this source for injection into an LLM prompt."""
        return (
            f"[Source {index}] ({self.source_type}) {self.source_title}\n"
            f"URL: {self.source_url}\n"
            f"Content: {self.content}\n"
        )


class Citation(BaseModel):
    """A citation reference in the final report."""

    id: int = Field(description="Citation number [1], [2], etc.")
    source_title: str = Field(default="")
    source_url: str = Field(default="")
    source_type: str = Field(default="web")
    accessed_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )


class ReportSection(BaseModel):
    """A section of the final research report."""

    heading: str = Field(description="Section heading")
    content: str = Field(
        description="Body text with inline citation refs like [1], [2]"
    )
    citation_ids: list[int] = Field(
        default_factory=list,
        description="Which citation IDs this section references",
    )


class CritiqueResult(BaseModel):
    """Structured output from the Critic node."""

    overall_quality: str = Field(
        description="good | needs_revision",
        default="good",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Missing topics or perspectives",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims in the report that lack citations",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Specific improvements to make",
    )
    additional_searches: list[str] = Field(
        default_factory=list,
        description="New queries to run if gaps are found",
    )


class ResearchPlanItem(BaseModel):
    """A single step in the research plan."""

    sub_question: str = Field(description="The sub-question to answer")
    tool: str = Field(description="web_search | wikipedia_search | pdf_reader")
    search_query: str = Field(description="The actual query string for the tool")
    reasoning: str = Field(default="", description="Why this step is needed")


# ---------------------------------------------------------------------------
# Agent State – the TypedDict passed between LangGraph nodes
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Full state passed between LangGraph nodes."""

    # --- Input ---
    query: str                                      # User's research topic
    pdf_texts: list[str]                            # Extracted text from uploaded PDFs
    pdf_filenames: list[str]                        # Names of uploaded PDF files

    # --- Planning ---
    research_plan: list[dict]                       # List of ResearchPlanItem dicts

    # --- Research ---
    source_results: list[dict]                      # List of SourceResult dicts

    # --- Synthesis ---
    report_sections: list[dict]                     # List of ReportSection dicts
    citations: list[dict]                           # List of Citation dicts

    # --- Reflection ---
    critique: Optional[dict]                        # CritiqueResult dict or None
    revision_count: int                             # Number of revisions done (max 1)

    # --- Agent Trace (for UI) ---
    agent_logs: list[str]                           # Human-readable logs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_initial_state(
    query: str,
    pdf_texts: list[str] | None = None,
    pdf_filenames: list[str] | None = None,
) -> AgentState:
    """Create a fresh AgentState with sensible defaults."""
    return AgentState(
        query=query,
        pdf_texts=pdf_texts or [],
        pdf_filenames=pdf_filenames or [],
        research_plan=[],
        source_results=[],
        report_sections=[],
        citations=[],
        critique=None,
        revision_count=0,
        agent_logs=[],
    )


def format_report(sections: list[dict], citations: list[dict]) -> str:
    """Render the report as a Markdown string."""
    lines: list[str] = []
    for sec in sections:
        lines.append(f"## {sec.get('heading', 'Untitled')}\n")
        lines.append(sec.get("content", "") + "\n")

    if citations:
        lines.append("\n---\n## References\n")
        for cit in citations:
            cid = cit.get("id", "?")
            title = cit.get("source_title", "Unknown")
            url = cit.get("source_url", "")
            stype = cit.get("source_type", "")
            date = cit.get("accessed_date", "")
            lines.append(f"[{cid}] {title} — *{stype}* — {url} (accessed {date})\n")

    return "\n".join(lines)
