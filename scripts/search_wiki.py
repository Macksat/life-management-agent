#!/usr/bin/env python3
"""LLMWiki を検索・閲覧する CLI。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools.llm_wiki import wiki_follow_links, wiki_read, wiki_read_index, wiki_search


def main() -> None:
    parser = argparse.ArgumentParser(description="Search or inspect LLMWiki pages")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--type", dest="page_type", action="append", help="Page type filter")
    parser.add_argument("--top-k", type=int, default=5, help="Number of search results")
    parser.add_argument("--index", dest="index_type", help="Read an index page by type")
    parser.add_argument("--read", dest="read_path", help="Read a page by relative path")
    parser.add_argument("--follow", dest="follow_path", help="Follow links from a page path")
    parser.add_argument("--root", dest="root", help="Wiki root path override")
    args = parser.parse_args()

    if args.index_type:
        page = wiki_read_index(args.index_type, root=args.root)
        print(f"[index] {page.title}")
        print(f"path: {page.path}")
        print(f"summary: {page.summary}")
        for link in page.links[:12]:
            print(f"  - {link.target_path}")
        return

    if args.read_path:
        pages = wiki_read([args.read_path], root=args.root)
        if not pages:
            print(f"Page not found: {args.read_path}")
            return
        page = pages[0]
        print(f"[{page.page_type}] {page.title}")
        print(f"path: {page.path}")
        print(f"summary: {page.summary}")
        if page.key_facts:
            print("key_facts:")
            for fact in page.key_facts[:5]:
                print(f"  - {fact}")
        if page.links:
            print("links:")
            for link in page.links[:8]:
                print(f"  - {link.relation}: {link.target_path} ({link.confidence:.2f})")
        return

    if args.follow_path:
        links = wiki_follow_links(args.follow_path, top_k=args.top_k, root=args.root)
        for link in links:
            print(f"- {link.relation}: {link.target_path} ({link.confidence:.2f}) [{link.source}]")
        return

    if not args.query:
        parser.error("query is required unless --index, --read, or --follow is used")

    results = wiki_search(args.query, page_types=args.page_type, top_k=args.top_k, root=args.root)
    if not results:
        print("No results found.")
        return

    for result in results:
        print(f"[{result.page_type}] {result.title} score={result.score:.2f}")
        print(f"  path: {result.path}")
        print(f"  reason: {result.reason}")
        print(f"  summary: {result.summary}")


if __name__ == "__main__":
    main()
