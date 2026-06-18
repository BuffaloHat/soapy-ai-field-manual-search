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
import urllib.request
from collections import OrderedDict
from pathlib import Path

import streamlit as st

# Make the sibling module importable regardless of launcher (streamlit run / AppTest / pytest).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import indexer  # noqa: E402
import cloud  # noqa: E402

IMAGE_PATH = Path(__file__).parent / "images" / "soapy_manual.jpeg"
# Gitignored sample of the real manuscript (first 25 of 451 pages — Chapter 1 foundations).
PREVIEW_PDF = Path(__file__).resolve().parent.parent / "data" / "manual_preview.pdf"

DESCRIPTION = (
    "A gated, keyword-search view of a private field manual on building AI/LLM "
    "systems. Keyword search only — no AI answers."
)

# Intro shown at the top of the Search tab.
SEARCH_INTRO = (
    "Search a topic to see which chapters and sections cover it, plus a few short excerpts."
)

# Overview, lifted from the manual's front matter (## Overview) for the About tab.
OVERVIEW = (
    "This is a field manual for building AI systems that work in practice. It is written to "
    "support linear learning from LLM foundations through AI application deployment, while "
    "still being useful as a reference when working on a specific project.\n\n"
    "The emphasis is implementation reality: clear mental models, practical decisions, and "
    "procedures that hold up across changing tools. When a specific tool materially changes a "
    "decision, this guide names it. When a concept is more durable than a tool, the concept "
    "takes priority."
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
/* Search tab intro — pronounced */
.search-intro { font-size: 1.3rem; font-weight: 700; color: #1a1a1a; margin: .25rem 0 .85rem 0; }
/* Result sub-headers (coverage/excerpts notes) — accent chip so they stand out */
.result-note {
    display: inline-block;
    font-size: 1.05rem; font-weight: 600; color: #333;
    background: #fff4f4; border-left: 4px solid #ff4b4b; border-radius: 4px;
    padding: .35rem .7rem; margin: .1rem 0 .85rem 0;
}
/* Per-excerpt section label (Ch X → N.M Title) — bold so it stands out above the box */
.excerpt-label { font-size: 1rem; font-weight: 700; font-style: italic; color: #333; margin: 0 0 .15rem 0; }
/* Manual Contents */
.contents-part { font-weight: 700; margin: .25rem 0 .15rem 0; }
.contents-chap { color: #444; }
/* Tabs — house style */
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #e0e0e0; }
.stTabs [data-baseweb="tab"] {
    height: 48px; padding: 0 28px; border-radius: 6px 6px 0 0;
    font-size: 16px; font-weight: 600; color: #555;
    background-color: #f5f5f5; border: 1px solid #e0e0e0; border-bottom: none;
}
.stTabs [aria-selected="true"] {
    background-color: #ff4b4b !important; color: white !important; border-color: #ff4b4b !important;
}
.stTabs [data-baseweb="tab"]:hover { background-color: #ffe5e5; color: #ff4b4b; }
</style>
"""


def _secret(key, default=None):
    """Read a value from Streamlit secrets, falling back to an env var (UPPER), else default."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key.upper(), default)


def expected_password():
    """Shared password from secrets / env (SAIFM_PASSWORD for local dev)."""
    return _secret("app_password", os.environ.get("SAIFM_PASSWORD"))


def _fetch_private_file(path):
    """Raw bytes of a file in the private manual repo via the GitHub Contents API.

    Deploy (Streamlit Cloud) sets `github_token` + `manual_repo` in secrets so the
    gitignored corpus/preview never need to live in this public repo. Returns None
    on any failure (missing config, auth, network) so the app degrades gracefully.
    """
    token, repo = _secret("github_token"), _secret("manual_repo")
    if not (token and repo and path):
        return None
    ref = _secret("manual_branch", "main")
    url = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (repo, path, ref)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer %s" % token,
        "Accept": "application/vnd.github.raw",
        "User-Agent": "saifm-app",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def get_corpus_text():
    """Corpus markdown: local file if present (dev), else fetched from the private repo (deploy)."""
    if indexer.DATA_FILE.exists():
        return indexer.DATA_FILE.read_text(encoding="utf-8")
    data = _fetch_private_file(_secret("corpus_path", "build/manuscript_review.md"))
    return data.decode("utf-8") if data else ""


@st.cache_resource(show_spinner=False)
def get_index():
    """Build the FTS5 index once per process from the corpus (local or fetched)."""
    text = get_corpus_text()
    if not text.strip():
        return None
    return indexer.build_index(indexer.parse_text(text))


@st.cache_data(show_spinner=False)
def get_cloud_html():
    """Build the Topic Cloud markup once per process ('' if corpus unavailable)."""
    text = get_corpus_text()
    if not text.strip():
        return ""
    return cloud.build_html(indexer.parse_text(text))


def authed() -> bool:
    return bool(st.session_state.get("authed"))


# --------------------------------------------------------------------------- #
# Shell pieces
# --------------------------------------------------------------------------- #
def render_header() -> None:
    col_img, col_title = st.columns([1, 4])
    with col_img:
        if IMAGE_PATH.exists():
            st.image(str(IMAGE_PATH), width=280)
    with col_title:
        st.markdown(
            "<h1 style='font-size: 2.8rem; margin-bottom: 0;'>Soapy AI Field Manual</h1>",
            unsafe_allow_html=True,
        )
        st.markdown("<p class='app-desc'>%s</p>" % DESCRIPTION, unsafe_allow_html=True)


def render_contents() -> None:
    st.markdown("#### Manual Contents — Parts & Chapters")
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


def render_about_tab() -> None:
    st.markdown("#### Overview")
    st.markdown(OVERVIEW)


def render_cloud_tab() -> None:
    st.markdown("#### Topic Cloud")
    st.markdown(
        "<p class='app-desc' style='font-weight:700; color:#1a1a1a;'>A jumping-off point for "
        "Search — the concepts this manual covers, sized by how much ground each gets. Spot one "
        "that interests you, then search it.</p>",
        unsafe_allow_html=True,
    )
    markup = get_cloud_html()
    if markup:
        st.markdown(markup, unsafe_allow_html=True)
    else:
        st.info("The topic cloud isn't available in this environment.")


@st.cache_data(show_spinner=False)
def _preview_bytes():
    """Preview PDF: local file if present (dev), else fetched from the private repo (deploy)."""
    if PREVIEW_PDF.exists():
        return PREVIEW_PDF.read_bytes()
    return _fetch_private_file(_secret("preview_path", "build/manual_preview.pdf"))


def render_preview_tab() -> None:
    st.markdown("#### Manual Preview")
    st.markdown(
        "<p class='app-desc' style='font-weight:700; color:#1a1a1a;'>Download the opening "
        "foundations chapter (25 of 451 pages) to read the real writing — a taste of the full "
        "manuscript. The complete chapter map is below.</p>",
        unsafe_allow_html=True,
    )
    data = _preview_bytes()
    if data:
        st.download_button("Download Manual Preview (PDF)", data=data,
                           file_name="Soapy_AI_Field_Manual_Sample_ch1.pdf",
                           mime="application/pdf")
    else:
        st.info("The preview isn't available in this environment.")
    st.divider()
    render_contents()


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
    st.markdown("<p class='result-note'>Found in %d section%s across %d chapter%s.</p>"
                % (n_sec, "" if n_sec == 1 else "s", n_ch, "" if n_ch == 1 else "s"),
                unsafe_allow_html=True)
    for (cnum, ctitle), secs in by_chapter.items():
        sec_line = " · ".join("**%s** %s" % (num, title) for num, title in secs)
        st.markdown("**Ch %d — %s**  \n%s" % (cnum, ctitle, sec_line))


def render_excerpts(excerpts) -> None:
    st.markdown("### Excerpts")
    st.markdown("<p class='result-note'>A few short, capped tidbits — not full sections.</p>",
                unsafe_allow_html=True)
    for ch, sec, title, snip in excerpts:
        label = "Ch %d → %s %s" % (ch, sec, title) if sec else "Ch %d" % ch
        st.markdown("<p class='excerpt-label'>%s</p>" % html.escape(label), unsafe_allow_html=True)
        st.markdown(
            "<div style='margin:0 0 1rem 0;padding:.5rem .75rem;border-left:3px solid #ccc;"
            "background:rgba(127,127,127,.08)'>%s</div>" % render_snippet(snip),
            unsafe_allow_html=True,
        )


def render_search() -> None:
    st.markdown("<p class='search-intro'>%s</p>" % SEARCH_INTRO, unsafe_allow_html=True)
    con = get_index()
    if con is None:
        st.error("The manual corpus couldn't be loaded — check the deploy secrets "
                 "(`github_token`, `manual_repo`).")
        return
    with st.form("search"):
        query = st.text_input("**Search the manual:**", key="search",
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

    tab_search, tab_cloud, tab_preview, tab_about = st.tabs(
        ["Search", "Topic Cloud", "Manual Preview", "About"])
    with tab_search:
        render_search()
    with tab_cloud:
        render_cloud_tab()
    with tab_preview:
        render_preview_tab()
    with tab_about:
        render_about_tab()


if __name__ == "__main__":
    main()
