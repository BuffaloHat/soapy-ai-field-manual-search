"""Query-hygiene checks (eval_plan.md §4): low-signal rejection, clean
no-results state, and case-insensitive matching.
"""
import indexer


def test_low_signal_rejected(con):
    """Q1 — empty / whitespace / stopword-only queries return None, not everything."""
    for q in ["", "   ", "the", "a", "and the"]:
        assert indexer.search(con, q) is None, repr(q)


def test_no_results_state(con):
    """Q2 — a plausible-but-absent topic returns an empty (not None, not error) result."""
    result = indexer.search(con, "kubernetes operators zxqwlk")
    assert result is not None
    coverage, excerpts = result
    assert coverage == [] and excerpts == []


def test_casing_insensitive(con):
    """Q3 — MCP / mcp behave the same (both surface 12.7)."""
    for q in ["MCP", "mcp"]:
        result = indexer.search(con, q)
        assert result is not None
        secs = [r["section_number"] for r in result[0]]
        assert "12.7" in secs, q
