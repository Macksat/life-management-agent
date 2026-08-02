"""Phase 1 LLMWiki search。"""

from __future__ import annotations

import json
from pathlib import Path

from .models import WikiPage, WikiSearchResult
from .paths import DEFAULT_WIKI_ROOT


def _load_page_index(root: Path) -> list[WikiPage]:
    page_index_path = root / "indexes" / "page_index.json"
    if not page_index_path.exists():
        raise FileNotFoundError(
            f"Wiki index not found: {page_index_path}\n"
            "Run python scripts/build_llm_wiki.py first."
        )
    raw = json.loads(page_index_path.read_text(encoding="utf-8"))
    return [WikiPage.from_dict(item) for item in raw]


def _score_page(page: WikiPage, query: str) -> tuple[float, str]:
    q = query.strip().lower()
    if not q:
        return 0.0, "empty query"

    score = 0.0
    reasons: list[str] = []
    if q in page.title.lower():
        score += 3.0
        reasons.append("title match")
    if any(q in alias.lower() for alias in page.aliases):
        score += 2.0
        reasons.append("alias match")
    if any(q in tag.lower() for tag in page.tags):
        score += 1.5
        reasons.append("tag match")
    if q in page.summary.lower():
        score += 1.0
        reasons.append("summary match")

    tokens = [token for token in q.split() if token]
    corpus = " ".join([page.title, page.summary, *page.tags, *page.aliases]).lower()
    token_hits = sum(1 for token in tokens if token in corpus)
    if token_hits:
        score += min(1.5, token_hits * 0.5)
        reasons.append(f"token hits:{token_hits}")

    return score, ", ".join(reasons) or "no match"


def search_pages(
    query: str,
    page_types: list[str] | None = None,
    top_k: int = 5,
    root: Path | str | None = None,
) -> list[WikiSearchResult]:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    pages = _load_page_index(wiki_root)
    target_types = set(page_types or [])

    results: list[WikiSearchResult] = []
    for page in pages:
        if target_types and page.page_type not in target_types:
            continue
        score, reason = _score_page(page, query)
        if score <= 0:
            continue
        results.append(
            WikiSearchResult(
                page_id=page.page_id,
                page_type=page.page_type,
                title=page.title,
                path=page.path,
                score=score,
                reason=reason,
                summary=page.summary,
                tags=page.tags,
            )
        )

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:top_k]


def load_pages(paths: list[str], root: Path | str | None = None) -> list[WikiPage]:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    pages = _load_page_index(wiki_root)
    by_path = {page.path: page for page in pages}
    return [by_path[path] for path in paths if path in by_path]


def load_index_page(page_type: str, root: Path | str | None = None) -> WikiPage:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    target_path = f"{page_type}/_index.md"
    pages = load_pages([target_path], root=wiki_root)
    if not pages:
        raise FileNotFoundError(f"Index page not found: {target_path}")
    return pages[0]
