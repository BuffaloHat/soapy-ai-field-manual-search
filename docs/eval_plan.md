# Eval Plan — saifm

**Created:** 2026-06-13
**Companion:** [prd.md](prd.md) · [overview.md](overview.md) · [data_inventory.md](data_inventory.md)

This app has **no LLM**, so "evaluation" is not model scoring — it's **deterministic correctness, protection, and product-polish checks**. The bar: every query returns the right *coverage*, the prose stays *capped*, and a "no results" or rejected query still reads as a finished product.

---

## 1. What success means

| # | Success criterion | Maps to |
| --- | --- | --- |
| G1 | The gate blocks all content until the correct password is entered. | M1 |
| G2 | A topic query returns the **correct chapters/sections** in the coverage layer. | M4 |
| G3 | Excerpts are always capped (chars + count) and never expose a whole section. | M5, M6 |
| G4 | Ranking surfaces the most relevant sections first. | S1 |
| G5 | Low-signal and no-result queries fail gracefully and look intentional. | S3, S4 |

---

## 2. Golden query set (the core eval)

A small, hand-curated set of queries with **expected coverage** — the sections we *know* address each topic, from the TOC. This is the regression suite: after any indexer/cleaning change, coverage for these must not degrade.

| Query | Expected to appear in coverage (≥) | Notes |
| --- | --- | --- |
| `MCP` | 12.7 (MCP) | Should rank 12.7 first. |
| `LLM-as-judge` | 13.5 | Exact-ish phrase. |
| `RAG evaluation` | 13.3, (7.x retrieval) | 13.3 should lead. |
| `agent evaluation` | 13.4 | Distinguish from 13.3/13.5. |
| `prompt caching` | 6.3 (CAG), 8.x | Tests a term that spans chapters. |
| `chunking` | 5.4 | Single clear home. |
| `reranking` | 7.4 | Single clear home. |
| `fine-tuning` | 16.x | Whole-chapter topic. |
| `guardrails` | 14.3 | Security chapter. |
| `memory retrieval` | 11.4 | Distinguish from 11.x siblings. |

*(Expand to ~20–30 once the indexer exists; keep it in a checked-in fixture so it's runnable.)*

**Pass condition:** for each query, every "expected" section appears in the returned coverage layer, and the lead section is correct where noted. **Recall on expected sections is the headline metric** — a missing expected section is a real bug (the showcase under-sells coverage).

---

## 3. Protection checks (must always pass)

These guard the content-protection model (PRD §7). Treat any failure as release-blocking.

- **P1 — Char cap.** No returned excerpt exceeds the configured max (~700 chars, excluding highlight markers). Assert on raw response, not just rendered text.
- **P2 — Count cap.** No query returns more than the configured max excerpts (~5).
- **P3 — No whole-section leak.** Concatenating all excerpts for one query never reconstructs a full section; there is no parameter (page, offset, "show more") that returns additional prose.
- **P4 — Server-side only.** The client response contains only the gate result, coverage labels, and capped excerpts — never the raw corpus or a section body. Inspect the actual payload.
- **P5 — Gate cannot be bypassed.** No search endpoint/action returns content before the password check passes in `session_state`.
- **P6 — Topic Cloud is prose-free.** The Topic Cloud output contains only vocabulary tokens and their sizes (aggregate section counts) — never paragraph text or excerpts. It is a structural surface, not a prose one.

---

## 4. Query-hygiene checks

- **Q1 — Low-signal rejection (S3).** Empty, whitespace, stopword-only (`the`, `and`), and single-character queries are rejected with a clear message — they must **not** return "everything."
- **Q2 — No-results state (S4).** A plausible-but-absent topic (e.g. `kubernetes operators`) returns a clean, finished-looking "no results" — not an error, not a blank page.
- **Q3 — Casing / punctuation.** `MCP`, `mcp`, and `M.C.P` behave sensibly (case-insensitive; punctuation tolerant).

---

## 5. Indexing-integrity checks (offline, against the snapshot)

Run after each corpus refresh to confirm the parse still matches the format contract ([data_inventory.md](data_inventory.md) §2):

- **I1 — Chapter count.** Indexer finds all expected chapters (Part 0 + 18 chapters) from the `<!-- Source -->` markers.
- **I2 — Section labels.** Section numbers/titles parsed from headings match the TOC (spot-check a sample, e.g. 13.1–13.8).
- **I3 — Cleaning.** No HTML wrapper divs, image links, or attachment refs survive into indexed text.
- **I4 — Non-empty rows.** No indexed paragraph is empty or structural-only.
- **I5 — Topic Cloud vocabulary.** `cloud.SPRINKLE` keys are a subset of `cloud.CANONICAL_TAGS` (enforced by an `assert` at import), and `cloud.topic_frequencies` returns a non-empty mapping for the current corpus.

---

## 6. How we run it

These checks are now a **`pytest` suite** in `tests/` — run it with:

```
uv run pytest          # fast (~0.6s), no network, no model
```

The suite mirrors the sections above, against the local corpus snapshot:

| File | Covers |
| --- | --- |
| `tests/test_golden.py` | §2 golden set (G2), parametrized over the query set |
| `tests/test_protection.py` | §3 caps — P1 (char), P2 (count/coverage), P3 (one excerpt per section) |
| `tests/test_hygiene.py` | §4 — Q1 low-signal rejection, Q2 no-results, Q3 casing |
| `tests/test_integrity.py` | §5 — I1 chapters, I2 section labels, I3 cleaning, I4 non-empty |
| `tests/test_cloud.py` | Topic Cloud — I5 (`SPRINKLE ⊆ CANONICAL_TAGS` + non-empty), P6 prose-free |

Session-scoped fixtures in `conftest.py` parse the corpus and build the index once, and **skip** cleanly if the snapshot isn't present (fresh clone / CI without `data/`). `pytest` is a uv dev-dependency (`[dependency-groups] dev`), not in the deploy mirror. The gate checks (P4/P5) and a final visual click-through of the result states stay a manual step.

**Definition of "good enough to share":** G1–G5 hold, all P-checks pass, the golden set has full expected-section recall, and the no-results/rejected states look intentional.

---

## 7. Out of scope (deliberately)

- No relevance *quality* scoring beyond the golden set's lead-section checks — BM25 default ordering is accepted unless the golden set exposes a clear miss.
- No A/B testing, no analytics-driven tuning (May3 logging is optional and informational only).
- No semantic/embedding evaluation — there is no semantic search to evaluate.
