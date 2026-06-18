"""Golden query set (eval_plan.md §2 / G2).

Recall on expected sections is the headline metric: for each known query, the
expected chapter/section must appear in the coverage layer. A miss means the
showcase under-sells real coverage — a regression to block.
"""
import pytest

import indexer


def _hit(expected: str, secs) -> bool:
    """Mirror the indexer self-check's match rule: exact, sub-section, or chapter-level."""
    return any(
        s == expected
        or s.startswith(expected + ".")
        or (("." not in expected) and s.split(".")[0] == expected)
        for s in secs
    )


@pytest.mark.parametrize("query,expected", list(indexer.GOLDEN.items()))
def test_golden_coverage(con, query, expected):
    result = indexer.search(con, query)
    assert result is not None, f"{query!r} was wrongly rejected as low-signal"
    secs = [r["section_number"] for r in result[0]]
    assert _hit(expected, secs), f"{query!r}: expected {expected}, coverage was {secs[:5]}"
