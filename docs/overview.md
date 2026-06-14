# Overview — saifm (Soapy AI Field Manual Showcase)

**Created:** 2026-06-13
**Status:** Active — planning docs stage (no app code yet)
**Author:** Matt Kennedy
**Working name:** `saifm` (short for *Soapy AI Field Manual*). Renameable.

> Companion docs: [prd.md](prd.md) (requirements), [data_inventory.md](data_inventory.md) (corpus + refresh), [eval_plan.md](eval_plan.md) (how we judge it), [progress.md](../progress.md) (execution log), [CLAUDE.md](../CLAUDE.md) (agent context).

---

## 1. System intent

A password-gated, **keyword-search-only** web app that lets a deliberately-shared contact (recruiter, hiring manager, peer) ask whether the Soapy AI Field Manual covers a topic — and see proof — *without* distributing the manual itself.

Every search returns two layers, **coverage first**:

1. **Coverage layer** — which chapters/sections address the topic, by number and title (the manual's table-of-contents depth). This is the primary showcase value.
2. **Tidbit layer** — a few short, capped, term-highlighted excerpts from those sections.

The headline is the manual's *structure*; the prose is only a taste.

---

## 2. Boundaries

**In scope**
- Single shared password gating all content.
- Exact keyword search (SQLite FTS5 / BM25) over one corpus.
- Coverage layer + capped excerpts.
- Server-side corpus; only gate results and capped snippets reach the browser.

**Out of scope (explicit non-goals)**
- **Not an AI/LLM app.** No model, no embeddings, no generated answers or summaries. Keyword search only.
- **Not a distribution channel.** No browse-all, no pagination, no "show full section," no export.
- **Not public-access.** Gated; the link is shared deliberately.
- **Not a general search engine.** One corpus, one password.

---

## 3. Locked decisions (architecture)

| Decision | Choice |
| --- | --- |
| **Repo placement** | Standalone **public** portfolio repo. Separate from the private manual repo. |
| **What's shown publicly** | README + the build/search code (`app.py`, `indexer.py`, schema). The engineering is part of the portfolio story. |
| **The one secret** | The manual *prose* and the built search index. Gitignored; never committed to the public repo. See [data_inventory.md](data_inventory.md). |
| **Corpus source** | The prebuilt `manuscript_review.md` snapshot from the manual repo's `build/` dir. The app never reads live chapters or runs selection logic itself. |
| **Division of labor** | Manual repo owns *content selection/exclusion* (`build_manuscript.py`). saifm owns *search cleaning, indexing, and display* (`indexer.py`). Dependency is one-directional: saifm depends on the manual, never the reverse. |
| **Refresh workflow** | edit manual → run `build_manuscript.py` (which mirrors a copy into `saifm/data/`) → restart app (index rebuilds) → redeploy. Delivery is push-on-build; no separate saifm-side copy step. |
| **Stack** | Streamlit UI · SQLite FTS5 search · in-memory index built at startup (`@st.cache_resource`). No external services. |
| **Agent context file** | `CLAUDE.md` (this project uses Claude Code), serving the role of Ch. 3's `AGENTS.md`. |

---

## 4. Repo topology

```
saifm/  (public)
├── README.md            ← the portfolio headline: what this is + link to live UI
├── progress.md          ← execution log + next steps            (committed)
├── CLAUDE.md            ← agent project context                 (committed)
├── app.py               ← Streamlit gate + search UI            (committed)
├── indexer.py           ← parse snapshot → FTS5 index           (committed)
├── requirements.txt     ← deps                                  (committed)
├── docs/                ← overview · prd · data_inventory · eval_plan   (committed)
├── z_archive/           ← retired docs/artifacts                 (GITIGNORED)
└── data/                ← soapy_ai_manual.md + built index       (GITIGNORED — the secret)
                            mirrored in by the manual's build_manuscript.py
```

**The protection model in one line:** the code is public; the corpus is private; anything rendered to a browser is capped (≤~300 chars/excerpt, ≤~5 excerpts/query, no browse). A determined scraper is explicitly out of scope — see [prd.md](prd.md) §Content-Protection.

---

## 5. Definition of done (v1)

- Gate blocks all content behind one password.
- A topic query returns the correct coverage layer (right chapters/sections) plus capped, highlighted excerpts.
- No path exposes whole chapters or the raw corpus to the client.
- Deployed at a shareable gated URL; README links to it.
- Refreshing the corpus after a manual edit is a two-command local step.
