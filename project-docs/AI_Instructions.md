# AI Instructions — Master Prompt for Code Generation

## Context
You are building a multi-source research agent called ResearchFlow.
Read ALL files in the /project-docs folder before generating any code.
These documents are your source of truth for architecture, tools, prompts, and structure.

## Build Order
Generate the project in this exact sequence. Do NOT skip ahead.
After each step, verify it runs without errors before proceeding.

### Step 1: State & Models
File: `src/agent/state.py`
- Implement all Pydantic models from AgentGraph.md (SourceResult, Citation,
  ReportSection, CritiqueResult)
- Implement AgentState TypedDict
- Add JSON serialization helpers for each model

### Step 2: Tools
Files: `src/tools/web_search.py`, `src/tools/wiki_search.py`, `src/tools/pdf_reader.py`
- Implement each tool exactly as specified in Tools.md
- Each tool must handle errors gracefully (never crash the agent)
- Each tool must truncate output to max 500 tokens
- Add logging for every tool call (tool name, query, result length)

### Step 3: Prompt Templates
File: `src/agent/prompts/templates.py`
- Copy all prompt templates from Prompts.md
- Use Python string templates with .format() for variable injection
- Each prompt must be a module-level constant (e.g., PLANNER_SYSTEM_PROMPT)

### Step 4: Agent Nodes
Files: `src/agent/nodes/planner.py`, `researcher.py`, `synthesizer.py`,
       `critic.py`, `reviser.py`
- Each node is an async function that takes AgentState and returns partial state update
- Use ChatGroq from langchain_groq for LLM calls
- Planner, Synthesizer, Critic, Reviser use llama-3.3-70b-versatile
- Researcher's summarizer uses llama-3.1-8b-instant
- Parse JSON responses with json.loads() wrapped in try/except
  (fallback: ask LLM to fix its own JSON)
- Add agent_logs entry for every action (for UI display)
- Use rate_limiter.wait() before every LLM call

### Step 5: Graph Assembly
File: `src/agent/graph.py`
- Build the StateGraph with all 5 nodes
- Add edges exactly as specified in AgentGraph.md
- Implement the conditional edge: should_revise function
- Compile the graph
- Export a run_agent(query, pdf_texts) function

### Step 6: Streamlit UI
File: `app.py`
- Single page layout with sidebar for PDF upload
- Main area: text input for research query + "Research" button
- After submission, show real-time agent progress:
  - Use st.status() or st.expander() for each agent step
  - Show which node is running, what tools are being called
  - Display agent_logs as they accumulate
- Final report rendered with proper headings and citations
- Citations displayed as a numbered list at the bottom
- Add download button for the report as Markdown

### Step 7: Rate Limiter
File: `src/utils/rate_limiter.py`
- Implement GroqRateLimiter as shown in TechStack.md
- 2-second minimum delay between calls
- Used by all nodes before LLM calls

### Step 8: Output Parser
File: `src/utils/output_parser.py`
- parse_json_response(text: str) -> dict
- Strip markdown code fences (```json ... ```)
- Handle common LLM JSON errors (trailing commas, single quotes)
- Fallback: return {"error": "parse_failed", "raw": text}

## Code Quality Rules
- Type hints on every function
- Docstrings on every public function
- No hardcoded API keys (use python-dotenv)
- No print statements (use Python logging module)
- Async functions for all agent nodes
- requirements.txt must be complete and pinned

## Common Pitfalls to Avoid
1. Do NOT use OpenAI client directly — use ChatGroq from langchain_groq
2. Do NOT build a vector database for PDF search — use simple chunking
3. Do NOT make the reflection loop run more than once (1 revision max)
4. Do NOT dump raw tool outputs into prompts — always truncate to 500 tokens
5. Do NOT forget error handling on JSON parsing — LLMs produce invalid JSON often
6. Do NOT use st.cache_data for LLM calls — they should run fresh each time
7. Do NOT store API keys in code — use .env file

## Testing After Build
Run these commands to verify:
```bash
# Check imports work
python -c "from src.agent.graph import run_agent; print('Graph OK')"

# Run the app
streamlit run app.py

# Test a simple query
# In the UI, enter: "What is quantum computing?"
# Verify: report has sections, citations, and agent logs show all 5 nodes ran
```
