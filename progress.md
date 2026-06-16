# Progress — saifm

Working board. Three sections only: **Next steps**, **Backlog**, **Completed** (newest → oldest). Requirements and open questions live in [docs/prd.md](docs/prd.md), not here.

---

## Next steps

1. **Deploy (the keystone)** — resolve OQ5/OQ6 (host + how the private corpus *and* `manual_preview.pdf` reach it), deploy gated, then swap the live URL into the README.
2. **Tests** — promote the `indexer.py` self-checks + the `app.py` AppTest smoke checks into a `pytest` suite ([docs/eval_plan.md](docs/eval_plan.md) §6 Phase 2).

## Backlog

- Deploy gated (resolve OQ5 deploy target + OQ6 private-corpus delivery first — see PRD §9).
- Optional polish: "About this manual" panel (May2), rate limiting (May1), usage logging (May3).
- Expand the golden query set to ~20–30 entries.

## Completed

### 2026-06-15
- Added screenshots to the README: hero gated-landing shot + a Screenshots gallery (Search, Coverage, Excerpts, Manual Preview, About) in `scripts/images/`; refreshed the Status section. (A capped-excerpt screenshot intentionally shows a tame prose taste — consistent with the gated 25-page sample.)
- UI formatting pass: bold/enlarged search intro + "Search the manual:" label; coverage/excerpts notes restyled as red-accent chips; bold per-excerpt section labels.
- Added a **Manual Preview** tab (gated): downloadable 25-page Chapter 1 sample + the Parts/Chapters contents (folded in from the removed Chapters tab). Tabs now Search · Manual Preview · About. PDF lives gitignored in `data/manual_preview.pdf` — never committed. PRD §7 notes this intentional gated-sample exception. (Tried an inline PDF viewer — Chrome blocks data-URI PDFs, and image rendering felt off against the app's brevity — so settled on download + contents; `pymupdf` added then removed.)

### 2026-06-14
- Excerpt-quality pass (all tested, golden probe stayed 9/9): stripped inline markdown (`**`/`*`/backticks/bullets); switched excerpts to a centered ~700-char window with before/after context (PRD M5 cap updated 300→700); merged sub-threshold paragraphs (<80 chars) to kill one-line fragments; excluded "Tools and Field Cards" sections (table-heavy). Index now ~2,077 prose rows.
- UI to house style: mascot + title header (shown on the gate too), wide layout, and three tabs — Search / Chapters / About. Gate switched to an `on_click` callback (cleaner than `st.rerun()`).
- Housekeeping: moved code into `scripts/` (`app.py`, `indexer.py`); added [docs/z_scripts_inventory.md](docs/z_scripts_inventory.md); set default port 8503 via `.streamlit/config.toml`; fixed the indexer's corpus path for the new location.
- Built `app.py`: Streamlit password gate (shared password via `st.secrets`/env) + two-layer search UI — coverage grouped by chapter, then capped highlighted excerpts. Verified end-to-end with Streamlit `AppTest` (gate, `MCP`→12.7 coverage, `<mark>` highlights, no-results + low-signal states). Added `.streamlit/secrets.toml.example`; real secrets gitignored. `indexer.build_index` now uses `check_same_thread=False` for the cached connection.
- Set up uv environment: `pyproject.toml`, `.python-version` (3.12), `uv.lock`, `.venv/` (gitignored). `requirements.txt` kept as the deploy mirror. Re-ran indexer self-checks in the venv — all pass on 3.12.
- Built `indexer.py` + `requirements.txt`: parses the snapshot (Source markers → chapters, `## N.M` → sections), strips HTML/image/code-fence noise, loads 3,124 paragraph rows into in-memory FTS5. Self-checks pass: all 18 chapters, clean bodies, and all 9 golden queries return the expected section as the #1 result. Excerpt caps (≤5, ≤300 chars) verified.

### 2026-06-13
- Drafted `README.md` (first pass): pitch, manual contents, architecture, content/access model; dummy live link + screenshot placeholder.
- Scaffolded the repo: `git init`, root `.gitignore`, wired private remote `BuffaloHat/soapy-ai-field-manual-search`, first commit + push. Verified corpus + `z_archive/` are ignored and absent from the remote.
- Organized docs into `docs/`; moved `z_archive/` to repo root; archived `spec.md` + the root `manuscript_review.md` copy there.
- Drafted all planning docs: `overview`, `prd`, `data_inventory`, `eval_plan`, `CLAUDE.md`, this board.
- Added the guarded mirror block to the manual repo's `build_manuscript.py`; ran it; verified `data/soapy_ai_manual.md` landed byte-for-byte identical to source (SHA `defad405…`).
- Locked the architecture: standalone public portfolio repo; corpus is the one secret (gitignored); code shown publicly; corpus = `build_manuscript.py` snapshot, push-on-build delivery; manual owns selection, saifm owns search; `CLAUDE.md` as agent-context file.
- Oriented from `spec.md` (now archived) + the manuscript.
