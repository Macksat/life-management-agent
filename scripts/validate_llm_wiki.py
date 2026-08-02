#!/usr/bin/env python3
"""LLMWiki artifacts を検証する。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools.llm_wiki import wiki_validate


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate LLMWiki artifacts")
    parser.add_argument("--root", type=str, default=None, help="Wiki root path override")
    args = parser.parse_args()

    report = wiki_validate(root=args.root)
    if report.ok:
        print("Validation OK")
        return

    print("Validation issues:")
    for issue in report.issues:
        print(f"- [{issue.code}] {issue.path}: {issue.message}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
