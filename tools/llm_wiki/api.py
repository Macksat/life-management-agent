"""LLMWiki public API。"""

from __future__ import annotations

from pathlib import Path

from .compiler import DEFAULT_WIKI_ROOT, build_wiki
from .coref_logger import log_co_reference
from .error_book import load_constraints
from .models import ValidationReport, WikiLink, WikiPage, WikiSearchResult
from .search import load_index_page, load_pages, search_pages
from .validator import validate_wiki


def wiki_build(
    root: Path | str | None = None,
    *,
    include_issues: bool = False,
    refresh_issues: bool = False,
    issue_snapshot_path: Path | str | None = None,
    include_issue_comments: bool = False,
    enable_semantic_links: bool = True,
    force_embeddings: bool = False,
    enable_serendipity: bool = False,
    use_llm: bool = True,
) -> dict[str, int]:
    return build_wiki(
        root=root,
        include_issues=include_issues,
        refresh_issues=refresh_issues,
        issue_snapshot_path=issue_snapshot_path,
        include_issue_comments=include_issue_comments,
        enable_semantic_links=enable_semantic_links,
        force_embeddings=force_embeddings,
        enable_serendipity=enable_serendipity,
        use_llm=use_llm,
    )


def wiki_search(
    query: str,
    page_types: list[str] | None = None,
    top_k: int = 5,
    filters: dict | None = None,
    root: Path | str | None = None,
) -> list[WikiSearchResult]:
    del filters
    return search_pages(query, page_types=page_types, top_k=top_k, root=root)


def wiki_read(
    paths: list[str],
    include_sections: list[str] | None = None,
    root: Path | str | None = None,
) -> list[WikiPage]:
    del include_sections
    return load_pages(paths, root=root)


def wiki_read_index(page_type: str, root: Path | str | None = None) -> WikiPage:
    return load_index_page(page_type, root=root)


def wiki_follow_links(
    page_path: str,
    relation_types: list[str] | None = None,
    top_k: int = 10,
    root: Path | str | None = None,
) -> list[WikiLink]:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    pages = load_pages([page_path], root=wiki_root)
    if not pages:
        raise FileNotFoundError(f"Page not found: {page_path}")
    links = pages[0].links
    if relation_types:
        links = [link for link in links if link.relation in relation_types]
    return links[:top_k]


def wiki_validate(
    changed_paths: list[str] | None = None,
    root: Path | str | None = None,
) -> ValidationReport:
    del changed_paths
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    return validate_wiki(root=wiki_root, constraints=load_constraints(wiki_root))


def wiki_log_co_reference(
    pages: list[str],
    query_intent: str,
    conversation_id: str = "",
    root: Path | str | None = None,
) -> dict[str, str]:
    return log_co_reference(
        pages=pages,
        query_intent=query_intent,
        conversation_id=conversation_id,
        root=root,
    )
