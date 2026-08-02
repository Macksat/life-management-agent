"""Phase 1 LLMWiki linker。"""

from __future__ import annotations

from collections import defaultdict

from .builders import topic_tokens
from .models import WikiLink, WikiPage


def _page_token_set(page: WikiPage) -> set[str]:
    pieces = [page.title, page.summary, *page.tags, *page.aliases]
    tokens: set[str] = set()
    for piece in pieces:
        tokens.update(topic_tokens(piece))
    return tokens


def _shared_source_paths(page: WikiPage) -> set[str]:
    return {ref.source_path for ref in page.source_refs}


def link_structural(pages: list[WikiPage]) -> list[WikiPage]:
    by_type: dict[str, list[WikiPage]] = defaultdict(list)
    token_cache: dict[str, set[str]] = {}
    for page in pages:
        by_type[page.page_type].append(page)
        token_cache[page.page_id] = _page_token_set(page)

    index_pages = by_type.get("index", [])
    topic_pages = by_type.get("topics", [])
    people_pages = by_type.get("people_self", [])
    timeline_pages = by_type.get("timelines", [])
    issue_pages = by_type.get("issues", [])
    project_pages = by_type.get("projects", [])
    page_by_issue_number = {
        page.metadata.get("issue_number"): page
        for page in issue_pages + project_pages
        if page.metadata.get("issue_number") is not None
    }

    for index_page in index_pages:
        target_type = index_page.metadata.get("index_for")
        for target in by_type.get(str(target_type), [])[:20]:
            index_page.links.append(
                WikiLink(
                    relation="index_of",
                    target_page_id=target.page_id,
                    target_path=target.path,
                    confidence=1.0,
                    source="index",
                )
            )

    for topic in topic_pages:
        topic_tokens_set = token_cache[topic.page_id]
        topic_sources = _shared_source_paths(topic)
        existing_targets: set[tuple[str, str]] = set()

        for person in people_pages:
            overlap = topic_tokens_set & token_cache[person.page_id]
            if not overlap:
                continue
            confidence = min(0.95, 0.4 + 0.1 * len(overlap))
            key = ("relates_to", person.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            topic.links.append(
                WikiLink(
                    relation="relates_to",
                    target_page_id=person.page_id,
                    target_path=person.path,
                    confidence=confidence,
                    source=f"token_overlap:{','.join(sorted(overlap)[:4])}",
                )
            )

        for timeline in timeline_pages:
            overlap = topic_tokens_set & token_cache[timeline.page_id]
            if not overlap:
                continue
            confidence = min(0.95, 0.35 + 0.1 * len(overlap))
            key = ("mentions", timeline.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            topic.links.append(
                WikiLink(
                    relation="mentions",
                    target_page_id=timeline.page_id,
                    target_path=timeline.path,
                    confidence=confidence,
                    source=f"token_overlap:{','.join(sorted(overlap)[:4])}",
                )
            )

        for ref in topic.source_refs[:10]:
            key = ("derived_from", ref.source_path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            topic.links.append(
                WikiLink(
                    relation="derived_from",
                    target_page_id=ref.source_path,
                    target_path=ref.source_path,
                    confidence=1.0,
                    source="source_ref",
                )
            )

        for issue_page in issue_pages[:50]:
            overlap = topic_tokens_set & token_cache[issue_page.page_id]
            if not overlap:
                continue
            key = ("references_issue", issue_page.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            topic.links.append(
                WikiLink(
                    relation="references_issue",
                    target_page_id=issue_page.page_id,
                    target_path=issue_page.path,
                    confidence=min(0.9, 0.35 + 0.1 * len(overlap)),
                    source=f"token_overlap:{','.join(sorted(overlap)[:4])}",
                )
            )

        for other_topic in topic_pages:
            if other_topic.page_id == topic.page_id:
                continue
            source_overlap = topic_sources & _shared_source_paths(other_topic)
            token_overlap = topic_tokens_set & token_cache[other_topic.page_id]
            if not source_overlap and len(token_overlap) < 2:
                continue
            key = ("relates_to_topic", other_topic.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            confidence = 1.0 if source_overlap else min(0.8, 0.4 + 0.1 * len(token_overlap))
            source_reason = (
                f"shared_source:{','.join(sorted(source_overlap)[:2])}"
                if source_overlap else
                f"token_overlap:{','.join(sorted(token_overlap)[:4])}"
            )
            topic.links.append(
                WikiLink(
                    relation="relates_to_topic",
                    target_page_id=other_topic.page_id,
                    target_path=other_topic.path,
                    confidence=confidence,
                    source=source_reason,
                )
            )

    for issue_page in issue_pages:
        related_numbers = issue_page.metadata.get("related_issues", [])
        parent_numbers = issue_page.metadata.get("parent_issues", [])
        issue_tokens = token_cache[issue_page.page_id]
        existing_targets: set[tuple[str, str]] = set()

        for number in related_numbers:
            related_page = page_by_issue_number.get(number)
            if related_page is None:
                continue
            key = ("related_issue", related_page.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            issue_page.links.append(
                WikiLink(
                    relation="related_issue",
                    target_page_id=related_page.page_id,
                    target_path=related_page.path,
                    confidence=1.0,
                    source="body_reference",
                )
            )

        for project_page in project_pages:
            children = set(project_page.metadata.get("child_issues", []))
            issue_number = issue_page.metadata.get("issue_number")
            project_number = project_page.metadata.get("issue_number")
            if issue_number in children or project_number in parent_numbers:
                key = ("child_of", project_page.path)
                if key not in existing_targets:
                    existing_targets.add(key)
                    issue_page.links.append(
                        WikiLink(
                            relation="child_of",
                            target_page_id=project_page.page_id,
                            target_path=project_page.path,
                            confidence=1.0,
                            source="project_tasks",
                        )
                    )

        for topic in topic_pages:
            overlap = issue_tokens & token_cache[topic.page_id]
            if not overlap:
                continue
            key = ("relates_to_topic", topic.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            issue_page.links.append(
                WikiLink(
                    relation="relates_to_topic",
                    target_page_id=topic.page_id,
                    target_path=topic.path,
                    confidence=min(0.85, 0.35 + 0.1 * len(overlap)),
                    source=f"token_overlap:{','.join(sorted(overlap)[:4])}",
                )
            )

    for project_page in project_pages:
        child_numbers = set(project_page.metadata.get("child_issues", []))
        project_number = project_page.metadata.get("issue_number")
        existing_targets: set[tuple[str, str]] = set()
        for issue_page in issue_pages:
            if project_number in set(issue_page.metadata.get("parent_issues", [])):
                child_numbers.add(issue_page.metadata.get("issue_number"))
        for number in child_numbers:
            child_page = page_by_issue_number.get(number)
            if child_page is None:
                continue
            key = ("parent_of", child_page.path)
            if key in existing_targets:
                continue
            existing_targets.add(key)
            project_page.links.append(
                WikiLink(
                    relation="parent_of",
                    target_page_id=child_page.page_id,
                    target_path=child_page.path,
                    confidence=1.0,
                    source="project_tasks",
                )
            )

    return pages


# Backward compatibility for existing callers.
link_pages = link_structural
