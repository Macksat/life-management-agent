"""Parsers that normalize LLMWiki source files into MemoryRecord values."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from .models import MemoryRecord
from .paths import REPO_ROOT

_DATE_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})")
_MEMORY_TYPE_MAP = {
    "facts.md": "facts",
    "preferences.md": "preferences",
    "decisions.md": "decisions",
    "user_context.md": "user_context",
}
_SPAN_DIRS = {
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
}


def _short_hash(text: str, length: int = 8) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:length]


def _extract_date(line: str) -> str:
    match = _DATE_RE.search(line)
    return match.group(1) if match else ""


def _recency_bucket(date_str: str, today: date | None = None) -> str:
    if not date_str:
        return "old"
    today = today or date.today()
    try:
        parsed = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return "old"
    diff = (today - parsed).days
    if diff <= 7:
        return "recent"
    if diff <= 30:
        return "mid"
    return "old"


def _rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_memories(base_dir: Path | None = None) -> Iterator[MemoryRecord]:
    base = base_dir or REPO_ROOT / "data" / "llm_wiki" / "sources" / "memories"
    for filename, memory_type in _MEMORY_TYPE_MAP.items():
        file_path = base / filename
        if not file_path.exists():
            continue
        current_section = ""
        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                current_section = line.lstrip("# ").strip()
                continue
            if not line.startswith("- "):
                continue
            if line.startswith("<!-- ") or line.startswith("- <!-- "):
                continue
            text = line.lstrip("- ").strip()
            if not text:
                continue
            record_date = _extract_date(text)
            yield MemoryRecord(
                id=f"memories:{memory_type}:{_short_hash(text)}",
                layer="memories",
                source_path=_rel_path(file_path),
                title=f"{memory_type}/{current_section}",
                text=text,
                summary="",
                tags=memory_type,
                section=current_section,
                date=record_date,
                recency_bucket=_recency_bucket(record_date),
                metadata={
                    "memory_type": memory_type,
                    "section_name": current_section,
                },
            )


def _parse_index_tags(base_dir: Path) -> dict[str, str]:
    index_path = base_dir / "index.md"
    if not index_path.exists():
        return {}
    tags_map: dict[str, str] = {}
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if "|" not in line:
            continue
        columns = [column.strip() for column in line.split("|")]
        if len(columns) < 5:
            continue
        filename = columns[4]
        theme = columns[3]
        if filename.endswith(".md"):
            tags_map[filename] = theme
    return tags_map


def parse_second_brain(base_dir: Path | None = None) -> Iterator[MemoryRecord]:
    base = base_dir or REPO_ROOT / "data" / "llm_wiki" / "sources" / "second_brain"
    digests_dir = base / "digests"
    if not digests_dir.exists():
        return
    tags_map = _parse_index_tags(base)

    for file_path in sorted(digests_dir.glob("*.md")):
        if file_path.name == ".gitkeep":
            continue
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        title = ""
        for line in lines:
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break

        digest_date = ""
        match = re.match(r"(\d{4}-\d{2}-\d{2})", file_path.name)
        if match:
            digest_date = match.group(1)

        theme_tags = tags_map.get(file_path.name, "")
        yield MemoryRecord(
            id=f"second_brain:{file_path.stem}",
            layer="second_brain",
            source_path=_rel_path(file_path),
            title=title,
            text=content,
            summary="",
            tags=theme_tags,
            section="",
            date=digest_date,
            recency_bucket=_recency_bucket(digest_date),
            metadata={
                "digest_date": digest_date,
                "theme_tags": theme_tags,
                "source_kind": "digest",
            },
        )


def _extract_entry_date_from_path(file_path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", file_path.name)
    if match:
        return match.group(1)
    match = re.search(r"(\d{4}-W\d{2})", file_path.name)
    if match:
        return match.group(1)
    match = re.search(r"(\d{4}-\d{2})", file_path.name)
    if match:
        return match.group(1)
    return ""


def _parse_conversation_sessions(
    content: str,
    memory_span: str,
    entry_date: str,
    file_path: Path,
) -> Iterator[MemoryRecord]:
    lines = content.splitlines()
    current_session_title = ""
    current_session_lines: list[str] = []

    def _flush() -> MemoryRecord | None:
        if not current_session_title:
            return None
        text = "\n".join(current_session_lines).strip()
        if not text:
            return None
        slug = _short_hash(f"{file_path.name}:{current_session_title}")
        base_date = entry_date[:10] if len(entry_date) >= 10 else entry_date
        return MemoryRecord(
            id=f"conversation:{memory_span}:{entry_date}:{slug}",
            layer="conversation_memory",
            source_path=_rel_path(file_path),
            title=current_session_title,
            text=text,
            summary="",
            tags="",
            section=current_session_title,
            date=entry_date,
            recency_bucket=_recency_bucket(base_date),
            metadata={
                "memory_span": memory_span,
                "entry_date": entry_date,
            },
        )

    for line in lines:
        if line.startswith("### ") or line.startswith("## "):
            record = _flush()
            if record:
                yield record
            current_session_title = line.lstrip("# ").strip()
            current_session_lines = []
            continue
        current_session_lines.append(line)

    record = _flush()
    if record:
        yield record


def parse_conversation_memory(base_dir: Path | None = None) -> Iterator[MemoryRecord]:
    base = base_dir or REPO_ROOT / "data" / "llm_wiki" / "sources" / "conversation_memory"
    for span_name, span_dir in _SPAN_DIRS.items():
        span_path = base / span_dir
        if not span_path.exists():
            continue
        for file_path in sorted(span_path.rglob("*.md"), reverse=True):
            if file_path.name.startswith("."):
                continue
            content = file_path.read_text(encoding="utf-8")
            entry_date = _extract_entry_date_from_path(file_path)
            yield from _parse_conversation_sessions(content, span_name, entry_date, file_path)


def parse_rules(rules_path: Path | None = None) -> Iterator[MemoryRecord]:
    path = rules_path or REPO_ROOT / "data" / "llm_wiki" / "sources" / "memories" / "rules.json"
    if not path.exists():
        return
    rules = json.loads(path.read_text(encoding="utf-8"))
    for index, rule in enumerate(rules):
        title = rule.get("title", f"rule_{index}")
        text = "\n".join(
            [
                f"title: {title}",
                f"trigger: {rule.get('trigger', '')}",
                f"if: {rule.get('if', '')}",
                f"then: {rule.get('then', '')}",
            ]
        )
        yield MemoryRecord(
            id=f"rules:{_short_hash(title)}",
            layer="rules",
            source_path=_rel_path(path),
            title=title,
            text=text,
            summary="",
            tags="rules",
            section="",
            date="",
            recency_bucket="",
            metadata={
                "trigger": rule.get("trigger", ""),
                "if_condition": rule.get("if", ""),
                "then_action": rule.get("then", ""),
            },
        )


def parse_all() -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    records.extend(parse_memories())
    records.extend(parse_second_brain())
    records.extend(parse_conversation_memory())
    records.extend(parse_rules())
    return records
