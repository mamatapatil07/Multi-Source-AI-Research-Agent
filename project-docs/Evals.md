# Evaluation Criteria & Test Queries

## Overview
A portfolio project without evals is a toy. This file defines 20 test queries
with expected behaviors, plus automated evaluation criteria.
Run these after every major change to catch regressions.

---

## Automated Eval Dimensions

Each test run is scored on 5 dimensions (1-5 scale):

### 1. Citation Coverage (automated)
- Count factual claims in the report
- Count claims with inline citations [n]
- Score = (cited claims / total claims) × 5
- **Target**: ≥ 4.0 (80%+ claims cited)

### 2. Source Diversity (automated)
- Count unique source types used (web, wikipedia, pdf)
- Score: 1 type = 2, 2 types = 4, 3 types = 5
- **Target**: ≥ 4.0 (at least 2 source types)

### 3. Reflection Impact (automated)
- Compare word count and citation count: pre-critique vs post-revision
- Score: No change = 1, Minor additions = 3, Meaningful improvement = 5
- **Target**: ≥ 3.0

### 4. Structural Quality (LLM-as-judge)
- Send final report to LLM with rubric: "Rate 1-5 on organization,
  clarity, and logical flow"
- **Target**: ≥ 3.5

### 5. Factual Grounding (LLM-as-judge)
- Send report + source materials to LLM: "Rate 1-5 on whether claims
  in the report are supported by the provided sources"
- **Target**: ≥ 4.0

---

## Test Queries

### Category: Current Events (should use web_search heavily)

**Test 1**
- Query: "What are the latest developments in nuclear fusion energy?"
- Expected tools: web_search (primary), wikipedia_search (background)
- Expected sections: Recent breakthroughs, key players/companies, timeline to commercialization
- Pass criteria: Report mentions events from the last 6 months

**Test 2**
- Query: "How is the AI regulation landscape changing globally?"
- Expected tools: web_search (primary), wikipedia_search (background on existing laws)
- Expected sections: US regulation, EU AI Act, other countries, industry response
- Pass criteria: Mentions specific legislation or proposals

**Test 3**
- Query: "What happened with the latest SpaceX Starship launch?"
- Expected tools: web_search (primary)
- Expected sections: Launch details, outcomes, implications
- Pass criteria: Contains specific dates and technical details

### Category: Conceptual/Educational (should use wikipedia heavily)

**Test 4**
- Query: "Explain quantum computing and its potential applications"
- Expected tools: wikipedia_search (primary), web_search (recent developments)
- Expected sections: How it works, current state, applications, challenges
- Pass criteria: Explains qubits, superposition clearly

**Test 5**
- Query: "What is CRISPR and how is it being used in medicine?"
- Expected tools: wikipedia_search (CRISPR background), web_search (recent trials)
- Expected sections: Technology explanation, medical applications, ethics
- Pass criteria: Mentions specific clinical trials or treatments

**Test 6**
- Query: "History and impact of the Internet on society"
- Expected tools: wikipedia_search (primary)
- Expected sections: Origins, key milestones, social impact, economic impact
- Pass criteria: Mentions ARPANET, Tim Berners-Lee

### Category: Comparison/Analysis (needs multiple tools)

**Test 7**
- Query: "Compare React, Vue, and Angular for web development in 2025"
- Expected tools: web_search (current ecosystem), wikipedia_search (background)
- Expected sections: Performance, ecosystem, learning curve, job market
- Pass criteria: Contains current market share data or recent benchmarks

**Test 8**
- Query: "Electric vehicles vs hydrogen fuel cells for transportation"
- Expected tools: web_search + wikipedia_search
- Expected sections: Technology comparison, infrastructure, cost, environmental impact
- Pass criteria: Presents both sides fairly with citations

**Test 9**
- Query: "Python vs Rust for systems programming"
- Expected tools: web_search + wikipedia_search
- Expected sections: Performance, safety, ecosystem, use cases
- Pass criteria: Acknowledges tradeoffs rather than declaring a winner

### Category: People/Biography (Wikipedia + current news)

**Test 10**
- Query: "Who is Jensen Huang and what is NVIDIA's role in AI?"
- Expected tools: wikipedia_search (biography), web_search (recent news)
- Expected sections: Background, NVIDIA's AI strategy, recent developments
- Pass criteria: Covers both historical background and recent news

**Test 11**
- Query: "Contributions of Geoffrey Hinton to artificial intelligence"
- Expected tools: wikipedia_search (primary), web_search (recent statements)
- Expected sections: Academic career, key breakthroughs, recent AI safety views
- Pass criteria: Mentions backpropagation, deep learning, Nobel Prize

### Category: Science/Technical (needs depth)

**Test 12**
- Query: "How do large language models work?"
- Expected tools: wikipedia_search (transformer architecture), web_search (recent advances)
- Expected sections: Architecture, training, capabilities, limitations
- Pass criteria: Mentions transformers, attention mechanism, training data

**Test 13**
- Query: "Current state of cancer immunotherapy research"
- Expected tools: web_search (recent trials), wikipedia_search (immunotherapy basics)
- Expected sections: Types of immunotherapy, recent breakthroughs, challenges
- Pass criteria: Mentions CAR-T cells or checkpoint inhibitors

### Category: Edge Cases (test robustness)

**Test 14**
- Query: "asdkjfhaskjdf"
- Expected behavior: Agent acknowledges query is unclear, asks for clarification
  or provides best-effort interpretation
- Pass criteria: Does NOT hallucinate a report on gibberish

**Test 15**
- Query: "Tell me everything about everything"
- Expected behavior: Agent narrows scope, picks a reasonable interpretation
- Pass criteria: Produces a focused report, not a rambling dump

**Test 16**
- Query: "What is the meaning of life?"
- Expected behavior: Treats as philosophical question, covers major perspectives
- Pass criteria: Cites philosophical or scientific sources, not just opinion

**Test 17**
- Query: "" (empty string)
- Expected behavior: Returns error message asking for a topic
- Pass criteria: Does not crash

### Category: PDF-Dependent (requires uploaded PDF)

**Test 18**
- Query: "Summarize the key findings from the uploaded paper"
- PDF: Any research paper PDF
- Expected tools: pdf_reader (primary), web_search (for context)
- Pass criteria: Summary matches actual PDF content

**Test 19**
- Query: "How do the findings in my PDF compare to current research?"
- PDF: Any research paper PDF
- Expected tools: pdf_reader + web_search
- Pass criteria: Draws specific comparisons between PDF and web sources

**Test 20**
- Query: "What are the limitations mentioned in this document?"
- PDF: Any research paper PDF
- Expected tools: pdf_reader (primary)
- Pass criteria: Extracts actual limitations from the PDF, not generic ones

---

## Running Evals

```python
# eval_runner.py (simplified)
import json
from agent import run_research_agent

TEST_QUERIES = json.load(open("project-docs/test_queries.json"))

def run_eval():
    results = []
    for test in TEST_QUERIES:
        output = run_research_agent(test["query"])
        score = {
            "query": test["query"],
            "citation_coverage": calc_citation_score(output),
            "source_diversity": calc_diversity_score(output),
            "reflection_impact": calc_reflection_score(output),
            "structural_quality": llm_judge_structure(output),
            "factual_grounding": llm_judge_grounding(output),
        }
        results.append(score)
    
    avg_scores = aggregate(results)
    print(f"Overall Score: {avg_scores['mean']:.2f} / 5.0")
    return results
```

## Eval Schedule
- Run full eval suite after every agent graph change
- Run citation + diversity evals after every prompt change
- Log results to a CSV for tracking improvement over time
- Include eval results in the project README (recruiters love this)
