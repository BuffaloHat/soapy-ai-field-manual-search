"""
Topic Cloud — vocabulary + coverage frequencies
================================================
Builds the data behind the Topic Cloud tab. Deterministic and keyword-derived
(no LLM): a curated core of concept PHRASES plus a sprinkle of canonical TAGS
for topic-level breadth, with the RAG acronym promoted as a headline token.

Weight = the number of manual sections that cover each item. Phrases occupy a
larger size band than tags, so the curated core reads as the headline and the
tags fill in around it. Rendering lives in build_image(); app.py just caches it.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List

# --- core: curated concept phrases (adjacent token pair -> display token) ------
PHRASES = {
    ("context", "window"): "context-window",
    ("system", "prompt"): "system-prompt",
    ("context", "engineering"): "context-engineering",
    ("context", "assembly"): "context-assembly",
    ("golden", "set"): "golden-set",
    ("failure", "modes"): "failure-modes", ("failure", "mode"): "failure-modes",
    ("token", "budget"): "token-budget",
    ("tool", "call"): "tool-call", ("tool", "calls"): "tool-call",
    ("tool", "descriptions"): "tool-descriptions",
    ("prompt", "engineering"): "prompt-engineering",
    ("prompt", "injection"): "prompt-injection",
    ("retrieval", "quality"): "retrieval-quality",
    ("retrieved", "context"): "retrieved-context",
    ("hybrid", "retrieval"): "hybrid-retrieval",
    ("vector", "search"): "vector-search",
    ("embedding", "model"): "embedding-model",
    ("agent", "loop"): "agent-loop",
    ("coding", "agent"): "coding-agent",
    ("harness", "engineering"): "harness-engineering",
    ("progressive", "disclosure"): "progressive-disclosure",
    ("long-term", "memory"): "long-term-memory",
    ("structured", "output"): "structured-output",
    ("acceptance", "criteria"): "acceptance-criteria",
    ("model", "version"): "model-version",
    ("eval", "plan"): "eval-plan",
    ("risk", "security"): "security-risk", ("security", "risk"): "security-risk",
}

# --- sprinkle: canonical tags that add topic-level breadth the phrases miss.
# tag -> alias regex matched (case-insensitive) over cleaned section text.
# Tags that merely duplicate a phrase (e.g. hybrid-search, structured-outputs)
# are intentionally omitted; agentic-ai is tightened to the paradigm term only.
SPRINKLE = {
    "agentic-ai": r"\bagentic\b",
    "large-language-models": r"\bllms?\b|large language model",
    "retrieval-augmented-generation": r"\brag\b|retrieval[- ]augmented",
    "fine-tuning": r"fine[- ]?tun",
    "chunking": r"\bchunk",
    "reranking": r"re[- ]?rank",
    "ai-deployment": r"\bdeploy|\bproduction\b|rollout|\bserving\b",
    "ai-reliability": r"reliabilit|failure mode|\bfallback|\bretry|\bretries",
    "ai-observability": r"observability|tracing|\bmonitor|\blogging\b",
    "ai-security": r"\bsecurity\b|jailbreak|\bexfiltrat",
    "ai-governance": r"governance|\bcompliance\b|\bpolicy\b|policies",
    "guardrails": r"guardrail",
    "multi-agent-systems": r"multi[- ]agent",
    "model-context-protocol": r"\bmcp\b|model context protocol",
    "human-in-the-loop": r"human[- ]in[- ]the[- ]loop|human (review|approval)",
    "agent-frameworks": r"agent framework|langchain|langgraph|crew\s?ai|autogen",
    "llm-orchestration": r"orchestrat",
    "ai-assisted-development": r"ai[- ]assisted|code assistant|copilot",
    "multimodal-ai": r"multi[- ]?modal",
    "transformers": r"\btransformers?\b",
    "long-context": r"long[- ]context|long context",
    "data-ingestion": r"\bingest",
    "knowledge-graphs": r"knowledge graph",
}

# The full canonical tag taxonomy. Every SPRINKLE key must be one of these, so
# the sprinkle can never drift from the shared tag vocabulary.
CANONICAL_TAGS = {
    "ai", "ai-engineering", "large-language-models", "fine-tuning", "transformers",
    "embeddings", "multimodal-ai", "ai-assisted-development", "ai-tools",
    "llm-orchestration", "prompt-engineering", "context-engineering",
    "harness-engineering", "structured-outputs", "tool-use", "prompt-testing",
    "context-management", "vibe-coding", "retrieval-augmented-generation",
    "data-ingestion", "document-processing", "chunking", "reranking",
    "vector-databases", "knowledge-graphs", "hybrid-search", "long-context",
    "agentic-ai", "agent-architecture", "ai-workflows", "agent-memory",
    "multi-agent-systems", "model-context-protocol", "human-in-the-loop",
    "agent-frameworks", "ai-evaluation", "ai-observability", "ai-security",
    "guardrails", "ai-governance", "ai-deployment", "ai-reliability",
    "modern-data-stack", "data-engineering", "data-architecture", "data-pipelines",
    "data-integration", "data-modeling", "analytics-engineering", "data-governance",
    "data-quality", "data-lakehouse", "data-cloud", "databases", "data-tools",
    "sql", "dbt", "snowflake", "duckdb", "apache-iceberg", "business-intelligence",
    "data-visualization",
}
assert set(SPRINKLE) <= CANONICAL_TAGS, (
    "SPRINKLE keys must be canonical tags: "
    + ", ".join(sorted(set(SPRINKLE) - CANONICAL_TAGS))
)

PALETTE = ["#2a9d8f", "#4d908e", "#3a7ca5", "#1f6f6f", "#577590", "#52b788"]  # soft blue-green
# Narrow bands + sqrt scaling keep the cloud calm: the biggest token is only
# ~2.4x the smallest, so headline terms (RAG, tool call) don't shout.
PHRASE_BAND = (0.66, 1.0)   # curated core: the big size band
TAG_BAND = (0.42, 0.62)     # tags: the smaller sprinkle band
SEED = 23                   # fixed: stable layout + colors across reloads/deploys
MIN_TAG_HITS = 5            # drop tags covered by fewer sections than this
_WORD_RE = re.compile(r"[a-z][a-z0-9\-]{2,}")


def _band(c: float, lo_c: float, hi_c: float, lo: float, hi: float) -> float:
    """Map a section count into a size band, sqrt-compressed so high counts
    don't stretch far past the pack (a calmer, more even cloud)."""
    import math
    c, lo_c, hi_c = math.sqrt(c), math.sqrt(lo_c), math.sqrt(hi_c)
    if hi_c == lo_c:
        return (lo + hi) / 2
    return lo + (c - lo_c) / (hi_c - lo_c) * (hi - lo)


def topic_frequencies(paragraphs) -> Dict[str, float]:
    """Display-token -> render weight. Phrases (plus the RAG acronym) land in the
    big band; sprinkle tags with enough coverage land in the small band."""
    pats = {t: re.compile(rx, re.IGNORECASE) for t, rx in SPRINKLE.items()}
    ph: Counter = Counter()
    tg: Counter = Counter()
    for p in paragraphs:
        toks = _WORD_RE.findall(p.text.lower())
        seen = set()
        for a, b in zip(toks, toks[1:]):
            disp = PHRASES.get((a, b))
            if disp:
                seen.add(disp)
        ph.update(seen)
        if "rag" in toks:                       # headline acronym (uppercase, phrase-tier)
            ph["RAG"] += 1
        for tag, pat in pats.items():
            if pat.search(p.text):
                tg[tag] += 1

    tg = Counter({t: c for t, c in tg.items() if c >= MIN_TAG_HITS})
    if not ph:
        return {}

    pmin, pmax = min(ph.values()), max(ph.values())
    freqs = {tok: _band(c, pmin, pmax, *PHRASE_BAND) for tok, c in ph.items()}
    if tg:
        tmin, tmax = min(tg.values()), max(tg.values())
        for tok, c in tg.items():
            freqs[tok] = _band(c, tmin, tmax, *TAG_BAND)
    # display: drop the hyphen ("context window"); the acronym RAG stays as-is.
    return {tok.replace("-", " "): w for tok, w in freqs.items()}


def build_html(paragraphs) -> str:
    """Render the cloud as a clean descending-size list of styled spans
    (biggest first, flowing left-to-right) — legible, deterministic, dep-free."""
    import random

    freqs = topic_frequencies(paragraphs)
    if not freqs:
        return ""
    wmin, wmax = min(freqs.values()), max(freqs.values())
    rng = random.Random(SEED)                       # stable, mixed blue-green
    spans = []
    for tok, w in sorted(freqs.items(), key=lambda kv: -kv[1]):
        size = 18 + (w - wmin) / (wmax - wmin) * 34 if wmax > wmin else 30  # 18..52 px
        color = rng.choice(PALETTE)
        spans.append(
            f'<span style="font-size:{size:.0f}px; color:{color}; font-weight:600; '
            f'margin:0 13px; line-height:1.3; display:inline-block; '
            f'white-space:nowrap;">{tok}</span>'
        )
    return ('<div style="text-align:center; padding:14px 4px 6px;">'
            + "".join(spans) + "</div>")
