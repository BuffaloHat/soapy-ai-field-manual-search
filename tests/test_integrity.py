"""Indexing-integrity checks (eval_plan.md §5): the parse still matches the
format contract after a corpus refresh.
"""

def test_chapter_coverage(paragraphs):
    """I1 — all 18 chapters present (front matter is excluded, so no chapter 0)."""
    chapters = sorted({p.chapter_num for p in paragraphs})
    assert chapters == list(range(1, 19))


def test_section_labels(paragraphs):
    """I2 — sample section labels parse (Ch 13 Evaluation has 13.3/13.4/13.5)."""
    ch13 = {p.section_number for p in paragraphs if p.chapter_num == 13 and p.section_number}
    assert {"13.3", "13.4", "13.5"} <= ch13


def test_cleaning_no_residue(paragraphs):
    """I3 — no HTML wrapper, image/link, emphasis, or backtick residue survives."""
    bad = [
        p for p in paragraphs
        if "<div" in p.text or "![" in p.text or "](" in p.text
        or "**" in p.text or "`" in p.text
    ]
    assert not bad, [p.text[:60] for p in bad[:3]]


def test_no_empty_rows(paragraphs):
    """I4 — no indexed paragraph is empty or whitespace-only."""
    assert all(p.text.strip() for p in paragraphs)
