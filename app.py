"""
ResearchFlow — Streamlit UI
Multi-source research agent with real-time agent thought process display.
"""

import streamlit as st
import asyncio
import time
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    if "TAVILY_API_KEY" in st.secrets:
        os.environ["TAVILY_API_KEY"] = st.secrets["TAVILY_API_KEY"]
except FileNotFoundError:
    pass

from src.agent.graph import run_agent_sync
from src.agent.state import format_report
from src.tools.pdf_reader import extract_text_from_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page Config
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
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp { font-family: 'DM Sans', sans-serif; }

    /* Hero */
    .hero-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.5px;
        margin-bottom: 0.1rem;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: #94a3b8;
        letter-spacing: 0.3px;
    }

    /* Gradient divider */
    .gdiv {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99,102,241,0.35), transparent);
        border: none;
        margin: 1.5rem 0;
    }

    /* Agent log */
    .log-entry {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        line-height: 1.65;
        padding: 0.45rem 0.75rem;
        margin: 0.2rem 0;
        border-radius: 6px;
        background: rgba(99,102,241,0.07);
        border-left: 3px solid #6366f1;
    }

    /* Stat cards */
    .stat-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.06));
        border: 1px solid rgba(99,102,241,0.18);
        border-radius: 12px;
        padding: 1rem 0.5rem;
        text-align: center;
    }
    .stat-num {
        font-size: 1.8rem;
        font-weight: 700;
        color: #818cf8;
        line-height: 1.2;
    }
    .stat-lbl {
        font-size: 0.72rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-top: 0.2rem;
    }

    /* Citation */
    .cit-ref {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        padding: 0.4rem 0.7rem;
        margin: 0.2rem 0;
        border-radius: 6px;
        background: rgba(99,102,241,0.05);
        border-left: 3px solid #6366f1;
        line-height: 1.6;
    }
    .cit-ref a { color: #818cf8 !important; text-decoration: none; }
    .cit-ref a:hover { text-decoration: underline; }

    /* Quality badges */
    .q-good {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        background: rgba(52,211,153,0.12);
        color: #34d399;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid rgba(52,211,153,0.25);
    }
    .q-rev {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        background: rgba(251,191,36,0.12);
        color: #fbbf24;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid rgba(251,191,36,0.25);
    }

    /* Pipeline badges */
    .pipe { display:inline-flex; align-items:center; gap:0.3rem; padding:0.3rem 0.65rem; border-radius:8px; font-size:0.78rem; font-weight:500; margin:0.12rem; }
    .p1 { background:rgba(96,165,250,0.12); color:#60a5fa; border:1px solid rgba(96,165,250,0.25); }
    .p2 { background:rgba(52,211,153,0.12); color:#34d399; border:1px solid rgba(52,211,153,0.25); }
    .p3 { background:rgba(251,191,36,0.12); color:#fbbf24; border:1px solid rgba(251,191,36,0.25); }
    .p4 { background:rgba(244,114,182,0.12); color:#f472b6; border:1px solid rgba(244,114,182,0.25); }
    .p5 { background:rgba(167,139,250,0.12); color:#a78bfa; border:1px solid rgba(167,139,250,0.25); }

    .report-body { line-height: 1.8; font-size: 1rem; }

    /* Hide branding */
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 📎 Upload PDFs")
    st.caption("Reference documents the agent can search through.")

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)} PDF(s) ready")
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")

    st.markdown("---")
    st.markdown("### 🧬 Pipeline")
    st.markdown(
        '<span class="pipe p1">🔍 Plan</span>'
        '<span class="pipe p2">📡 Research</span>'
        '<span class="pipe p3">✍️ Synthesize</span>'
        '<span class="pipe p4">🔎 Critique</span>'
        '<span class="pipe p5">🔧 Revise</span>',
        unsafe_allow_html=True,
    )
    st.caption("")
    st.caption("Each step is visible in Agent Thought Process after a run.")

    st.markdown("---")
    st.markdown("### 🛠️ Tech Stack")
    st.markdown(
        "**Agent** — LangGraph StateGraph  \n"
        "**LLM** — Llama 3.3 70B *(reasoning)*  \n"
        "**Fast LLM** — Llama 3.1 8B *(summaries)*  \n"
        "**Inference** — Groq API  \n"
        "**Search** — Tavily API  \n"
        "**Knowledge** — Wikipedia  \n"
        "**PDF** — PyPDF2  \n"
        "**Validation** — Pydantic v2  \n"
    )

    st.markdown("---")
    st.caption("Total infrastructure cost: **$0**")

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.markdown("""
<div class="hero-title">🔬 ResearchFlow</div>
<div class="hero-sub">Multi-source AI research agent with self-reflection</div>
""", unsafe_allow_html=True)

st.markdown('<div class="gdiv"></div>', unsafe_allow_html=True)

# Query
query = st.text_input(
    "Enter your research topic or question",
    placeholder="e.g., What are the latest developments in nuclear fusion energy?",
    key="query_input",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_button = st.button("🚀 Research", type="primary", use_container_width=True)
with col2:
    st.caption("30–60s · 7–10 LLM calls · 3+ sources · Free tier APIs")

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if run_button and query.strip():

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

    st.markdown('<div class="gdiv"></div>', unsafe_allow_html=True)

    with st.status("🔬 Researching...", expanded=True) as status:
        start_time = time.time()
        try:
            final_state = run_agent_sync(
                query=query.strip(),
                pdf_texts=pdf_texts if pdf_texts else None,
                pdf_filenames=pdf_filenames if pdf_filenames else None,
            )
            elapsed = time.time() - start_time
            status.update(label=f"✅ Done in {elapsed:.1f}s", state="complete", expanded=False)
        except Exception as exc:
            status.update(label="❌ Failed", state="error")
            st.error(f"Agent error: {str(exc)}")
            st.stop()

    # --- Stats ---
    report_sections = final_state.get("report_sections", [])
    citations = final_state.get("citations", [])
    source_count = len(final_state.get("source_results", []))
    revision_count = final_state.get("revision_count", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, num, lbl in [
        (c1, source_count, "Sources"),
        (c2, len(report_sections), "Sections"),
        (c3, len(citations), "Citations"),
        (c4, revision_count, "Revisions"),
        (c5, f"{elapsed:.0f}s", "Time"),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-card"><div class="stat-num">{num}</div>'
                f'<div class="stat-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # --- Agent Thought Process ---
    with st.expander("🧠 Agent Thought Process", expanded=False):
        agent_logs = final_state.get("agent_logs", [])
        if agent_logs:
            for log in agent_logs:
                st.markdown(f'<div class="log-entry">{log}</div>', unsafe_allow_html=True)
        else:
            st.info("No agent logs recorded.")

    # --- Report ---
    st.markdown('<div class="gdiv"></div>', unsafe_allow_html=True)
    st.markdown("## 📄 Research Report")

    if not report_sections:
        st.warning("No report sections generated. Try a different query.")
    else:
        for section in report_sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            st.markdown(f"### {heading}")
            st.markdown(f'<div class="report-body">{content}</div>', unsafe_allow_html=True)
            st.markdown("")

    # --- References ---
    if citations:
        st.markdown('<div class="gdiv"></div>', unsafe_allow_html=True)
        st.markdown("### 📚 References")
        emojis = {"web": "🌐", "wikipedia": "📖", "pdf": "📄"}
        for cit in citations:
            cid = cit.get("id", "?")
            title = cit.get("source_title", "Unknown")
            url = cit.get("source_url", "")
            stype = cit.get("source_type", "")
            date = cit.get("accessed_date", "")
            e = emojis.get(stype, "📎")
            if url and url.startswith("http"):
                st.markdown(
                    f'<div class="cit-ref"><b>[{cid}]</b> {e} '
                    f'<a href="{url}" target="_blank">{title}</a> '
                    f'<span style="color:#64748b">— {stype} — {date}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="cit-ref"><b>[{cid}]</b> {e} {title} '
                    f'<span style="color:#64748b">— {stype} — {url}</span></div>',
                    unsafe_allow_html=True,
                )

    # --- Critique ---
    critique = final_state.get("critique", {})
    if critique:
        st.markdown('<div class="gdiv"></div>', unsafe_allow_html=True)
        with st.expander("🔎 Quality Critique", expanded=False):
            quality = critique.get("overall_quality", "unknown")
            if quality == "good":
                st.markdown('<span class="q-good">✅ Quality: Good</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="q-rev">📝 Revised Based on Critique</span>', unsafe_allow_html=True)
            st.markdown("")

            gaps = critique.get("gaps", [])
            suggestions = critique.get("suggestions", [])
            unsupported = critique.get("unsupported_claims", [])

            if gaps:
                st.markdown("**Gaps Identified**")
                for g in gaps:
                    st.markdown(f"- {g}")
            if suggestions:
                st.markdown("**Suggestions**")
                for s in suggestions:
                    st.markdown(f"- {s}")
            if unsupported:
                st.markdown("**Unsupported Claims**")
                for u in unsupported:
                    st.markdown(f"- {u}")
            if not gaps and not suggestions and not unsupported:
                st.caption("No issues found — report passed all quality checks.")

    # --- Download ---
    st.markdown('<div class="gdiv"></div>', unsafe_allow_html=True)

    report_md = format_report(report_sections, citations)
    dl1, dl2 = st.columns([1, 3])
    with dl1:
        st.download_button(
            "📥 Download Report",
            data=report_md,
            file_name="research_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl2:
        st.caption(f"{len(report_sections)} sections · {len(citations)} citations · {elapsed:.1f}s")

elif run_button and not query.strip():
    st.warning("Please enter a research topic or question.")
