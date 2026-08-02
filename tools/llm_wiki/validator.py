"""Phase 1 向けの軽量 validator。"""

from __future__ import annotations
from pathlib import Path

from .models import ValidationIssue, ValidationReport
from .paths import DEFAULT_WIKI_ROOT, REPO_ROOT
from .search import load_pages


def _has_only_weak_links(page) -> bool:
    # Sparse second_brain single-record topics often only have heuristic links; do not fail them.
    if page.metadata.get("source_layers") == ["second_brain"] and page.metadata.get("record_count") == 1:
        return False
    non_source_links = [link for link in page.links if link.relation != "derived_from"]
    if not non_source_links:
        return False
    return all(link.confidence < 1.0 for link in non_source_links)


def validate_wiki(
    root: Path | str | None = None,
    *,
    constraints: dict | None = None,
) -> ValidationReport:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    pages = load_pages(
        [
            str(path.relative_to(wiki_root / "pages"))
            for path in sorted((wiki_root / "pages").rglob("*.md"))
        ],
        root=wiki_root,
    )
    by_path = {page.path: page for page in pages}
    constraint_map = constraints or {}

    issues: list[ValidationIssue] = []
    seen_topic_titles: dict[str, str] = {}
    for page in pages:
        if page.page_type != "index" and constraint_map.get("require_evidence", True) and not page.source_refs:
            issues.append(
                ValidationIssue(
                    code="missing_evidence",
                    path=page.path,
                    message="page has no source_refs",
                    )
                )

        if page.page_type == "issues":
            if constraint_map.get("require_issue_next_action", True) and not page.metadata.get("next_action"):
                issues.append(
                    ValidationIssue(
                        code="missing_next_action",
                        path=page.path,
                        message="issue page has no next_action",
                    )
                )
            if constraint_map.get("require_issue_status", True) and not page.metadata.get("status"):
                issues.append(
                    ValidationIssue(
                        code="missing_status",
                        path=page.path,
                        message="issue page has no status label",
                    )
                )
            if page.metadata.get("state") == "OPEN" and not page.metadata.get("next_action"):
                issues.append(
                    ValidationIssue(
                        code="stale_next_action_snapshot",
                        path=page.path,
                        message="open issue snapshot is missing next_action",
                    )
                )

        if page.page_type == "topics":
            normalized_title = page.metadata.get("canonical_title", page.title).strip().lower()
            if normalized_title in seen_topic_titles:
                issues.append(
                    ValidationIssue(
                        code="duplicated_page",
                        path=page.path,
                        message=f"duplicate topic title with {seen_topic_titles[normalized_title]}",
                    )
                )
            else:
                seen_topic_titles[normalized_title] = page.path

            if not constraint_map.get("allow_weak_only_topics", False) and _has_only_weak_links(page):
                issues.append(
                    ValidationIssue(
                        code="weak_only_topic",
                        path=page.path,
                        message="topic page has only weak non-source links",
                    )
                )

        if page.summary.strip() == f"# {page.title}".strip() or page.summary.strip() == page.title.strip():
            issues.append(
                ValidationIssue(
                    code="unsupported_summary",
                    path=page.path,
                    message="summary looks like a copied heading without abstraction",
                )
            )

        for link in page.links:
            if link.relation == "derived_from":
                if link.target_path.startswith("http://") or link.target_path.startswith("https://"):
                    continue
                source_file = REPO_ROOT / link.target_path
                if not source_file.exists():
                    issues.append(
                        ValidationIssue(
                            code="missing_source",
                            path=page.path,
                            message=f"missing source file: {link.target_path}",
                        )
                    )
                continue

            if link.target_path not in by_path:
                issues.append(
                    ValidationIssue(
                        code="dangling_link",
                        path=page.path,
                        message=f"dangling link: {link.target_path}",
                    )
                )

    return ValidationReport(ok=not issues, issues=issues)
