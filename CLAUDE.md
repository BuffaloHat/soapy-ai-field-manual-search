# CLAUDE.md — saifm project context

Project context for Claude Code working in this repo. Read this first; the planning docs in `docs/` have the detail.

## What this is

**saifm** (Soapy AI Field Manual showcase) is a password-gated, **keyword-search-only** web app that proves the Soapy AI Field Manual's *coverage and depth* to a recruiter/peer without distributing it. Every search returns **coverage first** (matching chapter/section numbers + titles) then a few **capped excerpts**.

It is **not an AI app** — no LLM, no embeddings, no generated answers. SQLite FTS5 + BM25 keyword search only. Do not add a model to the loop.

## Read these

- [docs/overview.md](docs/overview.md) — intent, boundaries, locked decisions, repo topology.
- [docs/prd.md](docs/prd.md) — requirements (M/S/May), content-protection model, open questions.
- [docs/data_inventory.md](docs/data_inventory.md) — the corpus, the **format contract**, refresh.
- [docs/eval_plan.md](docs/eval_plan.md) — deterministic checks (golden set, protection, integrity).
- [progress.md](progress.md) — the project's working board. **Exactly three sections — Next steps, Backlog, Completed (newest → oldest); never add others.** Open questions live in the PRD, not here.

## Non-negotiables (don't break these)

1. **The corpus is the one secret.** `data/` is gitignored — the manual prose (`data/soapy_ai_manual.md`) and any built index must never be committed. Everything else (code, docs) is public by design.
2. **Server-side only.** Only gate results + capped excerpts reach the browser — never the raw corpus or a whole section. Caps: ~300 chars/excerpt, ~5 excerpts/query, no browse, no pagination, no "show full section" (PRD M5/M6).
3. **Gate before content.** No search path returns anything before the password check passes in `session_state`.

## How the corpus arrives (don't reinvent)

- Source of truth: the **private** manual repo (Obsidian/iCloud). saifm only *consumes* it.
- `build_manuscript.py` (manual repo) does content *selection* (latest `vN`/chapter, excludes outlines/editorials) and **mirrors a copy** into `data/soapy_ai_manual.md` on every build. saifm trusts the snapshot — do not re-implement file discovery here.
- **Format contract** `indexer.py` depends on: `<!-- Source: manual/… -->` markers (chapter split), `#/##/###` headings (coverage labels), `<div class="chapter-break">` separators, blank-line paragraphs. saifm's job is *search-side cleaning* (strip HTML divs, image/attachment links) — not content selection.

## Conventions

- **Docs:** planning docs live in `docs/`; only `README.md`, `progress.md`, `CLAUDE.md` at root.
- **Archive, don't delete:** retired docs/artifacts go in `z_archive/` at the repo root (gitignored).
- **Stack:** Streamlit UI · `scripts/app.py` + `scripts/indexer.py` · stdlib `sqlite3` FTS5 · index built in-memory at startup (`@st.cache_resource`). Keep it ~120–150 lines; resist scope creep. Code lives in `scripts/`; see [docs/z_scripts_inventory.md](docs/z_scripts_inventory.md).
- **Environment:** uv-managed venv, Python 3.12 (`.python-version`). `uv sync` to set up; run with `uv run python scripts/indexer.py` / `uv run streamlit run scripts/app.py --server.port 8503` (local). The committed `config.toml` does **not** pin a port — Streamlit Community Cloud needs its default (8501), so pinning breaks deploy. `pyproject.toml` + `uv.lock` are the source of truth; `requirements.txt` is the deploy mirror.
- **Status:** early build — `indexer.py` done and validated (FTS5, golden set passes); `app.py` next. Repo initialized and pushed to the private remote.
