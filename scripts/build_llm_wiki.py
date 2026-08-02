#!/usr/bin/env python3
"""LLMWiki artifacts をビルドする。

spec: docs/llm_wiki.md Phase 1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools.llm_wiki import wiki_build


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 1 LLMWiki artifacts")
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Output root (default: data/llm_wiki)",
    )
    parser.add_argument(
        "--include-issues",
        action="store_true",
        help="Include GitHub Issue snapshot pages",
    )
    parser.add_argument(
        "--refresh-issues",
        action="store_true",
        help="Refresh issue snapshot via gh before build",
    )
    parser.add_argument(
        "--issue-snapshot",
        type=str,
        default=None,
        help="Issue snapshot JSON path",
    )
    parser.add_argument(
        "--include-issue-comments",
        action="store_true",
        help="When refreshing issues, also fetch recent issue comments",
    )
    parser.add_argument(
        "--no-semantic-links",
        action="store_true",
        help="Skip L2 semantic linking based on embeddings",
    )
    parser.add_argument(
        "--force-embeddings",
        action="store_true",
        help="Rebuild page embeddings even when cache metadata matches",
    )
    parser.add_argument(
        "--serendipity",
        action="store_true",
        help="Enable L4 serendipity links",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM calls for serendipity generation",
    )
    args = parser.parse_args()

    started = time.time()
    counts = wiki_build(
        root=args.root,
        include_issues=args.include_issues,
        refresh_issues=args.refresh_issues,
        issue_snapshot_path=args.issue_snapshot,
        include_issue_comments=args.include_issue_comments,
        enable_semantic_links=not args.no_semantic_links,
        force_embeddings=args.force_embeddings,
        enable_serendipity=args.serendipity,
        use_llm=not args.no_llm,
    )
    elapsed = time.time() - started

    print(f"Build completed in {elapsed:.1f}s")
    for key, value in sorted(counts.items()):
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
