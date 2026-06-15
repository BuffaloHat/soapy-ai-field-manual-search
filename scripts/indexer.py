"""indexer.py — parse the manual snapshot into an in-memory SQLite FTS5 index.

The corpus (data/soapy_ai_manual.md) is a single markdown file produced upstream by
the manual repo's build_manuscript.py. This module:

  1. splits it into chapters on `<!-- Source: manual/... -->` markers,
  2. within each chapter, finds numbered sections (`## N.M Title`),
  3. cleans search-side noise (HTML divs, image/attachment links, code fences),
  4. loads (chapter, section, paragraph) rows into an FTS5 table for BM25 search.

Run `python indexer.py` to build the index and print self-checks (integrity +
a golden-query coverage probe). No app code here; app.py imports build_index/search.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# scripts/ lives one level below the repo root; the corpus is in <root>/data/.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "soapy_ai_manual.md"

# --- Output caps (PRD M5) ---
MAX_EXCERPTS = 5
MAX_EXCERPT_CHARS = 300
MAX_COVERAGE_SECTIONS = 20

# --- Format-contract patterns (see docs/data_inventory.md §2) ---
SOURCE_RE = re.compile(r"^<!--\s*Source:\s*(.+?)\s*-->")
CHAPTER_DIR_RE = re.compile(r"manual/(\d{2})-")
CHAPTER_TITLE_RE = re.compile(r"^#\s+Chapter\s+(\d+)\s*[—-]\s*(.+)$")
SECTION_RE = re.compile(r"^##\s+(\d+\.\d+)\s+(.+)$")  # ## 1.1 Title
FENCE_RE = re.compile(r"^\s*(```|~~~)")

# --- Search-side cleaning ---
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HEADING_HASH_RE = re.compile(r"^#{1,6}\s*")
BULLET_RE = re.compile(r"^\s*[-*+]\s+")  # leading list marker
EMPHASIS_RE = re.compile(r"\*+")          # ** bold / * italic asterisks (underscores left intact)
BACKTICK_RE = re.compile(r"`+")           # inline code backticks

# Front matter that must not be indexed (would create fake coverage hits).
SKIP_SOURCES = ("00_title_page", "toc")

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "on", "for",
    "with", "as", "at", "by", "be", "this", "that", "are", "was", "from",
}


@dataclass
class Paragraph:
    chapter_num: int
    chapter_title: str
    section_number: str  # "" for chapter-intro prose before the first numbered section
    section_title: str
    text: str


def _clean(line: str) -> str:
    line = IMAGE_RE.sub("", line)
    line = LINK_RE.sub(r"\1", line)
    line = HTML_TAG_RE.sub("", line)
    line = HEADING_HASH_RE.sub("", line)
    line = BULLET_RE.sub("", line)      # drop leading list marker
    line = EMPHASIS_RE.sub("", line)    # strip ** / * emphasis
    line = BACKTICK_RE.sub("", line)    # strip inline-code backticks
    return line.strip()


def parse_corpus(path: Path = DATA_FILE) -> List[Paragraph]:
    raw = path.read_text(encoding="utf-8")

    # Split into (source_path, lines) blocks on Source markers.
    blocks: List[Tuple[str, List[str]]] = []
    cur_src: Optional[str] = None
    cur_lines: List[str] = []
    for line in raw.splitlines():
        m = SOURCE_RE.match(line)
        if m:
            if cur_src is not None:
                blocks.append((cur_src, cur_lines))
            cur_src, cur_lines = m.group(1), []
        else:
            cur_lines.append(line)
    if cur_src is not None:
        blocks.append((cur_src, cur_lines))

    paragraphs: List[Paragraph] = []
    for src, lines in blocks:
        if any(s in src for s in SKIP_SOURCES):
            continue
        dm = CHAPTER_DIR_RE.search(src)
        if not dm or int(dm.group(1)) == 0:
            continue  # 00-meta front matter (intro) — not a chapter
        chapter_num = int(dm.group(1))

        chapter_title = ""
        section_number = ""
        section_title = ""
        buf: List[str] = []
        in_fence = False

        def flush() -> None:
            text = re.sub(r"\s+", " ", " ".join(buf)).strip()
            if text:
                paragraphs.append(
                    Paragraph(chapter_num, chapter_title, section_number, section_title, text)
                )
            buf.clear()

        for line in lines:
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue  # drop fence markers and skip code content from the index
            if in_fence:
                continue

            cm = CHAPTER_TITLE_RE.match(line)
            if cm:
                chapter_title = cm.group(2).strip()
                continue
            sm = SECTION_RE.match(line)
            if sm:
                flush()
                section_number, section_title = sm.group(1), sm.group(2).strip()
                continue
            if line.strip() == "":
                flush()
                continue
            cleaned = _clean(line)
            if cleaned:
                buf.append(cleaned)
        flush()

    return paragraphs


def build_index(paragraphs: Optional[List[Paragraph]] = None) -> sqlite3.Connection:
    if paragraphs is None:
        paragraphs = parse_corpus()
    # check_same_thread=False: the index is read-only and shared across Streamlit's
    # per-session script threads via @st.cache_resource.
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute(
        """CREATE VIRTUAL TABLE sections USING fts5(
            chapter_num UNINDEXED, chapter_title UNINDEXED,
            section_number UNINDEXED, section_title, body,
            tokenize='porter unicode61'
        )"""
    )
    con.executemany(
        "INSERT INTO sections(chapter_num, chapter_title, section_number, section_title, body)"
        " VALUES (?, ?, ?, ?, ?)",
        [(p.chapter_num, p.chapter_title, p.section_number, p.section_title, p.text) for p in paragraphs],
    )
    con.commit()
    return con


def build_match_query(query: str) -> Optional[str]:
    """Turn raw user input into a safe FTS5 MATCH string, or None if low-signal (S3)."""
    tokens = re.findall(r"[A-Za-z0-9]+", query.lower())
    meaningful = [t for t in tokens if len(t) > 1 and t not in STOPWORDS]
    if not meaningful:
        return None
    return " ".join('"%s"' % t for t in meaningful)  # AND-joined, each token quoted


def search(con: sqlite3.Connection, query: str,
           max_excerpts: int = MAX_EXCERPTS,
           max_sections: int = MAX_COVERAGE_SECTIONS):
    """Return (coverage, excerpts) or None for a rejected low-signal query.

    coverage: list of rows (chapter_num, chapter_title, section_number, section_title)
    excerpts: list of (chapter_num, section_number, section_title, snippet_text)
    """
    match = build_match_query(query)
    if match is None:
        return None

    rows = con.execute(
        "SELECT chapter_num, chapter_title, section_number, section_title, "
        "snippet(sections, 4, '\x02', '\x03', '…', 16) AS snip "
        "FROM sections WHERE sections MATCH ? ORDER BY rank",
        (match,),
    ).fetchall()

    coverage = []
    excerpts = []
    seen_cov = set()
    seen_exc = set()
    for r in rows:
        sec = r["section_number"]
        if sec:
            key = (r["chapter_num"], sec)
            if key not in seen_cov and len(coverage) < max_sections:
                seen_cov.add(key)
                coverage.append(r)
        # one excerpt per section, capped
        ekey = (r["chapter_num"], sec)
        if ekey not in seen_exc and len(excerpts) < max_excerpts:
            snip = re.sub(r"\s+", " ", r["snip"]).strip()
            if len(snip) > MAX_EXCERPT_CHARS:
                snip = snip[:MAX_EXCERPT_CHARS].rstrip() + "…"
            seen_exc.add(ekey)
            excerpts.append((r["chapter_num"], sec, r["section_title"], snip))

    return coverage, excerpts


# --------------------------------------------------------------------------- #
# Self-checks: run `python indexer.py` to validate against eval_plan.md.
# --------------------------------------------------------------------------- #
GOLDEN = {
    "MCP": "12.7",
    "LLM-as-judge": "13.5",
    "RAG evaluation": "13.3",
    "agent evaluation": "13.4",
    "chunking": "5.4",
    "reranking": "7.4",
    "guardrails": "14.3",
    "memory retrieval": "11.4",
    "fine-tuning": "16",  # chapter-level; expect some 16.x section
}


def _selfcheck() -> int:
    if not DATA_FILE.exists():
        print("FAIL: corpus missing at %s" % DATA_FILE)
        return 1

    paras = parse_corpus()
    con = build_index(paras)
    failures = 0

    # I1 — chapter coverage
    chapters = sorted({p.chapter_num for p in paras})
    print("I1 chapters parsed: %s" % chapters)
    if chapters != list(range(1, 19)):
        print("  WARN: expected chapters 1..18")

    # I2 — section labels for a sample chapter (13)
    ch13 = sorted({p.section_number for p in paras if p.chapter_num == 13 and p.section_number})
    print("I2 chapter 13 sections: %s" % ch13)

    # I3 — cleaning: no HTML/image/link residue in any body
    bad = [p for p in paras if "<div" in p.text or "![" in p.text or "](" in p.text
           or "**" in p.text or "`" in p.text]
    print("I3 cleaning residue rows: %d %s" % (len(bad), "OK" if not bad else "FAIL"))
    failures += 1 if bad else 0

    # I4 — no empty bodies
    empties = [p for p in paras if not p.text.strip()]
    print("I4 empty rows: %d %s" % (len(empties), "OK" if not empties else "FAIL"))
    failures += 1 if empties else 0

    print("\nrows indexed: %d\n" % len(paras))

    # Golden coverage probe
    print("GOLDEN coverage probe:")
    for q, expected in GOLDEN.items():
        result = search(con, q)
        if result is None:
            print("  %-18s REJECTED (low-signal) — FAIL" % q)
            failures += 1
            continue
        coverage, _ = result
        secs = [r["section_number"] for r in coverage]
        hit = any(s == expected or s.startswith(expected + ".") or
                  (("." not in expected) and s.split(".")[0] == expected) for s in secs)
        lead = secs[0] if secs else "—"
        print("  %-18s expect %-6s lead %-6s top5 %s  %s"
              % (q, expected, lead, secs[:5], "OK" if hit else "MISS"))
        failures += 0 if hit else 1

    # S3 — low-signal rejection
    print("\nS3 low-signal rejection:")
    for q in ["", "the", "a", "and the"]:
        rejected = search(con, q) is None
        print("  %-8r rejected=%s %s" % (q, rejected, "OK" if rejected else "FAIL"))
        failures += 0 if rejected else 1

    print("\n%s (%d issue(s))" % ("ALL CHECKS PASSED" if failures == 0 else "CHECKS HAD ISSUES", failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_selfcheck())
