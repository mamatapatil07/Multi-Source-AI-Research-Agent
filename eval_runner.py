"""
ResearchFlow Evaluation Runner
Runs test queries and scores the agent on 5 dimensions.
"""

import asyncio
import json
import re
import time
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from src.agent.graph import run_agent
from src.agent.llm import get_llm, MODEL_SMALL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test Queries
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    {
        "id": 1,
        "query": "What are the latest developments in nuclear fusion energy?",
        "category": "current_events",
        "expected_tools": ["web_search", "wikipedia_search"],
    },
    {
        "id": 2,
        "query": "Explain quantum computing and its potential applications",
        "category": "conceptual",
        "expected_tools": ["wikipedia_search", "web_search"],
    },
    {
        "id": 3,
        "query": "Compare React, Vue, and Angular for web development",
        "category": "comparison",
        "expected_tools": ["web_search", "wikipedia_search"],
    },
    {
        "id": 4,
        "query": "Who is Jensen Huang and what is NVIDIA's role in AI?",
        "category": "biography",
        "expected_tools": ["wikipedia_search", "web_search"],
    },
    {
        "id": 5,
        "query": "How do large language models work?",
        "category": "technical",
        "expected_tools": ["wikipedia_search", "web_search"],
    },
]


# ---------------------------------------------------------------------------
# Scoring Functions
# ---------------------------------------------------------------------------

def score_citation_coverage(state: dict) -> float:
    """
    Score 0-5: What fraction of report sentences contain citations?
    """
    sections = state.get("report_sections", [])
    if not sections:
        return 0.0

    total_sentences = 0
    cited_sentences = 0

    for sec in sections:
        content = sec.get("content", "")
        # Split into sentences (rough)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        total_sentences += len(sentences)

        for sentence in sentences:
            if re.search(r'\[\d+\]', sentence):
                cited_sentences += 1

    if total_sentences == 0:
        return 0.0

    ratio = cited_sentences / total_sentences
    return min(ratio * 5, 5.0)


def score_source_diversity(state: dict) -> float:
    """
    Score 0-5: How many different source types were used?
    1 type = 2, 2 types = 4, 3 types = 5
    """
    source_results = state.get("source_results", [])
    if not source_results:
        return 0.0

    types = {sr.get("source_type", "") for sr in source_results}
    types.discard("")

    count = len(types)
    if count >= 3:
        return 5.0
    elif count == 2:
        return 4.0
    elif count == 1:
        return 2.0
    return 0.0


def score_reflection_impact(state: dict) -> float:
    """
    Score 0-5: Did the reflection loop produce a revision?
    """
    revision_count = state.get("revision_count", 0)
    critique = state.get("critique", {})

    if not critique:
        return 1.0

    quality = critique.get("overall_quality", "good")

    if quality == "needs_revision" and revision_count > 0:
        return 5.0  # Critique found issues AND revision happened
    elif quality == "good":
        return 3.0  # Critique ran but found no major issues
    else:
        return 1.0


def score_structural_quality(state: dict) -> float:
    """
    Score 0-5: Basic structural checks.
    """
    sections = state.get("report_sections", [])
    citations = state.get("citations", [])

    score = 0.0

    # Has multiple sections?
    if len(sections) >= 2:
        score += 1.5
    elif len(sections) == 1:
        score += 0.5

    # Sections have headings?
    headings_ok = all(sec.get("heading", "") for sec in sections)
    if headings_ok:
        score += 1.0

    # Has citations?
    if len(citations) >= 3:
        score += 1.5
    elif len(citations) >= 1:
        score += 0.75

    # Reasonable content length?
    total_content = sum(len(sec.get("content", "")) for sec in sections)
    if total_content >= 500:
        score += 1.0
    elif total_content >= 200:
        score += 0.5

    return min(score, 5.0)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_single_eval(test: dict) -> dict:
    """Run a single test query and score it."""
    query = test["query"]
    test_id = test["id"]

    logger.info("=" * 60)
    logger.info("Running eval #%d: %s", test_id, query)
    logger.info("=" * 60)

    start = time.time()

    try:
        state = await run_agent(query)
        elapsed = time.time() - start

        scores = {
            "test_id": test_id,
            "query": query,
            "category": test["category"],
            "elapsed_seconds": round(elapsed, 1),
            "citation_coverage": round(score_citation_coverage(state), 2),
            "source_diversity": round(score_source_diversity(state), 2),
            "reflection_impact": round(score_reflection_impact(state), 2),
            "structural_quality": round(score_structural_quality(state), 2),
            "source_count": len(state.get("source_results", [])),
            "section_count": len(state.get("report_sections", [])),
            "citation_count": len(state.get("citations", [])),
            "revision_count": state.get("revision_count", 0),
            "error": None,
        }

        avg = (
            scores["citation_coverage"]
            + scores["source_diversity"]
            + scores["reflection_impact"]
            + scores["structural_quality"]
        ) / 4
        scores["average_score"] = round(avg, 2)

    except Exception as exc:
        elapsed = time.time() - start
        scores = {
            "test_id": test_id,
            "query": query,
            "category": test["category"],
            "elapsed_seconds": round(elapsed, 1),
            "citation_coverage": 0,
            "source_diversity": 0,
            "reflection_impact": 0,
            "structural_quality": 0,
            "source_count": 0,
            "section_count": 0,
            "citation_count": 0,
            "revision_count": 0,
            "average_score": 0,
            "error": str(exc)[:200],
        }

    return scores


async def run_all_evals():
    """Run all test queries and produce a summary report."""
    print("\n" + "=" * 70)
    print("  ResearchFlow Evaluation Suite")
    print("=" * 70 + "\n")

    all_scores: list[dict] = []

    for test in TEST_QUERIES:
        scores = await run_single_eval(test)
        all_scores.append(scores)

        # Print individual result
        if scores["error"]:
            print(f"  ❌ #{scores['test_id']} FAILED: {scores['error'][:80]}")
        else:
            print(
                f"  ✅ #{scores['test_id']} | "
                f"Avg: {scores['average_score']:.1f}/5 | "
                f"Citations: {scores['citation_coverage']:.1f} | "
                f"Diversity: {scores['source_diversity']:.1f} | "
                f"Reflection: {scores['reflection_impact']:.1f} | "
                f"Structure: {scores['structural_quality']:.1f} | "
                f"Time: {scores['elapsed_seconds']}s"
            )

    # Summary
    successful = [s for s in all_scores if s["error"] is None]
    if successful:
        avg_overall = sum(s["average_score"] for s in successful) / len(successful)
        avg_time = sum(s["elapsed_seconds"] for s in successful) / len(successful)

        print("\n" + "-" * 70)
        print(f"  SUMMARY: {len(successful)}/{len(all_scores)} tests passed")
        print(f"  Overall Average Score: {avg_overall:.2f} / 5.0")
        print(f"  Average Time: {avg_time:.1f}s")
        print("-" * 70)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"eval_results_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(all_scores, f, indent=2)
    print(f"\n  Results saved to {output_file}\n")


if __name__ == "__main__":
    asyncio.run(run_all_evals())
