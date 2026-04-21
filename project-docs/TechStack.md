# Tech Stack & Setup

## Stack Overview

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent Framework | LangGraph | Industry-standard for stateful agent orchestration |
| LLM Provider | Groq API (free tier) | Fast inference, free, OpenAI-compatible |
| Primary Model | Llama 3.3 70B | Strong reasoning for planning, synthesis, critique |
| Secondary Model | Llama 3.1 8B | Cost-effective for summarization tasks |
| Web Search | Tavily API (free tier) | Built for AI agents, 1,000 free searches/month |
| Wikipedia | LangChain WikipediaQueryRun | Free, no API key, reliable |
| PDF Processing | PyPDF2 | Lightweight, no external dependencies |
| Output Validation | Pydantic v2 | Structured output parsing and validation |
| UI | Streamlit | Fast prototyping, built-in streaming support |
| Python | 3.11+ | Required for LangGraph |

## Environment Variables

```bash
# .env file
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
```

## Getting API Keys

### Groq (Free)
1. Go to https://console.groq.com
2. Sign up with email (no credit card)
3. Go to API Keys → Create new key
4. Free tier: 30 RPM, 6,000 TPM, 14,400 RPD

### Tavily (Free)
1. Go to https://tavily.com
2. Sign up for free plan
3. Go to Dashboard → API Key
4. Free tier: 1,000 searches/month

## Dependencies

```txt
# requirements.txt
langgraph>=0.2.0
langchain>=0.3.0
langchain-groq>=0.2.0
langchain-community>=0.3.0
tavily-python>=0.4.0
wikipedia>=1.4.0
PyPDF2>=3.0.0
pydantic>=2.0.0
streamlit>=1.38.0
python-dotenv>=1.0.0
```

## Project Structure

```
research-agent/
├── project-docs/           # Documentation (this folder)
│   ├── PRD.md
│   ├── AgentGraph.md
│   ├── Tools.md
│   ├── Prompts.md
│   ├── Evals.md
│   └── TechStack.md
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py         # LangGraph state graph definition
│   │   ├── state.py         # AgentState and Pydantic models
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── planner.py   # Planner node
│   │   │   ├── researcher.py # Researcher node
│   │   │   ├── synthesizer.py # Synthesizer node
│   │   │   ├── critic.py     # Critic node
│   │   │   └── reviser.py    # Reviser node
│   │   └── prompts/
│   │       ├── __init__.py
│   │       └── templates.py  # All prompt templates
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_search.py    # Tavily wrapper
│   │   ├── wiki_search.py   # Wikipedia wrapper
│   │   └── pdf_reader.py    # PDF extraction tool
│   └── utils/
│       ├── __init__.py
│       ├── rate_limiter.py  # Sleep-based rate limiter for Groq
│       └── output_parser.py # JSON parsing with fallback
├── app.py                   # Streamlit UI
├── eval_runner.py           # Evaluation script
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/username/research-agent.git
cd research-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and TAVILY_API_KEY

# 5. Run the app
streamlit run app.py
```

## Rate Limit Handling

```python
# src/utils/rate_limiter.py
import asyncio
import time

class GroqRateLimiter:
    """Simple rate limiter for Groq free tier (30 RPM, 6000 TPM)."""
    
    def __init__(self, min_delay: float = 2.0):
        self.min_delay = min_delay
        self.last_call = 0
    
    async def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self.last_call = time.time()
```

## Git Ignore

```
# .gitignore
.env
__pycache__/
*.pyc
venv/
.streamlit/
uploaded_pdfs/
```
