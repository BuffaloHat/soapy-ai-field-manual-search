# Data Inventory — saifm

**Created:** 2026-06-13
**Companion:** [overview.md](overview.md) · [prd.md](prd.md)

This app indexes exactly **one corpus**: a prebuilt snapshot of the Soapy AI Field Manual. This doc records where it comes from, the contract it must satisfy, how it's refreshed, and how it's protected.

---

## 1. The corpus

| Aspect | Detail |
| --- | --- |
| **Artifact** | `soapy_ai_manual.md` — a single markdown file concatenating the current manual. A byte-for-byte copy of the manual repo's `manuscript_review.md`, renamed as saifm's primary artifact. |
| **Size** | ~778 KB, ~11,140 lines, 21 source sections (title page, intro, TOC, chapters 1–18, glossary, planning examples) as of 2026-06-11. |
| **Source of truth** | The **private** manual repo `soapy-ai-field-manual` (authored in Obsidian, synced via iCloud). saifm only *consumes* it. |
| **Built by** | `build_manuscript.py` in the manual repo (`--mode review`), which writes `build/manuscript_review.md` + a manifest, then mirrors a copy into saifm (see §4). |
| **Local source path** | `<icloud-obsidian-vault>/soapy_ai_field_manual/build/manuscript_review.md` (a local, machine-specific path) |
| **Where it lives in saifm** | `data/soapy_ai_manual.md` — **gitignored**, never committed to the public repo. |

### What the builder already guarantees (manual side)
`build_manuscript.py` performs *content selection*, so saifm doesn't have to:
- Includes Part 0 (`00_title_page.md`, `00_introduction_v1.md`, `toc.md`) then chapters **01–18**.
- Selects the **latest `vN`** per chapter; excludes `_outline` and `_editorial` files.
- Prepends `<!-- Source: manual/<dir>/<file> -->` before each section.
- Separates sections with a `<div class="chapter-break"></div>` marker.
- Rewrites relative image/attachment links (kept out of search by saifm; see §3).

This satisfies PRD **M2** (index only authored, current, latest-`vN` content) at *build time* — saifm trusts the snapshot rather than re-implementing discovery.

---

## 2. Format contract (the decoupling boundary)

`indexer.py` depends on these properties of the snapshot. As long as the manual's builder keeps emitting them, the two projects stay independent. **If this contract changes, `indexer.py` must change with it.**

| Element | Used for |
| --- | --- |
| `<!-- Source: manual/<dir>/<file> -->` markers | Splitting the file into chapters; deriving chapter identity (number + folder). |
| `#` / `##` / `###` headings | Section numbers + titles → the **coverage layer**. |
| `<div class="chapter-break"></div>` separators | Secondary section boundary signal. |
| Paragraph breaks (blank lines) | Snippet granularity for the **tidbit layer**. |

Anything outside this contract (HTML wrapper divs, image links, attachment refs) is **noise** that `indexer.py` strips before indexing — see §3.

---

## 3. Indexing units & cleaning (saifm side)

`indexer.py` turns the snapshot into searchable rows:

- **Granularity:** split by `Source` markers → chapters; by `##`/`###` headings → sections; by blank lines → paragraphs. Sub-threshold paragraphs (< ~80 chars, e.g. subheading lead-ins) are merged into a same-section neighbor so excerpts carry context, not one-line fragments.
- **Row shape:** `(chapter, section_number, heading, paragraph_text)`.
- **Search-side cleaning (saifm's job, not the manual's):**
  - Strip HTML wrapper divs (`title-page`, `chapter-break`, etc.).
  - Strip image/attachment markdown (`![...](...)`) and bare attachment links.
  - Strip inline markdown emphasis (`**`/`*`), inline-code backticks, and leading list markers.
  - Exclude reference-scaffolding sections ("Tools and Field Cards") — table-heavy, low showcase value; removed from coverage and excerpts alike (like the title page / TOC).
  - Drop empty/structural-only fragments.
- **Excerpts:** a centered ~700-char window around the match (context before and after), with all query terms highlighted. Capped at 5 per query, one per section.
- **Index:** SQLite FTS5, BM25 ranking. Built **in-memory at startup**, cached with `@st.cache_resource`. Rebuild is instant (tiny corpus); never stale relative to the snapshot it loaded.

---

## 4. Delivery & refresh cadence

**Two delivery paths, same source.** Locally the corpus + preview load from `data/`; when those files are absent (deploy), the app fetches them from the **private manual repo** via the GitHub Contents API using a read-only token (`github_token` + `manual_repo` in secrets — see [prd.md](prd.md) OQ6). Neither file ever enters this public repo. Deploy refresh = commit the updated `build/manuscript_review.md` (and `build/manual_preview.pdf`) to the private repo, then reboot the Streamlit Cloud app.

The manual is **edited continuously** (sections added, rewritten, deleted). The app is only as current as the last snapshot delivered. Local delivery is **push-on-build**: `build_manuscript.py` mirrors a copy straight into `saifm/data/` as part of its run.

```
1. (manual repo)  python scripts/build_manuscript.py --mode review
                    → writes build/manuscript_review.md
                    → mirrors a copy to saifm/data/soapy_ai_manual.md  (best-effort)
2. (saifm)        restart app  → index rebuilds at startup
3. redeploy if the live URL needs updating
```

The mirror step (appended to `build_manuscript.py`'s `main()`):

```python
# Mirror an exact copy into the saifm showcase project, if present on this machine.
saifm_dest = Path("<local-saifm-checkout>/data/soapy_ai_manual.md")
if saifm_dest.parent.is_dir():
    saifm_dest.write_text(manuscript)
    print(f"Mirrored manuscript to {saifm_dest}")
```

- **Best-effort by design:** `build_manuscript.py` lives in the iCloud-synced manual vault, so it runs on machines where `saifm/` may not exist. The `is_dir()` guard means the copy is skipped quietly there and never fails the manual build.
- **Cadence:** automatic on every manual build — no separate saifm-side step, nothing to forget.
- **Staleness risk:** low and self-correcting — there is no partial/incremental index to drift; each build replaces the whole snapshot.

---

## 5. Protection & sensitivity

- **Sensitivity:** the prose is the author's unpublished work product. The *value* of the showcase depends on **not** distributing it.
- **Never public:** `data/` (snapshot + any built index) is gitignored. The public repo contains code and docs only.
- **Honest limit:** the snapshot necessarily contains the full prose (FTS must store text to search and snippet it). Protection is *operational* (server-side, gitignored, capped output), not cryptographic. Bulk reconstruction by a determined scraper is explicitly **out of scope** — see [prd.md](prd.md) Content-Protection.
- **Deploy implication (open):** because the corpus can't be in the public repo, the host must receive it through a private channel (baked into the deploy image / fetched from private storage / built locally and shipped). Resolved in [prd.md](prd.md) deploy section — tracked as an open question.

---

## 6. Open questions

- **DI-1.** Path portability — the mirror step hardcodes saifm's absolute path in `build_manuscript.py`. The `is_dir()` guard makes this safe (skips where absent), but if saifm ever moves, update the path. An env var (`SAIFM_DATA_DIR`) is the more portable alternative if multi-machine builds matter.
- **DI-2.** Whether to also copy the `manuscript_review_manifest.txt` for provenance/version display in the UI's "About" panel.
- **DI-3.** Final deploy-time delivery of the private corpus to the host (ties to PRD deploy decision).
