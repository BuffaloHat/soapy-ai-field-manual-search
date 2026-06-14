"""app.py — gated, keyword-search-only showcase for the Soapy AI Field Manual.

Coverage first (matching chapters/sections), then a few capped, highlighted excerpts.
No LLM, no browse, no pagination. Search lives in indexer.py; this file is UI + gate.

Run: uv run streamlit run app.py
"""
from __future__ import annotations

import html
import os
from collections import OrderedDict

import streamlit as st

import indexer

st.set_page_config(page_title="Soapy AI Field Manual — Search", page_icon="🔎", layout="centered")


@st.cache_resource
def get_index():
    """Parse the snapshot and build the FTS5 index once per process."""
    return indexer.build_index()


def expected_password() -> str | None:
    """Shared password from Streamlit secrets, falling back to an env var for local dev."""
    try:
        if "app_password" in st.secrets:
            return st.secrets["app_password"]
    except Exception:
        pass
    return os.environ.get("SAIFM_PASSWORD")


def gate() -> bool:
    """Single shared password. Nothing below this returns until it passes (PRD M1)."""
    if st.session_state.get("authed"):
        return True

    st.title("Soapy AI Field Manual — Search")
    st.caption(
        "A gated, keyword-search view of a private field manual on building AI/LLM systems. "
        "Search a topic to see **where** the manual covers it, plus a few short excerpts."
    )
    secret = expected_password()
    with st.form("gate"):
        pw = st.text_input("Access password", type="password", key="gate",
                           placeholder="Enter the shared password")
        ok = st.form_submit_button("Enter")
    if ok:
        if secret is None:
            st.error("No password configured. Set `app_password` in secrets or `SAIFM_PASSWORD`.")
        elif pw == secret:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


def render_snippet(snip: str) -> str:
    """Escape HTML, then turn the indexer's match markers into <mark> highlights (S2)."""
    safe = html.escape(snip)
    return safe.replace("\x02", "<mark>").replace("\x03", "</mark>")


def render_coverage(coverage) -> None:
    by_chapter = OrderedDict()
    for r in coverage:
        key = (r["chapter_num"], r["chapter_title"])
        by_chapter.setdefault(key, []).append((r["section_number"], r["section_title"]))

    n_sec = len(coverage)
    n_ch = len(by_chapter)
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


def main() -> None:
    if not gate():
        return

    st.title("Soapy AI Field Manual — Search")
    st.caption("Coverage first, then a taste of the prose. Keyword search only — no AI answers.")

    with st.expander("About this manual"):
        st.markdown(
            "An implementation-first field manual for building AI/LLM systems end-to-end — "
            "18 chapters across foundations, RAG, prompt/context/harness engineering, agents, "
            "evaluation, security, deployment, and fine-tuning. This app proves its coverage "
            "and depth without distributing the manuscript."
        )

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


main()
