#!/usr/bin/env python3
"""LLMWiki retrieval quality scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools.llm_wiki import wiki_follow_links, wiki_read_index, wiki_search


def evaluate_case(case: dict, root: str | None) -> dict:
    page_type = case.get("index_type", "topics")
    index_path = None
    try:
        index_page = wiki_read_index(page_type, root=root)
        index_path = index_page.path
    except FileNotFoundError:
        index_page = None
    search_results = wiki_search(case["query"], top_k=case.get("top_k", 5), root=root)
    found_paths = [result.path for result in search_results]
    follow_paths: list[str] = []
    if search_results:
        follow_paths = [link.target_path for link in wiki_follow_links(search_results[0].path, top_k=10, root=root)]
    expected_any = set(case.get("expected_any", []))
    haystack = list(found_paths + follow_paths)
    if index_path:
        haystack.append(index_path)
    matched = bool(expected_any & set(haystack))
    return {
        "query": case["query"],
        "matched": matched,
        "index_path": index_path,
        "found_paths": found_paths,
        "follow_paths": follow_paths,
        "expected_any": sorted(expected_any),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LLMWiki retrieval scaffold")
    parser.add_argument("--cases", required=True, help="JSON file with eval cases")
    parser.add_argument("--root", default=None, help="Wiki root override")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    results = [evaluate_case(case, args.root) for case in cases]
    passed = sum(1 for result in results if result["matched"])
    print(json.dumps({"passed": passed, "total": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
