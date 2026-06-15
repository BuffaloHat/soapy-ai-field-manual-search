# Scripts Inventory — saifm

What each script in `scripts/` does. Both run inside the uv venv (`uv run …`) on Python 3.12.

| Script | Role |
| --- | --- |
| [`scripts/indexer.py`](../scripts/indexer.py) | Corpus → search index (the engine). |
| [`scripts/app.py`](../scripts/app.py) | Gated Streamlit UI (the front end). |

---

## `scripts/indexer.py` — parse + index + search

The search engine. No Streamlit, no UI — pure parsing and SQLite. `app.py` imports from it.

- **Parses** the corpus snapshot `data/soapy_ai_manual.md` into `(chapter, section_number, section_title, paragraph)` rows: splits chapters on `<!-- Source: -->` markers, sections on `## N.M` headings, and strips search-side noise (HTML divs, image/attachment links, fenced code blocks). See the format contract in [data_inventory.md](data_inventory.md) §2.
- **Builds** an in-memory SQLite **FTS5** index (BM25 ranking, `snippet()` highlighting), shared across Streamlit sessions via `check_same_thread=False`.
- **Searches**: `search(con, query)` returns `(coverage, excerpts)` — the matching sections (coverage layer) and a few capped, marker-wrapped excerpts — or `None` for a low-signal query (empty/stopword-only). Enforces the caps: ≤5 excerpts, ≤300 chars each.
- **Self-checks**: run `uv run python scripts/indexer.py` to validate against [eval_plan.md](eval_plan.md) — chapter/section integrity, cleaning, the golden coverage probe, and low-signal rejection. Exits non-zero on any failure.

Key knobs (top of file): `MAX_EXCERPTS`, `MAX_EXCERPT_CHARS`, `MAX_COVERAGE_SECTIONS`.

## `scripts/app.py` — gated search UI

The Streamlit front end. Thin: gate + presentation over `indexer.search`.

- **Gate** (PRD M1): single shared password from `st.secrets["app_password"]` (or `SAIFM_PASSWORD` env for local dev). Nothing below the gate renders until it passes.
- **Search UI**: a query box → **Coverage** (matching sections grouped by chapter) then **Excerpts** (capped tidbits with the matched term highlighted via `<mark>`). Handles the no-results and low-signal states cleanly.
- **Index**: built once per process with `@st.cache_resource`.
- **Run:** `uv run streamlit run scripts/app.py` (defaults to port 8503 via `.streamlit/config.toml`).
