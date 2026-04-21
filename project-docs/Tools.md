# Tools Specification

## Overview
ResearchFlow uses 3 external tools. Each tool is defined as a LangChain Tool
with a clear input schema, output format, and error handling strategy.

---

## Tool 1: Web Search (Tavily)

### Purpose
Search the web for recent, relevant information on a topic.

### API Details
- **Provider**: Tavily API (https://tavily.com)
- **Free Tier**: 1,000 searches/month (more than enough for portfolio project)
- **API Key**: `TAVILY_API_KEY` environment variable

### Input Schema
```python
class TavilySearchInput(BaseModel):
    query: str          # Search query, max 200 chars
    max_results: int = 5  # Number of results to return
```

### Output Format
```python
class TavilySearchOutput(BaseModel):
    results: List[dict]  # Each dict has: title, url, content (snippet)
```

### Implementation Notes
- Use `TavilySearchResults` from `langchain_community.tools.tavily_search`
- Truncate each result's `content` to 500 tokens before returning
- If API fails, return empty results with error logged (don't crash the agent)

### Error Handling
- 429 Rate Limit: Wait 5s and retry once
- Timeout: Return empty results after 10s
- Invalid query: Return empty results, log warning

---

## Tool 2: Wikipedia Search

### Purpose
Get structured, reliable background information on well-known topics,
people, events, and concepts.

### API Details
- **Provider**: Wikipedia API (free, no key needed)
- **Library**: `langchain_community.tools.WikipediaQueryRun`

### Input Schema
```python
class WikipediaSearchInput(BaseModel):
    query: str          # Topic to search on Wikipedia
    max_chars: int = 2000  # Max characters to return from article
```

### Output Format
```python
class WikipediaSearchOutput(BaseModel):
    title: str       # Article title
    summary: str     # Article content (truncated to max_chars)
    url: str         # Wikipedia article URL
```

### Implementation Notes
- Use `WikipediaQueryRun` with `WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=2000)`
- Wikipedia is best for background/context, not for recent events
- The planner should prefer Tavily for current events, Wikipedia for concepts

### Error Handling
- Page not found: Return empty result, log "No Wikipedia article found"
- Disambiguation: Take the first result
- Timeout: Return empty results after 8s

---

## Tool 3: PDF Reader

### Purpose
Extract text from user-uploaded PDF files and answer questions
based on their content.

### API Details
- **Provider**: Local processing using PyPDF2
- **No API key needed**

### Input Schema
```python
class PDFReaderInput(BaseModel):
    question: str       # What to look for in the PDF
    pdf_index: int = 0  # Which uploaded PDF to read (if multiple)
```

### Output Format
```python
class PDFReaderOutput(BaseModel):
    relevant_text: str   # Extracted text relevant to the question
    source_file: str     # Filename of the PDF
    page_numbers: List[int]  # Which pages the text came from
```

### Implementation Notes
- PDFs are uploaded via Streamlit's `file_uploader`
- Extract text using PyPDF2 at upload time, store in session state
- For Q&A over PDF: chunk the text (500 tokens per chunk), use simple
  keyword/semantic matching to find relevant chunks
- Do NOT use a vector DB for MVP — simple chunking + LLM relevance
  scoring is sufficient and avoids extra infrastructure
- Limit to 3 PDFs, 50 pages each max

### Error Handling
- Corrupted PDF: Return error message, skip this source
- Empty PDF (scanned/image-only): Return "PDF contains no extractable text"
- PDF too large: Truncate to first 50 pages with warning

---

## Tool Registration with LangGraph

```python
from langchain_core.tools import tool

@tool
def web_search(query: str) -> str:
    """Search the web for current information on a topic.
    Use this for recent events, news, current data, and specific facts.
    Returns relevant web page snippets with URLs."""
    # Implementation here

@tool
def wikipedia_search(query: str) -> str:
    """Search Wikipedia for background information on a topic.
    Use this for established concepts, historical events, biographies,
    and scientific topics. Returns article summary with URL."""
    # Implementation here

@tool
def pdf_reader(question: str) -> str:
    """Search through uploaded PDF documents to find relevant information.
    Use this when the user has uploaded reference documents.
    Returns relevant text excerpts with page numbers."""
    # Implementation here
```

## Tool Selection Logic (for Planner node)

The planner decides which tools to use based on the query type:

| Query Type | Primary Tool | Secondary Tool |
|-----------|-------------|---------------|
| Recent events / news | Tavily | Wikipedia (for background) |
| Scientific concepts | Wikipedia | Tavily (for recent papers) |
| Person / biography | Wikipedia | Tavily (for recent news) |
| User's uploaded docs | PDF Reader | Tavily (for context) |
| Comparison / analysis | Tavily | Wikipedia |
| General knowledge | Wikipedia | Tavily |

The planner ALWAYS uses at least 2 different tool types per query to
demonstrate multi-source capability.
