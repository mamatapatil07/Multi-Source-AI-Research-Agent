# Agent Graph — LangGraph Architecture

## Overview
ResearchFlow uses a LangGraph StateGraph with 5 nodes and conditional edges.
The agent follows: Plan → Research → Synthesize → Critique → Revise (or loop back).

## State Schema

```python
from typing import TypedDict, List, Optional
from pydantic import BaseModel

class SourceResult(BaseModel):
    """A single piece of information from a source."""
    content: str            # The extracted information
    source_type: str        # "web" | "wikipedia" | "pdf"
    source_url: str         # URL or filename
    source_title: str       # Title of the article/page/document
    relevance_score: float  # 0.0 to 1.0, how relevant to the query

class Citation(BaseModel):
    """A citation reference in the final report."""
    id: int                 # Citation number [1], [2], etc.
    source_title: str
    source_url: str
    source_type: str
    accessed_date: str      # ISO date string

class ReportSection(BaseModel):
    """A section of the final report."""
    heading: str
    content: str            # Text with inline citation references like [1], [2]
    citation_ids: List[int] # Which citations this section uses

class CritiqueResult(BaseModel):
    """Output of the critic node."""
    overall_quality: str        # "good" | "needs_revision"
    gaps: List[str]             # Missing topics or perspectives
    unsupported_claims: List[str]  # Claims without citations
    suggestions: List[str]      # Specific improvements to make
    additional_searches: List[str] # New queries to run if gaps found

class AgentState(TypedDict):
    """The full state passed between nodes."""
    # Input
    query: str                          # User's research topic/question
    pdf_texts: Optional[List[str]]      # Extracted text from uploaded PDFs

    # Planning
    research_plan: List[str]            # List of sub-queries to search
    search_queries: List[str]           # Actual search strings for tools

    # Research
    source_results: List[SourceResult]  # All gathered source material

    # Synthesis
    report_sections: List[ReportSection]  # Structured report sections
    citations: List[Citation]             # All citations used

    # Reflection
    critique: Optional[CritiqueResult]  # Critic's assessment
    revision_count: int                  # How many revisions done (max 1)

    # Agent Trace (for UI display)
    agent_logs: List[str]               # Human-readable log of agent actions
```

## Node Definitions

### Node 1: Planner
- **Input**: `query`, `pdf_texts`
- **LLM**: Llama 3.3 70B (needs strong reasoning)
- **Action**: Break the user's query into 3-5 research sub-questions. Decide which tools to use for each sub-question.
- **Output**: Updates `research_plan`, `search_queries`, `agent_logs`

### Node 2: Researcher
- **Input**: `search_queries`, `pdf_texts`
- **LLM**: Llama 3.1 8B (only for summarizing tool results)
- **Tools Called**: `tavily_search`, `wikipedia_search`, `pdf_reader`
- **Action**: Execute each search query using the appropriate tool. Summarize and score each result. Add delay between API calls (2s) to respect Groq TPM limits.
- **Output**: Updates `source_results`, `agent_logs`

### Node 3: Synthesizer
- **Input**: `query`, `source_results`
- **LLM**: Llama 3.3 70B (needs reasoning to organize and cite)
- **Action**: Organize source results into a coherent, structured report with sections and inline citations. Every factual claim must have a citation reference.
- **Output**: Updates `report_sections`, `citations`, `agent_logs`

### Node 4: Critic
- **Input**: `query`, `report_sections`, `citations`, `source_results`
- **LLM**: Llama 3.3 70B (needs strong reasoning to evaluate)
- **Action**: Review the report for gaps, unsupported claims, missing perspectives, and factual consistency. Output a structured critique.
- **Output**: Updates `critique`, `agent_logs`

### Node 5: Reviser
- **Input**: `report_sections`, `citations`, `critique`, `source_results`
- **LLM**: Llama 3.3 70B
- **Action**: Revise the report based on the critique. Fill gaps using existing source_results. If critique suggested additional searches, run them first.
- **Output**: Updates `report_sections`, `citations`, `revision_count`, `agent_logs`

## Edge Definitions

```
START → planner
planner → researcher
researcher → synthesizer
synthesizer → critic
critic → should_revise (conditional edge)
    - if critique.overall_quality == "needs_revision" AND revision_count < 1:
        → reviser
    - else:
        → END
reviser → END
```

## Graph Visualization

```
┌─────────┐
│  START   │
└────┬─────┘
     │
┌────▼─────┐
│  Planner  │  Break query into sub-questions
└────┬─────┘
     │
┌────▼──────┐
│ Researcher │  Search web, Wikipedia, PDFs
└────┬──────┘
     │
┌────▼───────┐
│ Synthesizer │  Draft structured report
└────┬───────┘
     │
┌────▼─────┐
│  Critic   │  Review for gaps and issues
└────┬─────┘
     │
     ▼
 ┌────────────┐    needs_revision     ┌─────────┐
 │ Should      │ ──────────────────── │ Reviser │ ──── END
 │ Revise?     │                      └─────────┘
 └─────┬──────┘
       │ good
       ▼
      END
```

## Rate Limit Strategy
- Insert `asyncio.sleep(2)` between consecutive Groq API calls
- Use Llama 3.1 8B for summarization tasks (lower token usage)
- Use Llama 3.3 70B only for planning, synthesis, critique, revision
- Truncate tool outputs to max 500 tokens before passing to LLM
- Total LLM calls per run: ~7-10 (well within 30 RPM and 14,400 RPD)
