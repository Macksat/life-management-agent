"""Shared paths for llm_wiki modules."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WIKI_ROOT = REPO_ROOT / "data" / "llm_wiki"
