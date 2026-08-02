"""Phase 1 LLMWiki builders。

spec: docs/llm_wiki.md Phase 1
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .issues import _normalize_section_key
from .models import IssueSnapshot, MemoryRecord, SourceRef, WikiPage

_TOPIC_SPLIT_RE = re.compile(r"[,/|、・\n]+")
_TOKEN_SPLIT_RE = re.compile(r"[\s/|,、。・:：()\[\]{}<>_\-]+")
_MEANINGLESS_LINE_RE = re.compile(r"^(#|##|###|-\s*\[.\]|-\s*$|\|[- :|]+\|?)")
_METADATA_LINE_PREFIXES = (
    "- **日時:**",
    "**日時:**",
    "日時:",
    "date:",
    "category:",
    "type:",
    "status:",
    "priority:",
    "goal:",
    "next_action:",
)


def normalize_slug(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^\w\s-]", " ", lowered)
    lowered = re.sub(r"\s+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered or "untitled"


def topic_tokens(text: str) -> list[str]:
    tokens = []
    for token in _TOKEN_SPLIT_RE.split(text):
        token = token.strip().lower()
        if len(token) < 2:
            continue
        if token.isdigit():
            continue
        if re.fullmatch(r"\d{4}", token):
            continue
        tokens.append(token)
    return tokens


def split_topic_tags(tag_text: str) -> list[str]:
    parts = []
    for part in _TOPIC_SPLIT_RE.split(tag_text):
        part = part.strip()
        if part:
            parts.append(part)
    return parts


def _first_lines(text: str, limit: int = 3) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _MEANINGLESS_LINE_RE.match(line):
            continue
        lowered = line.lower()
        if any(lowered.startswith(prefix.lower()) for prefix in _METADATA_LINE_PREFIXES):
            continue
        lines.append(line)
    return lines[:limit]


def _best_summary(lines: list[str], fallback: str) -> str:
    cleaned = [line for line in lines if line and not line.startswith("#")]
    if cleaned:
        return " / ".join(cleaned[:3])[:400]
    return fallback[:400]


def _make_source_ref(record: MemoryRecord) -> SourceRef:
    return SourceRef(
        source_type=record.layer,
        source_path=record.source_path,
        anchor=record.section or record.title or None,
    )


def _dedupe_source_refs(refs: list[SourceRef]) -> list[SourceRef]:
    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[SourceRef] = []
    for ref in refs:
        key = (ref.source_type, ref.source_path, ref.anchor)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def build_people_pages(records: Iterable[MemoryRecord]) -> list[WikiPage]:
    grouped: dict[str, list[MemoryRecord]] = defaultdict(list)
    order = ["facts", "preferences", "user_context"]
    titles = {
        "facts": "Self Facts",
        "preferences": "Self Preferences",
        "user_context": "Self Context",
    }
    aliases = {
        "facts": ["facts", "個人的事実"],
        "preferences": ["preferences", "好み"],
        "user_context": ["user_context", "文脈"],
    }

    for record in records:
        if record.layer != "memories":
            continue
        memory_type = record.metadata.get("memory_type")
        if memory_type in titles:
            grouped[memory_type].append(record)

    pages: list[WikiPage] = []
    for memory_type in order:
        items = grouped.get(memory_type, [])
        if not items:
            continue
        key_facts = [item.text for item in items[:8]]
        summary = _best_summary(key_facts[:3], titles[memory_type])
        pages.append(
            WikiPage(
                page_id=f"people-self-{memory_type.replace('_', '-')}",
                page_type="people_self",
                title=titles[memory_type],
                path=f"people_self/{memory_type}.md",
                summary=summary,
                tags=[memory_type, "self"],
                aliases=aliases[memory_type],
                source_refs=_dedupe_source_refs([_make_source_ref(item) for item in items]),
                metadata={
                    "memory_type": memory_type,
                    "record_count": len(items),
                },
                key_facts=key_facts,
                open_questions=[],
            )
        )
    return pages


def build_timeline_pages(records: Iterable[MemoryRecord]) -> list[WikiPage]:
    grouped: dict[tuple[str, str, str], list[MemoryRecord]] = defaultdict(list)

    for record in records:
        if record.layer != "conversation_memory":
            continue
        span = record.metadata.get("memory_span", "unknown")
        entry_date = record.metadata.get("entry_date", "") or "undated"
        grouped[(span, entry_date, record.source_path)].append(record)

    pages: list[WikiPage] = []
    for (span, entry_date, source_path), items in sorted(grouped.items(), reverse=True):
        slug = normalize_slug(f"{entry_date}-{span}")
        title = f"Timeline {entry_date} ({span})"
        page_id = f"timeline-{slug}"
        key_facts = []
        for item in items[:6]:
            key_facts.extend(_first_lines(item.text, limit=1))
        pages.append(
            WikiPage(
                page_id=page_id,
                page_type="timelines",
                title=title,
                path=f"timelines/{slug}.md",
                summary=_best_summary(_first_lines(items[0].text, limit=3), title),
                tags=[span, entry_date],
                aliases=[entry_date, span],
                source_refs=_dedupe_source_refs([_make_source_ref(item) for item in items]),
                metadata={
                    "memory_span": span,
                    "entry_date": entry_date,
                    "source_path": source_path,
                    "record_count": len(items),
                },
                key_facts=key_facts[:8],
                open_questions=[],
            )
        )
    return pages


def build_topic_pages(records: Iterable[MemoryRecord]) -> list[WikiPage]:
    buckets: dict[str, dict[str, object]] = {}

    def ensure_bucket(topic_name: str) -> dict[str, object]:
        slug = normalize_slug(topic_name)
        bucket = buckets.get(slug)
        if bucket is None:
            bucket = {
                "title": topic_name,
                "records": [],
                "aliases": set(),
                "tags": set(),
            }
            buckets[slug] = bucket
        return bucket

    for record in records:
        if record.layer == "rules":
            continue

        seeds: list[str] = []
        if record.layer == "second_brain":
            seeds.extend(split_topic_tags(str(record.metadata.get("theme_tags", ""))))
            if not seeds and record.title:
                seeds.append(record.title)
        elif record.layer == "memories":
            section = str(record.metadata.get("section_name", "")).strip()
            if section:
                seeds.append(section)
        elif record.layer == "conversation_memory":
            title = record.title.strip()
            if title and not title.lower().startswith("day summary"):
                seeds.append(title)

        for seed in seeds:
            bucket = ensure_bucket(seed)
            bucket["records"].append(record)
            bucket["aliases"].add(seed)
            for token in topic_tokens(seed):
                bucket["tags"].add(token)

    pages: list[WikiPage] = []
    for slug, bucket in sorted(buckets.items()):
        topic_title = str(bucket["title"])
        items = list(bucket["records"])
        if not items:
            continue

        # conversation_memory 由来だけの topic は増えすぎるので間引く
        source_layers = {item.layer for item in items}
        if source_layers == {"conversation_memory"} and len(items) < 2:
            continue

        page_id = f"topic-{slug}"
        summary_lines = [part for item in items[:3] for part in _first_lines(item.text, limit=1)]
        page_summary = _best_summary(summary_lines, topic_title)
        key_facts = []
        for item in items[:8]:
            key_facts.extend(_first_lines(item.text, limit=1))

        tags = sorted(set(bucket["tags"]))[:12]
        aliases = sorted(set(str(alias) for alias in bucket["aliases"]))[:8]
        pages.append(
            WikiPage(
                page_id=page_id,
                page_type="topics",
                title=topic_title,
                path=f"topics/{slug}.md",
                summary=page_summary,
                tags=tags,
                aliases=aliases,
                source_refs=_dedupe_source_refs([_make_source_ref(item) for item in items[:20]]),
                metadata={
                    "record_count": len(items),
                    "source_layers": sorted(source_layers),
                    "canonical_title": topic_title,
                },
                key_facts=key_facts[:10],
                open_questions=[],
            )
        )
    return pages


def build_index_page(page_type: str, pages: list[WikiPage]) -> WikiPage:
    title = f"{page_type.replace('_', ' ').title()} Index"
    path = f"{page_type}/_index.md"
    key_facts = [f"{page.title}: {page.summary}" for page in pages[:8]]
    return WikiPage(
        page_id=f"index-{page_type}",
        page_type="index",
        title=title,
        path=path,
        summary=f"{page_type} pages: {len(pages)}",
        tags=[page_type, "index"],
        aliases=[page_type],
        metadata={
            "index_for": page_type,
            "selection_rule": "sorted by title",
            "page_count": len(pages),
        },
        key_facts=key_facts,
        open_questions=[],
    )


def _issue_field(sections: dict[str, str], *names: str) -> str:
    for name in names:
        value = sections.get(_normalize_section_key(name), "").strip()
        if value:
            return value
    return ""


def _extract_label_value(labels: list[str], prefix: str) -> str:
    for label in labels:
        if label.startswith(prefix):
            return label
    return ""


def _extract_issue_numbers(text: str) -> list[int]:
    numbers = []
    for match in re.finditer(r"#(\d+)", text):
        numbers.append(int(match.group(1)))
    return sorted(set(numbers))


def _extract_inline_section_value(body: str, *names: str) -> str:
    target_keys = {_normalize_section_key(name) for name in names}
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if _normalize_section_key(key) in target_keys and value.strip():
            return value.strip()
    return ""


def _infer_issue_next_action(
    title: str,
    issue_type: str,
    body: str,
) -> str:
    lowered_title = title.lower()
    lowered_body = body.lower()
    if "dashboard" in lowered_title:
        return "次回の集計結果を確認する"
    if "時計候補" in title:
        return "候補ごとの比較軸と優先順位を整理する"
    if "daily" in lowered_title or "本日のタスク管理" in title:
        return "今日扱う個別 Issue と next_action を見直す"
    if issue_type == "type:habit":
        return "次回の定期更新タイミングで内容を確認する"
    if issue_type == "type:research":
        return "本文を整理して次の調査ステップを明記する"
    if issue_type == "type:project":
        return "子 Issue と最初の着手順を明記する"
    if "やること" in body or "todo" in lowered_body:
        return "本文のタスクリストから最初の一手を 1 つ選ぶ"
    return "本文を整理して next_action を明記する"


def _infer_issue_status(labels: list[str], state: str) -> str:
    status = _extract_label_value(labels, "status:")
    if status:
        return status
    if state.upper() == "OPEN":
        return "status:ready"
    return "status:done"


def _latest_comment_summary(comments: list[str]) -> str:
    for comment in reversed(comments):
        lines = _first_lines(comment, limit=2)
        if lines:
            return " / ".join(lines)[:400]
    return ""


def build_issue_pages(issues: Iterable[IssueSnapshot]) -> list[WikiPage]:
    pages: list[WikiPage] = []
    for issue in sorted(issues, key=lambda item: item.number, reverse=True):
        status = _infer_issue_status(issue.labels, issue.state)
        priority = _extract_label_value(issue.labels, "priority:")
        issue_type = _extract_label_value(issue.labels, "type:")
        category = _extract_label_value(issue.labels, "category:")
        goal = _issue_field(issue.sections, "goal") or _extract_inline_section_value(issue.body, "goal")
        next_action = (
            _issue_field(issue.sections, "next_action", "next action")
            or _extract_inline_section_value(issue.body, "next_action", "next action")
        )
        acceptance = _issue_field(
            issue.sections,
            "acceptance_criteria",
            "acceptance criteria",
        ) or _extract_inline_section_value(issue.body, "acceptance_criteria", "acceptance criteria")
        parent = _issue_field(issue.sections, "parent")
        related = _issue_field(
            issue.sections,
            "related_links / related_issues",
            "related_issues",
            "related",
            "related links",
        )
        if not next_action:
            next_action = _infer_issue_next_action(issue.title, issue_type, issue.body)
        latest_summary = (
            _latest_comment_summary(issue.comments)
            or goal
            or next_action
            or (_first_lines(issue.body, limit=1)[0] if _first_lines(issue.body, limit=1) else issue.title)
        )
        related_numbers = _extract_issue_numbers("\n".join([related, acceptance, issue.body]))
        parent_numbers = _extract_issue_numbers(parent)

        path_slug = normalize_slug(issue.title)
        pages.append(
            WikiPage(
                page_id=f"issue-{issue.number}-{path_slug}",
                page_type="issues",
                title=issue.title,
                path=f"issues/{issue.number}-{path_slug}.md",
                summary=latest_summary[:400],
                tags=[tag for tag in [issue_type, category, status, priority] if tag],
                aliases=[f"#{issue.number}", str(issue.number)],
                source_refs=[
                    SourceRef(
                        source_type="github_issue",
                        source_path=issue.url,
                        anchor=None,
                    )
                ],
                metadata={
                    "issue_number": issue.number,
                    "state": issue.state,
                    "url": issue.url,
                    "labels": issue.labels,
                    "comment_count": len(issue.comments),
                    "status": status,
                    "priority": priority,
                    "issue_type": issue_type,
                    "category": category,
                    "goal": goal,
                    "next_action": next_action,
                    "acceptance_criteria": acceptance,
                    "related_issues": related_numbers,
                    "parent_issues": parent_numbers,
                },
                key_facts=[
                    fact
                    for fact in [goal, next_action, acceptance, parent]
                    if fact
                ][:8],
                open_questions=[],
            )
        )
    return pages


def build_project_pages(issues: Iterable[IssueSnapshot]) -> list[WikiPage]:
    issue_map = {issue.number: issue for issue in issues}
    pages: list[WikiPage] = []
    for issue in sorted(issues, key=lambda item: item.number, reverse=True):
        if "type:project" not in issue.labels:
            continue

        goal = _issue_field(issue.sections, "goal")
        context = _issue_field(issue.sections, "context")
        milestones = _issue_field(issue.sections, "milestones")
        tasks = _issue_field(issue.sections, "tasks")
        next_action = _issue_field(issue.sections, "next_action", "next action")
        child_numbers = _extract_issue_numbers("\n".join([milestones, tasks, issue.body]))
        child_titles = [
            f"#{number} {issue_map[number].title}"
            for number in child_numbers
            if number in issue_map
        ]
        path_slug = normalize_slug(issue.title)
        summary = _best_summary(
            [item for item in [goal, context, next_action, *child_titles] if item],
            issue.title,
        )
        pages.append(
            WikiPage(
                page_id=f"project-{issue.number}-{path_slug}",
                page_type="projects",
                title=issue.title,
                path=f"projects/{issue.number}-{path_slug}.md",
                summary=summary,
                tags=[
                    "type:project",
                    *[label for label in issue.labels if label.startswith("category:")],
                ],
                aliases=[f"project #{issue.number}", f"#{issue.number}"],
                source_refs=[
                    SourceRef(
                        source_type="github_issue",
                        source_path=issue.url,
                        anchor=None,
                    )
                ],
                metadata={
                    "issue_number": issue.number,
                    "goal": goal,
                    "context": context,
                    "next_action": next_action,
                    "child_issues": child_numbers,
                    "status": _extract_label_value(issue.labels, "status:"),
                },
                key_facts=[
                    fact
                    for fact in [goal, next_action, *child_titles]
                    if fact
                ][:10],
                open_questions=[],
            )
        )
    return pages
