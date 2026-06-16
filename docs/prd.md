# PRD — saifm (Soapy AI Field Manual Showcase)

**Created:** 2026-06-13
**Status:** Active
**Companion docs:** [overview.md](overview.md) · [data_inventory.md](data_inventory.md) · [eval_plan.md](eval_plan.md) · [progress.md](../progress.md) · [CLAUDE.md](../CLAUDE.md)

---

## 1. Problem / Motivation

The Soapy AI Field Manual is a substantial personal work, but there is no way to *show* it to someone — a recruiter, a hiring manager, a peer — without handing over the full file. Sharing the whole manual gives away the entire work to anyone who asks; sharing nothing leaves the work invisible.

The goal is a middle path: a gated, searchable showcase that proves the manual's **coverage and depth** and offers exact-wording **tidbits**, without distributing the manual itself. As a portfolio piece, the *code* is also part of the story — it demonstrates a gated, server-side search system with a deliberate content-protection model.

---

## 2. Goal and Non-Goals

### Goal
A password-gated web app where a known contact enters a topic (e.g. `prompt caching`, `MCP`, `evaluation`) and receives:
1. **Coverage proof** — which chapters/sections address the topic (the manual's structure).
2. **Tidbits** — a few short, exact-wording excerpts from those sections.

### Non-Goals
- **Not an AI / Q&A app.** No LLM, no embeddings, no generated answers or summarization. Keyword search only.
- **Not a distribution channel.** No reading or exporting whole chapters; no browse-all, no pagination.
- **Not public-access.** Access is gated and the link is shared deliberately.
- **Not a search engine for the world.** Single corpus (this manual), single shared password.

---

## 3. Users and Access

| Aspect | Decision |
| --- | --- |
| Audience | People the author shares the link with directly (recruiters, hiring contacts, peers). |
| Auth model | Single shared password (no accounts, no per-user identity). |
| Trust posture | Casual showcase. Determined scraping is explicitly out of scope to prevent (see §7). |

**Representative user moment (drives the design):** A recruiter says *"I'm sure it covers agents, but does it give guidance on Evaluation? On MCP usage?"* The app must answer **that** question first — yes / where / how-deeply — and then offer a taste of the prose.

---

## 4. Core Behavior (UX)

Search returns a **two-layer** result, **coverage first**:

1. **Coverage layer (headline).** List the matching chapters and sections by number and title — e.g. *"Found in: Ch 13 Evaluation, Testing, and Observability → 13.4 Agent Evaluation, 13.5 LLM-as-Judge, 13.3 RAG Evaluation."* This proves coverage using the manual's table-of-contents depth and is the primary showcase value.
2. **Tidbit layer.** Under the coverage list, show a few capped, term-highlighted excerpts drawn from those sections.

Leading with structure is both the strongest pitch (it shows how thoroughly the manual is organized) and the most copy-resistant framing (the headline is the TOC, not prose).

---

## 5. Functional Requirements (Must / Should / May)

**Must**
- **M1.** Gate all content behind a single shared password before any search UI is shown.
- **M2.** Index only authored, current chapter content — the **latest `vN` per chapter**, excluding outlines, editorials, and `sources/`. *Satisfied at build time:* the corpus is the `build_manuscript.py` snapshot, which already performs this selection (see [data_inventory.md](data_inventory.md) §1). saifm trusts the snapshot rather than re-implementing discovery.
- **M3.** Perform exact-keyword search (no embeddings / semantic match).
- **M4.** Return the coverage layer (matching section numbers + titles) for every query.
- **M5.** Cap exposed prose: max ~700 characters per excerpt, max ~5 excerpts per query; no pagination, no "show full section," no browse-all. Excerpts are a centered window (context before and after the match).
- **M6.** Keep the full corpus server-side; send only the gate result and the capped excerpts to the browser.

**Should**
- **S1.** Rank results by relevance (BM25 or equivalent).
- **S2.** Highlight matched terms within excerpts.
- **S3.** Reject low-signal queries (empty, stopword-only, single common character) that would otherwise return everything.
- **S4.** Show a clear "no results" state that still reads as a finished product.

**May**
- **May1.** Per-session or per-IP rate limiting to blunt automated term-sweeping.
- **May2.** A short "About this manual" panel (TOC overview, chapter count, build date from the manifest) as standing showcase context.
- **May3.** Light usage logging (query counts) to see what visitors search for.

---

## 6. Architecture

The structural decisions are now settled; see [overview.md](overview.md) §3 for the canonical table. Summary:

| Layer | Choice | Rationale |
| --- | --- | --- |
| Repo | Standalone **public** portfolio repo; corpus gitignored | Code is part of the showcase; only the prose is secret. |
| UI | Streamlit | Author has built local Streamlit front-ends; ~120–150 lines total. |
| Search | SQLite FTS5 (stdlib `sqlite3`) | Built-in full-text search with BM25 ranking and `snippet()` highlighting; no extra service. |
| Index build | In-memory at startup, cached (`@st.cache_resource`) | Corpus is tiny (~17 chapters); rebuild on launch is instant and never stale. |
| Indexing unit | Split snapshot by `<!-- Source -->` markers → chapters, by `##`/`###` → sections, by paragraph; store `(chapter, section_number, heading, paragraph)`. | Section labels power the coverage layer; paragraphs are the snippet granularity. |
| Corpus delivery | `build_manuscript.py` mirrors `data/soapy_ai_manual.md` into saifm on every build (push-on-build) | One command builds and delivers; nothing to forget. |
| Gate | `st.text_input(type="password")` vs `st.secrets`, held in `session_state` | No auth service needed. |

**Build estimate:** ~120–150 lines across `app.py` + `indexer.py`, plus `requirements.txt`.

---

## 7. Content-Protection Model

**Threat model.** The concern is *bulk reconstruction* (scripting hundreds of queries to rebuild the manual), not one person copying one snippet.

**Decision (author):** Pragmatic. Snippet caps on the full corpus are sufficient. A determined scraper is explicitly out of scope — not worth design effort to stop.

**Mitigations in scope:** server-side search with snippets-only to the client (M6), hard snippet caps (M5), search-only with no browse/pagination (M5), low-signal query rejection (S3), optional rate limiting (May1). Leading with the coverage/TOC layer also rations prose by design. The corpus is gitignored, so it never enters the public repo (see [data_inventory.md](data_inventory.md) §5).

**Honest limit (fact, not solvable):** anything rendered in a browser can be copied; the FTS index must store the full prose to search and snippet it. These measures make casual copying low-value and bulk scraping slow; they do not make extraction impossible. This is accepted.

**Intentional exception — the gated sample.** The "Manual Preview" tab offers a downloadable 25-page excerpt (Chapter 1 foundations, ~5% of the manuscript) to gated viewers. This is a deliberate, bounded relaxation: it proves the work is a real, living document rather than a database. Scope is fixed (the least-proprietary intro chapter), it sits behind the password, and the PDF lives in gitignored `data/` — never committed to the public repo (it reaches the host via the same private channel as the corpus, OQ6).

---

## 8. Feasibility & Cost

**Feasibility: high.** No model, no API keys, no inference — the hardest and most expensive parts of a typical "AI app" are absent. The trickiest piece (selecting only current authored content) is already solved upstream by `build_manuscript.py`. Primary unknowns are product polish (result layout, query-rejection rules), not technical risk.

**Cost (ballparks — verify before committing):**

| Item | Estimate | Notes |
| --- | --- | --- |
| LLM / inference | **$0** | No model in the loop. |
| Hosting (Streamlit Community Cloud) | **$0** | Free tier; secrets-based password. Likely first deploy target — but see deploy open question. |
| Hosting (alt: Fly.io / Render / Railway) | **~$0–7/mo** | Free tiers exist; paid instance if more control / custom rate limiting wanted. |
| Custom domain (optional) | **~$10–15/yr** | Only if a vanity URL is desired. |

**Bottom line:** can run at **$0/month** on free hosting with no inference cost.

---

## 9. Open Questions / Decisions Pending

Already resolved: repo placement (standalone public repo), content sync (push-on-build mirror of `soapy_ai_manual.md`), agent-context file (`CLAUDE.md`), exact caps (OQ3 — ~700 chars × 5), deploy (OQ5/OQ6 below).

- **OQ5. Deploy target.** **Resolved (2026-06-16): Streamlit Community Cloud** — free, deploys from the GitHub repo, password via its secrets manager. No Docker.
- **OQ6. Private-corpus delivery to host.** **Resolved (2026-06-16): fetch-at-startup.** The app loads the corpus + preview PDF from local `data/` if present (dev), else fetches them from the **private manual repo** via the GitHub Contents API using a read-only token in secrets (`github_token`, `manual_repo`). Neither file ever enters this public repo. The same mechanism delivers `manual_preview.pdf`.

Still open:
- **OQ4. Coverage display depth.** Show every matching section, or top N? Show a match count per chapter?

---

## 10. Next Steps

1. Finish the remaining planning docs (`eval_plan.md`, `progress.md`, `CLAUDE.md`).
2. Scaffold the repo: `git init`, `requirements.txt`, root `.gitignore`.
3. Build `indexer.py` (parse snapshot → FTS5) and verify the coverage layer against the known TOC.
4. Build `app.py` (gate + two-layer search UI) and run locally.
5. Resolve OQ5/OQ6, then deploy gated and share the link selectively.
