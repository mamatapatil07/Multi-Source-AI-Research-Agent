"""
ResearchFlow — Streamlit UI
Multi-source research agent with real-time agent thought process display.
"""

import streamlit as st
import asyncio
import time
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.agent.graph import run_agent_sync
from src.agent.state import format_report
from src.tools.pdf_reader import extract_text_from_pdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ResearchFlow",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Main title styling */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }

    /* Agent log styling */
    .agent-log {
        background-color: #f8f9fa;
        border-left: 3px solid #4a90d9;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        border-radius: 0 4px 4px 0;
        font-size: 0.9rem;
    }

    /* Report section styling */
    .report-section {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    /* Citation styling */
    .citation-block {
        background-color: #f1f3f5;
        border-radius: 6px;
        padding: 1rem;
        margin-top: 1rem;
        font-size: 0.85rem;
    }

    /* Sidebar info */
    .sidebar-info {
        background-color: #e8f4f8;
        border-radius: 6px;
        padding: 0.8rem;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — PDF Upload & Info
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 📎 Upload PDFs (Optional)")
    st.caption("Upload reference documents for the agent to include in research.")

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)} PDF(s) uploaded")
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")

    st.markdown("---")
    st.markdown("### ℹ️ How It Works")
    st.markdown("""
    <div class="sidebar-info">
    <strong>ResearchFlow</strong> is an AI research agent that:
    <br><br>
    1. <strong>Plans</strong> — Breaks your topic into sub-questions<br>
    2. <strong>Researches</strong> — Searches web, Wikipedia & PDFs<br>
    3. <strong>Synthesizes</strong> — Drafts a cited report<br>
    4. <strong>Critiques</strong> — Self-reviews for gaps<br>
    5. <strong>Revises</strong> — Improves based on critique
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🛠️ Tech Stack")
    st.caption("LangGraph · Groq (Llama 3.3 70B) · Tavily · Streamlit")

# ---------------------------------------------------------------------------
# Main Content
# ---------------------------------------------------------------------------

st.markdown('<div class="main-title">🔬 ResearchFlow</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">AI-powered multi-source research agent with self-reflection</div>',
    unsafe_allow_html=True,
)

# Query input
query = st.text_input(
    "Enter your research topic or question",
    placeholder="e.g., What are the latest developments in nuclear fusion energy?",
    key="query_input",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_button = st.button("🚀 Research", type="primary", use_container_width=True)
with col2:
    st.caption("Typical research takes 30-60 seconds")

# ---------------------------------------------------------------------------
# Run Agent
# ---------------------------------------------------------------------------

if run_button and query.strip():

    # Extract PDF texts if uploaded
    pdf_texts: list[str] = []
    pdf_filenames: list[str] = []

    if uploaded_files:
        for f in uploaded_files:
            text = extract_text_from_pdf(f.read(), f.name)
            if text:
                pdf_texts.append(text)
                pdf_filenames.append(f.name)
            else:
                st.warning(f"Could not extract text from {f.name}")

    # Agent progress display
    st.markdown("---")

    with st.status("🔬 Researching...", expanded=True) as status:

        progress_placeholder = st.empty()
        start_time = time.time()

        try:
            # Run the agent
            final_state = run_agent_sync(
                query=query.strip(),
                pdf_texts=pdf_texts if pdf_texts else None,
                pdf_filenames=pdf_filenames if pdf_filenames else None,
            )

            elapsed = time.time() - start_time
            status.update(
                label=f"✅ Research complete ({elapsed:.1f}s)",
                state="complete",
                expanded=False,
            )

        except Exception as exc:
            status.update(label="❌ Research failed", state="error")
            st.error(f"Agent error: {str(exc)}")
            st.stop()

    # ---------------------------------------------------------------------------
    # Display Agent Thought Process
    # ---------------------------------------------------------------------------

    with st.expander("🧠 Agent Thought Process", expanded=False):
        agent_logs = final_state.get("agent_logs", [])
        for log_entry in agent_logs:
            st.markdown(f'<div class="agent-log">{log_entry}</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Display Report
    # ---------------------------------------------------------------------------

    st.markdown("---")
    st.markdown("## 📄 Research Report")

    report_sections = final_state.get("report_sections", [])
    citations = final_state.get("citations", [])

    for section in report_sections:
        heading = section.get("heading", "")
        content = section.get("content", "")
        st.markdown(f"### {heading}")
        st.markdown(content)

    # Display Citations
    if citations:
        st.markdown("---")
        st.markdown("### 📚 References")
        for cit in citations:
            cid = cit.get("id", "?")
            title = cit.get("source_title", "Unknown")
            url = cit.get("source_url", "")
            stype = cit.get("source_type", "")
            date = cit.get("accessed_date", "")

            if url and url.startswith("http"):
                st.markdown(
                    f"**[{cid}]** [{title}]({url}) — *{stype}* — accessed {date}"
                )
            else:
                st.markdown(
                    f"**[{cid}]** {title} — *{stype}* — {url}"
                )

    # ---------------------------------------------------------------------------
    # Display Critique Summary
    # ---------------------------------------------------------------------------

    critique = final_state.get("critique", {})
    if critique:
        with st.expander("🔎 Quality Critique", expanded=False):
            quality = critique.get("overall_quality", "unknown")
            if quality == "good":
                st.success("Report quality: ✅ Good")
            else:
                st.warning("Report quality: 📝 Revised based on critique")

            gaps = critique.get("gaps", [])
            if gaps:
                st.markdown("**Gaps identified:**")
                for gap in gaps:
                    st.markdown(f"- {gap}")

            suggestions = critique.get("suggestions", [])
            if suggestions:
                st.markdown("**Suggestions applied:**")
                for sug in suggestions:
                    st.markdown(f"- {sug}")

    # ---------------------------------------------------------------------------
    # Download Report
    # ---------------------------------------------------------------------------

    st.markdown("---")
    report_md = format_report(report_sections, citations)
    st.download_button(
        label="📥 Download Report (Markdown)",
        data=report_md,
        file_name="research_report.md",
        mime="text/markdown",
    )

    # Stats
    revision_count = final_state.get("revision_count", 0)
    source_count = len(final_state.get("source_results", []))
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Sources", source_count)
    col_b.metric("Sections", len(report_sections))
    col_c.metric("Citations", len(citations))
    col_d.metric("Revisions", revision_count)

elif run_button and not query.strip():
    st.warning("Please enter a research topic or question.")
