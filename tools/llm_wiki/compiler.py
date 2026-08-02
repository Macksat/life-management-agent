"""Phase 1 LLMWiki compiler。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .builders import (
    build_index_page,
    build_issue_pages,
    build_people_pages,
    build_project_pages,
    build_timeline_pages,
    build_topic_pages,
)
from .error_book import append_repair_log, load_constraints, save_constraints, save_errors
from .issues import fetch_open_issues, load_issue_snapshot, save_issue_snapshot
from .linker import link_structural
from .linker_coref import link_co_referenced
from .linker_semantic import link_semantic
from .linker_serendipity import link_serendipity
from .models import WikiPage
from .parsers import parse_all
from .paths import DEFAULT_WIKI_ROOT
from .validator import validate_wiki
PAGES_ROOT = DEFAULT_WIKI_ROOT / "pages"
INDEXES_ROOT = DEFAULT_WIKI_ROOT / "indexes"

PRESERVED_INDEX_FILES = {
    "co_references.jsonl",
    "embeddings.npz",
    "embeddings_meta.json",
    "similarity_cache.json",
    "serendipity_cache.json",
}


def _render_page(page: WikiPage) -> str:
    metadata_lines = [
        f"- page_type: {page.page_type}",
        f"- canonical_id: {page.page_id}",
        f"- aliases: {', '.join(page.aliases) if page.aliases else '-'}",
        f"- tags: {', '.join(page.tags) if page.tags else '-'}",
        f"- source_refs: {len(page.source_refs)}",
        f"- updated_at: generated",
    ]
    relation_lines = [
        f"- {link.relation}: [{link.target_page_id}]({link.target_path})"
        for link in page.links[:20]
    ] or ["- -"]
    evidence_lines = [
        f"- source: {ref.source_path}" + (f"#{ref.anchor}" if ref.anchor else "")
        for ref in page.source_refs[:20]
    ] or ["- -"]
    key_facts = [f"- {fact}" for fact in page.key_facts] or ["- -"]
    open_questions = [f"- {item}" for item in page.open_questions] or ["- -"]

    parts = [
        f"# {page.title}",
        "",
        "## Metadata",
        *metadata_lines,
        "",
        "## Summary",
        "",
        page.summary or "-",
        "",
        "## Key Facts",
        "",
        *key_facts,
        "",
        "## Relations",
        "",
        *relation_lines,
        "",
        "## Evidence",
        "",
        *evidence_lines,
        "",
        "## Open Questions",
        "",
        *open_questions,
        "",
    ]
    return "\n".join(parts)


def _reset_output(root: Path) -> None:
    # sources/ は保護する — ビルド成果物のみリセット
    root.mkdir(parents=True, exist_ok=True)
    pages_root = root / "pages"
    indexes_root = root / "indexes"

    if pages_root.exists():
        shutil.rmtree(pages_root)
    pages_root.mkdir(parents=True, exist_ok=True)

    indexes_root.mkdir(parents=True, exist_ok=True)
    for child in indexes_root.iterdir():
        if child.name in PRESERVED_INDEX_FILES:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _write_pages(root: Path, pages: list[WikiPage]) -> None:
    for page in pages:
        target = root / "pages" / page.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_page(page), encoding="utf-8")


def _write_indexes(root: Path, pages: list[WikiPage]) -> None:
    page_index = [page.to_dict() for page in pages]
    alias_index: dict[str, list[str]] = {}
    graph = {}
    for page in pages:
        graph[page.path] = [link.to_dict() for link in page.links]
        keys = [page.title, page.page_id, *page.aliases, *page.tags]
        for key in keys:
            normalized = key.strip().lower()
            if not normalized:
                continue
            alias_index.setdefault(normalized, [])
            if page.path not in alias_index[normalized]:
                alias_index[normalized].append(page.path)

    (root / "indexes" / "page_index.json").write_text(
        json.dumps(page_index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "indexes" / "alias_index.json").write_text(
        json.dumps(alias_index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "indexes" / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _apply_auto_repairs(root: Path, pages: list[WikiPage], issues: list) -> tuple[list[WikiPage], list[str]]:
    dangling_targets = {
        (issue.path, issue.message.removeprefix("dangling link: ").strip())
        for issue in issues
        if issue.code == "dangling_link"
    }
    repaired: list[str] = []
    if dangling_targets:
        page_map = {page.path: page for page in pages}
        for page_path, target_path in sorted(dangling_targets):
            page = page_map.get(page_path)
            if page is None:
                continue
            before = len(page.links)
            page.links = [
                link for link in page.links
                if not (link.target_path == target_path and link.relation != "derived_from")
            ]
            if len(page.links) != before:
                detail = f"removed dangling link to {target_path}"
                repaired.append(f"{page_path}: {detail}")
                append_repair_log(root, action="remove_dangling_link", target=page_path, detail=detail)

    for page in pages:
        if page.page_type == "index":
            before = [link.target_path for link in page.links]
            page.links = sorted(page.links, key=lambda link: (link.target_path, link.relation))
            after = [link.target_path for link in page.links]
            if before != after:
                repaired.append(f"{page.path}: sorted index links")
                append_repair_log(root, action="sort_index_links", target=page.path, detail="sorted index links")

    return pages, repaired


def build_wiki(
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
    output_root = Path(root) if root else DEFAULT_WIKI_ROOT
    constraints = load_constraints(output_root)
    issue_pages: list[WikiPage] = []
    project_pages: list[WikiPage] = []

    if include_issues:
        if refresh_issues:
            issues = fetch_open_issues(include_comments=include_issue_comments)
            save_issue_snapshot(issues, path=issue_snapshot_path)
        else:
            issues = load_issue_snapshot(path=issue_snapshot_path)
        issue_pages = build_issue_pages(issues)
        project_pages = build_project_pages(issues)

    _reset_output(output_root)

    records = [record for record in parse_all() if record.layer != "rules"]
    people_pages = build_people_pages(records)
    timeline_pages = build_timeline_pages(records)
    topic_pages = build_topic_pages(records)

    main_pages = people_pages + timeline_pages + topic_pages + issue_pages + project_pages
    index_pages = [
        build_index_page("topics", topic_pages),
        build_index_page("people_self", people_pages),
        build_index_page("timelines", timeline_pages),
    ]
    if include_issues:
        index_pages.append(build_index_page("issues", issue_pages))
        index_pages.append(build_index_page("projects", project_pages))
    pages = link_structural(main_pages + index_pages)
    if enable_semantic_links:
        pages = link_semantic(pages, root=output_root, force_embed=force_embeddings)
    pages = link_co_referenced(pages, root=output_root)
    if enable_serendipity:
        pages = link_serendipity(pages, root=output_root, use_llm=use_llm)

    # Validate in-memory pages before writing, then apply minimal repairs.
    _write_pages(output_root, pages)
    _write_indexes(output_root, pages)
    report = validate_wiki(output_root, constraints=constraints)
    repaired: list[str] = []
    if report.issues:
        pages, repaired = _apply_auto_repairs(output_root, pages, report.issues)
        if repaired:
            _write_pages(output_root, pages)
            _write_indexes(output_root, pages)
            report = validate_wiki(output_root, constraints=constraints)

    save_errors(output_root, report.issues)
    save_constraints(output_root, constraints)

    return {
        "topics": len(topic_pages),
        "people_self": len(people_pages),
        "timelines": len(timeline_pages),
        "issues": len(issue_pages),
        "projects": len(project_pages),
        "indexes": len(index_pages),
        "total_pages": len(pages),
        "validation_issues": len(report.issues),
        "auto_repairs": len(repaired),
        "l2_similar_to_links": sum(
            1 for page in pages for link in page.links if link.relation == "similar_to"
        ),
        "l3_co_referenced_links": sum(
            1 for page in pages for link in page.links if link.relation == "co_referenced"
        ),
        "l4_serendipity_links": sum(
            1 for page in pages for link in page.links if link.relation == "serendipity"
        ),
    }
