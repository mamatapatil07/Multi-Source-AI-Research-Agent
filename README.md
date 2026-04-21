# 🔬 ResearchFlow — Multi-Source Research Agent

An autonomous AI research agent that searches the web, reads PDFs, queries Wikipedia, and synthesizes structured reports with citations — powered by a self-reflection loop that critiques and improves its own output.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Orchestration-green)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)

---

## 🎯 What This Demonstrates

| GenAI Pattern | Implementation |
|--------------|----------------|
| **Agent Orchestration** | LangGraph StateGraph with 5 nodes, conditional edges, and typed state |
| **Tool Use** | 3 external tools (Tavily web search, Wikipedia, PDF reader) with structured I/O |
| **Reflection** | Self-critique loop that evaluates 5 quality dimensions and triggers revision |
| **Structured Output** | Pydantic models for every data structure; JSON-mode prompts with fallback parsing |
| **Cost Optimization** | Dual-model routing — Llama 3.3 70B for reasoning, Llama 3.1 8B for summarization |

---

## 🏗️ Architecture

```
                    ┌─────────┐
                    │  START   │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  Planner  │  Llama 3.3 70B
                    │           │  Breaks query into 3-5 sub-questions
                    └────┬─────┘
                         │
                    ┌────▼──────┐
                    │ Researcher │  Llama 3.1 8B (summarizer)
                    │            │  Calls: Tavily, Wikipedia, PDF Reader
                    └────┬──────┘
                         │
                    ┌────▼───────┐
                    │ Synthesizer │  Llama 3.3 70B
                    │             │  Drafts cited report
                    └────┬───────┘
                         │
                    ┌────▼─────┐
                    │  Critic   │  Llama 3.3 70B
                    │           │  Reviews: completeness, citations,
                    │           │  diversity, balance, accuracy
                    └────┬─────┘
                         │
                    ┌────▼────────┐     needs_revision    ┌─────────┐
                    │ Should       │ ───────────────────── │ Reviser │──── END
                    │ Revise?      │                       │ 70B     │
                    └─────┬───────┘                       └─────────┘
                          │ good
                          ▼
                         END
```

### Why This Architecture?

- **Planner → Researcher separation**: The planner uses the strong model (70B) to decide *what* to search. The researcher uses the small model (8B) to summarize results. This cuts token costs ~60% vs using 70B for everything.
- **Critic checks 5 specific dimensions**: Not a vague "improve this" — the critic evaluates completeness, citation coverage, source diversity, balance, and accuracy. This specificity produces actionable feedback.
- **Max 1 revision**: More revisions hit diminishing returns and burn API quota. One targeted revision based on specific critique is enough.
- **Rate limiter between every LLM call**: 2.5s delay keeps us safely under Groq's 30 RPM free tier limit.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Free Groq API key ([console.groq.com](https://console.groq.com))
- Free Tavily API key ([tavily.com](https://tavily.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/research-agent.git
cd research-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and TAVILY_API_KEY

# Run the application
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 📁 Project Structure

```
research-agent/
├── project-docs/              # Architecture documentation
│   ├── PRD.md                 # Product requirements
│   ├── AgentGraph.md          # LangGraph node/edge specification
│   ├── Tools.md               # Tool input/output contracts
│   ├── Prompts.md             # All LLM prompt templates
│   ├── Evals.md               # 20 test queries + scoring rubric
│   └── TechStack.md           # Stack decisions + setup
├── src/
│   ├── agent/
│   │   ├── graph.py           # LangGraph StateGraph assembly
│   │   ├── state.py           # AgentState + Pydantic models
│   │   ├── llm.py             # Groq client configuration
│   │   ├── nodes/
│   │   │   ├── planner.py     # Query → research plan
│   │   │   ├── researcher.py  # Plan → source results
│   │   │   ├── synthesizer.py # Sources → cited report
│   │   │   ├── critic.py      # Report → quality critique
│   │   │   └── reviser.py     # Critique → improved report
│   │   └── prompts/
│   │       └── templates.py   # All prompt templates
│   ├── tools/
│   │   ├── web_search.py      # Tavily API wrapper
│   │   ├── wiki_search.py     # Wikipedia wrapper
│   │   └── pdf_reader.py      # PDF text extraction + search
│   └── utils/
│       ├── rate_limiter.py    # Groq free tier rate limiter
│       └── output_parser.py   # JSON parsing with fallback
├── app.py                     # Streamlit UI
├── eval_runner.py             # Evaluation script
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🧪 Evaluation

The project includes 20 test queries across 6 categories with automated scoring:

| Dimension | Method | Target |
|-----------|--------|--------|
| Citation Coverage | Automated (cited claims / total claims) | ≥ 80% |
| Source Diversity | Automated (unique source types) | ≥ 2 types |
| Reflection Impact | Automated (pre vs post revision diff) | Measurable improvement |
| Structural Quality | LLM-as-judge | ≥ 3.5 / 5 |
| Factual Grounding | LLM-as-judge | ≥ 4.0 / 5 |

Run evaluations:
```bash
python eval_runner.py
```

---

## 💡 Design Decisions

### Why Groq?
Free tier with no credit card. Llama 3.3 70B on Groq runs at ~300+ tokens/second — fast enough that the reflection loop (which doubles LLM calls) still completes in under 60 seconds.

### Why not a vector database for PDFs?
For an MVP with ≤3 PDFs and ≤50 pages each, simple keyword chunking + LLM relevance scoring is sufficient. A vector DB adds infrastructure complexity without meaningful quality improvement at this scale.

### Why structured JSON output instead of free-form text?
Every LLM response is parsed into Pydantic models. This makes the agent's output programmatically accessible, enables automated evaluation, and demonstrates production-grade output handling.

### Why limit to 1 revision?
Testing showed that the first revision captures ~90% of quality improvement. Additional revisions consume 7+ more LLM calls for diminishing returns — critical when operating within Groq's free tier limits.

---

## 🛠️ Tech Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| Agent Framework | LangGraph | Free |
| LLM (reasoning) | Llama 3.3 70B via Groq | Free tier |
| LLM (summarization) | Llama 3.1 8B via Groq | Free tier |
| Web Search | Tavily API | Free (1,000/month) |
| Wikipedia | wikipedia Python library | Free |
| PDF Processing | PyPDF2 | Free |
| UI | Streamlit | Free |
| Deployment | Streamlit Cloud / Render | Free tier |

**Total cost: $0**

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
