"""Content-protection checks (eval_plan.md §3). Any failure is release-blocking.

These guard the model: capped prose out, and the Topic Cloud stays prose-free.
"""
import indexer

# A spread of real queries that return excerpts.
QUERIES = ["RAG evaluation", "agent", "prompt", "context window", "security", "chunking"]


def _strip(snip: str) -> str:
    """Excerpt text without highlight markers or boundary ellipses."""
    return snip.replace(indexer.HL_OPEN, "").replace(indexer.HL_CLOSE, "").strip("…")


def test_excerpt_char_cap(con):
    """P1 — no excerpt exceeds the char cap (markers/ellipses excluded)."""
    for q in QUERIES:
        result = indexer.search(con, q)
        assert result is not None
        for *_, snip in result[1]:
            assert len(_strip(snip)) <= indexer.MAX_EXCERPT_CHARS, q


def test_excerpt_and_coverage_count_caps(con):
    """P2 — excerpt count and coverage breadth stay within their caps."""
    for q in QUERIES:
        result = indexer.search(con, q)
        assert result is not None
        coverage, excerpts = result
        assert len(excerpts) <= indexer.MAX_EXCERPTS, q
        assert len(coverage) <= indexer.MAX_COVERAGE_SECTIONS, q


def test_one_excerpt_per_section(con):
    """P3 (partial) — excerpts never stack multiple snippets from one section."""
    for q in QUERIES:
        result = indexer.search(con, q)
        assert result is not None
        keys = [(ch, sec) for ch, sec, *_ in result[1]]
        assert len(keys) == len(set(keys)), q
