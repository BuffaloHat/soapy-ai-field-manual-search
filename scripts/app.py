"""
Soapy AI Field Manual — Search
==============================
A gated, keyword-search-only showcase for a private AI/LLM field manual.

Coverage first (matching chapters/sections), then a few capped, highlighted
excerpts. No LLM, no browse, no pagination. Search lives in indexer.py; this
file is the gate + UI shell.

Run:
  uv run streamlit run scripts/app.py     # port 8503 via .streamlit/config.toml

Change Log
----------
2026-06-14 — House-style header + Manual Contents
  Adopted the shared Streamlit app conventions: mascot + title header (shown on
  the gate too), wide layout, injected style block, and a "Manual Contents"
  expander (Parts → Chapters, no sections) near the top.

2026-06-14 — Initial gated search app
  Password gate + two-layer result (coverage grouped by chapter, then capped,
  <mark>-highlighted excerpts). Verified end-to-end with Streamlit AppTest.
"""
from __future__ import annotations

import html
import os
import sys
from collections import OrderedDict
from pathlib import Path

import streamlit as st

# Make the sibling module importable regardless of launcher (streamlit run / AppTest / pytest).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import indexer  # noqa: E402

IMAGE_PATH = Path(__file__).parent / "images" / "soapy_manual.jpeg"

DESCRIPTION = (
    "A gated, keyword-search view of a private field manual on building AI/LLM "
    "systems. Search a topic to see which chapters and sections cover it, plus a "
    "few short excerpts. Keyword search only — no AI answers."
)

# Parts → (chapter number, chapter title). Sections are intentionally omitted here.
PARTS = [
    ("Part 0 — Foundations", [
        (1, "AI, LLMs, and Transformers"),
    ]),
    ("Part I — Project Baseline", [
        (2, "Development Environment"),
        (3, "Planning Docs"),
        (4, "AI Deployment Decisions"),
    ]),
    ("Part II — RAG: Knowledge Intake + Retrieval", [
        (5, "Data Ingestion and Document Handling"),
        (6, "RAG Alternatives: Simpler Knowledge Patterns"),
        (7, "RAG Implementation"),
    ]),
    ("Part III — Controlling the Model", [
        (8, "Prompt Engineering"),
        (9, "Context Engineering"),
        (10, "Harness Engineering"),
    ]),
    ("Part IV — Agents", [
        (11, "Agent Memory"),
        (12, "Agents, Workflows, and Architectures"),
    ]),
    ("Part V — Production Discipline", [
        (13, "Evaluation, Testing, and Observability"),
        (14, "Security, Safety, and Governance"),
        (15, "Deployment and Operations"),
    ]),
    ("Part VI — Adapting the Model", [
        (16, "Fine-Tuning"),
    ]),
    ("Part VII — Appendices", [
        (17, "Glossary"),
        (18, "Planning Docs Examples"),
    ]),
]

STYLES = """
<style>
/* Excerpt highlight */
mark { background: #ffe39c; padding: 0 2px; border-radius: 2px; }
/* Muted description line */
.app-desc { font-size: 1.05rem; color: #555; margin-top: .25rem; }
/* Manual Contents */
.contents-part { font-weight: 700; margin: .25rem 0 .15rem 0; }
.contents-chap { color: #444; }
</style>
"""


@st.cache_resource
def get_index():
    """Parse the snapshot and build the FTS5 index once per process."""
    return indexer.build_index()


def expected_password():
    """Shared password from Streamlit secrets, falling back to an env var for local dev."""
    try:
        if "app_password" in st.secrets:
            return st.secrets["app_password"]
    except Exception:
        pass
    return os.environ.get("SAIFM_PASSWORD")


def authed() -> bool:
    return bool(st.session_state.get("authed"))


# --------------------------------------------------------------------------- #
# Shell pieces
# --------------------------------------------------------------------------- #
def render_header() -> None:
    col_img, col_title = st.columns([1, 4])
    with col_img:
        if IMAGE_PATH.exists():
            st.image(str(IMAGE_PATH), width=180)
    with col_title:
        st.markdown(
            "<h1 style='font-size: 2.8rem; margin-bottom: 0;'>Soapy AI Field Manual</h1>",
            unsafe_allow_html=True,
        )
        st.markdown("<p class='app-desc'>%s</p>" % DESCRIPTION, unsafe_allow_html=True)


def render_contents() -> None:
    with st.expander("Manual Contents — Parts & Chapters", expanded=True):
        cols = st.columns(2)
        half = (len(PARTS) + 1) // 2
        for idx, (part_label, chapters) in enumerate(PARTS):
            target = cols[0] if idx < half else cols[1]
            chap_md = "<br>".join(
                "<span class='contents-chap'><b>%d</b>&nbsp; %s</span>" % (n, html.escape(t))
                for n, t in chapters
            )
            target.markdown(
                "<div class='contents-part'>%s</div>%s<div style='margin-bottom:.6rem'></div>"
                % (html.escape(part_label), chap_md),
                unsafe_allow_html=True,
            )


def _attempt_login() -> None:
    """Form-submit callback: validate before the rerun so the gate cleanly disappears."""
    secret = expected_password()
    if secret is None:
        st.session_state.gate_msg = "No password configured. Set `app_password` in secrets or `SAIFM_PASSWORD`."
    elif st.session_state.get("gate") == secret:
        st.session_state.authed = True
        st.session_state.gate_msg = None
    else:
        st.session_state.gate_msg = "Incorrect password."


def render_gate() -> None:
    st.divider()
    st.caption("This showcase is password-gated. Enter the shared password to search.")
    with st.form("gate_form"):
        st.text_input("Access password", type="password", key="gate",
                      placeholder="Enter the shared password")
        st.form_submit_button("Enter", on_click=_attempt_login)
    if st.session_state.get("gate_msg"):
        st.error(st.session_state.gate_msg)


def render_snippet(snip: str) -> str:
    """Escape HTML, then turn the indexer's match markers into <mark> highlights (S2)."""
    safe = html.escape(snip)
    return safe.replace("\x02", "<mark>").replace("\x03", "</mark>")


def render_coverage(coverage) -> None:
    by_chapter = OrderedDict()
    for r in coverage:
        by_chapter.setdefault((r["chapter_num"], r["chapter_title"]), []).append(
            (r["section_number"], r["section_title"])
        )
    n_sec, n_ch = len(coverage), len(by_chapter)
    st.markdown("### Coverage")
    st.caption("Found in %d section%s across %d chapter%s."
               % (n_sec, "" if n_sec == 1 else "s", n_ch, "" if n_ch == 1 else "s"))
    for (cnum, ctitle), secs in by_chapter.items():
        sec_line = " · ".join("**%s** %s" % (num, title) for num, title in secs)
        st.markdown("**Ch %d — %s**  \n%s" % (cnum, ctitle, sec_line))


def render_excerpts(excerpts) -> None:
    st.markdown("### Excerpts")
    st.caption("A few short, capped tidbits — not full sections.")
    for ch, sec, title, snip in excerpts:
        label = "Ch %d → %s %s" % (ch, sec, title) if sec else "Ch %d" % ch
        st.markdown("<small><em>%s</em></small>" % html.escape(label), unsafe_allow_html=True)
        st.markdown(
            "<div style='margin:0 0 1rem 0;padding:.5rem .75rem;border-left:3px solid #ccc;"
            "background:rgba(127,127,127,.08)'>%s</div>" % render_snippet(snip),
            unsafe_allow_html=True,
        )


def render_search() -> None:
    con = get_index()
    with st.form("search"):
        query = st.text_input("Search the manual", key="search",
                              placeholder="e.g. MCP, agent evaluation, reranking, prompt caching")
        submitted = st.form_submit_button("Search")

    if not submitted or not query.strip():
        return

    result = indexer.search(con, query)
    if result is None:
        st.warning("Please enter a more specific search term.")
        return
    coverage, excerpts = result
    if not coverage and not excerpts:
        st.info("No matches for **%s**. Try another topic — e.g. *evaluation*, *agents*, or *RAG*."
                % html.escape(query))
        return
    render_coverage(coverage)
    st.divider()
    render_excerpts(excerpts)


# --------------------------------------------------------------------------- #
# App shell
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Soapy AI Field Manual — Search", page_icon="🔎", layout="wide")
    st.markdown(STYLES, unsafe_allow_html=True)
    render_header()

    if not authed():
        render_gate()
        return

    render_contents()
    render_search()


if __name__ == "__main__":
    main()
