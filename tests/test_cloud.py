"""Topic Cloud checks: vocabulary integrity (eval_plan.md I5) and the
prose-free guarantee (P6).
"""
import re

import cloud


def test_sprinkle_subset_of_canonical():
    """I5 — the sprinkle tags can't drift from the shared canonical taxonomy."""
    assert set(cloud.SPRINKLE) <= cloud.CANONICAL_TAGS


def test_frequencies_nonempty(paragraphs):
    """I5 — the cloud produces a non-empty vocabulary, with RAG promoted."""
    freqs = cloud.topic_frequencies(paragraphs)
    assert freqs
    assert "RAG" in freqs


def test_cloud_is_prose_free(paragraphs):
    """P6 — every token rendered in the cloud is a known vocabulary item, never prose."""
    vocab = set(cloud.topic_frequencies(paragraphs))
    tokens = re.findall(r">([^<]+)</span>", cloud.build_html(paragraphs))
    assert tokens
    unexpected = [t for t in tokens if t not in vocab]
    assert not unexpected, f"non-vocabulary tokens leaked into the cloud: {unexpected}"
