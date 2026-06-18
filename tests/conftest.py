"""Shared fixtures for the saifm test suite.

The checks are deterministic (no network, no model): they run against the local
corpus snapshot. If it isn't present (e.g. a fresh clone without the gitignored
`data/`), the corpus-dependent tests skip rather than fail.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import cloud  # noqa: E402
import indexer  # noqa: E402


@pytest.fixture(scope="session")
def paragraphs():
    """Parsed corpus rows (skips the suite if the snapshot isn't on this machine)."""
    if not indexer.DATA_FILE.exists():
        pytest.skip(f"corpus snapshot not available at {indexer.DATA_FILE}")
    return indexer.parse_corpus()


@pytest.fixture(scope="session")
def con(paragraphs):
    """An in-memory FTS5 index built once for the whole session."""
    return indexer.build_index(paragraphs)
