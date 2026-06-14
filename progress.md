# Progress — saifm

Working board. Three sections only: **Next steps**, **Backlog**, **Completed** (newest → oldest). Requirements and open questions live in [docs/prd.md](docs/prd.md), not here.

---

## Next steps

1. **`README.md`** — the portfolio headline (what this is + link to the live UI).
2. **Scaffold the repo** — `git init`; root `.gitignore` (Python + `data/` + `z_archive/`); `requirements.txt`.
3. **`indexer.py`** — parse `data/soapy_ai_manual.md` → SQLite FTS5; verify against the golden set + integrity checks ([docs/eval_plan.md](docs/eval_plan.md) §2, §5).
4. **`app.py`** — password gate + two-layer search UI (coverage first, capped excerpts); run locally.

## Backlog

- Deploy gated (resolve OQ5 deploy target + OQ6 private-corpus delivery first — see PRD §9).
- Optional polish: "About this manual" panel (May2), rate limiting (May1), usage logging (May3).
- Expand the golden query set to ~20–30 entries.

## Completed

### 2026-06-13
- Organized docs into `docs/`; moved `z_archive/` to repo root; archived `spec.md` + the root `manuscript_review.md` copy there.
- Drafted all planning docs: `overview`, `prd`, `data_inventory`, `eval_plan`, `CLAUDE.md`, this board.
- Added the guarded mirror block to the manual repo's `build_manuscript.py`; ran it; verified `data/soapy_ai_manual.md` landed byte-for-byte identical to source (SHA `defad405…`).
- Locked the architecture: standalone public portfolio repo; corpus is the one secret (gitignored); code shown publicly; corpus = `build_manuscript.py` snapshot, push-on-build delivery; manual owns selection, saifm owns search; `CLAUDE.md` as agent-context file.
- Oriented from `spec.md` (now archived) + the manuscript.
