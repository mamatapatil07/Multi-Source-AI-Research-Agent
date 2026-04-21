# PRD — Multi-Source Research Agent

## Project Name
**ResearchFlow** — An AI-powered multi-source research agent with self-reflection

## Problem Statement
Researchers, students, and professionals waste hours manually searching the web, reading PDFs, and cross-referencing Wikipedia to compile research on a topic. The output is often unstructured, missing citations, and lacks critical self-review.

## Solution
An autonomous research agent that:
1. Accepts a research topic or question
2. Plans a research strategy (what to search, what sources to check)
3. Executes searches across multiple sources (web, Wikipedia, uploaded PDFs)
4. Synthesizes findings into a structured report with proper citations
5. Self-critiques the report for gaps, hallucinations, and missing perspectives
6. Revises the report based on its own critique
7. Delivers a final, cited, structured report to the user

## Target Users
- Students writing research papers
- Professionals doing market or competitive research
- Anyone who needs a comprehensive, cited summary on a topic

## Success Criteria
- Agent uses at least 2 different source types per query
- Final report includes inline citations for every claim
- Reflection loop catches at least 1 gap or issue per run
- End-to-end latency under 60 seconds for typical queries
- Streamlit UI shows real-time agent thought process

## User Flow
```
Enter Topic → Agent Plans → Searches Sources → Drafts Report
    → Critic Reviews → Agent Revises → Final Report Displayed
```

## Scope
### In Scope (MVP)
- Web search via Tavily API
- Wikipedia lookup
- PDF text extraction and Q&A (user-uploaded PDFs)
- LangGraph orchestration with conditional edges
- Reflection/critique loop (1 iteration)
- Structured output with citations (Pydantic models)
- Streamlit UI with real-time agent state display
- Groq API (Llama 3.3 70B + Llama 3.1 8B)

### Out of Scope (v1)
- Multi-turn conversation / follow-up questions
- Persistent memory across sessions
- User authentication
- PDF OCR (scanned documents)
- Multi-language support

## Recruiter-Facing Value
This project demonstrates three core GenAI engineering patterns:
1. **Agent Orchestration** — LangGraph state machine with conditional routing
2. **Tool Use** — Multiple external tools with structured I/O
3. **Reflection** — Self-critique loop that improves output quality

## Key Differentiators vs Generic Research Agents
- Transparent agent reasoning shown in UI (not a black box)
- Cost-optimized dual-model routing (70B for reasoning, 8B for summarization)
- Structured Pydantic output, not raw text dumps
- Reflection with specific critique dimensions (not vague "improve this")
