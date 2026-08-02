"""Persistent note metadata store for A-MEM style memory evolution."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.llm_wiki.paths import DEFAULT_WIKI_ROOT


STORE_FILE = "agentic_memory_store.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M")


@dataclass
class MemoryNoteState:
    entry_id: str
    content: str
    layer: str
    memory_type: str
    source_path: str
    target_section: str
    keywords: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    retrieval_count: int = 0
    timestamp: str = field(default_factory=_now)
    last_accessed: str = field(default_factory=_now)
    context: str = "General"
    evolution_history: list[dict[str, Any]] = field(default_factory=list)
    category: str = "Uncategorized"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryNoteState":
        return cls(**data)


def store_path(root: Path | str | None = None) -> Path:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    return wiki_root / "indexes" / STORE_FILE


def load_store(root: Path | str | None = None) -> dict[str, MemoryNoteState]:
    path = store_path(root)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {entry_id: MemoryNoteState.from_dict(payload) for entry_id, payload in raw.items()}


def save_store(store: dict[str, MemoryNoteState], root: Path | str | None = None) -> Path:
    path = store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {entry_id: note.to_dict() for entry_id, note in store.items()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def upsert_note(
    store: dict[str, MemoryNoteState],
    *,
    entry_id: str,
    content: str,
    layer: str,
    memory_type: str,
    source_path: str,
    target_section: str,
    keywords: list[str] | None = None,
    context: str | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
) -> MemoryNoteState:
    note = store.get(entry_id)
    if note is None:
        note = MemoryNoteState(
            entry_id=entry_id,
            content=content,
            layer=layer,
            memory_type=memory_type,
            source_path=source_path,
            target_section=target_section,
            keywords=list(keywords or []),
            context=context or "General",
            tags=list(tags or []),
            category=category or "Uncategorized",
        )
        store[entry_id] = note
        return note

    note.content = content
    note.layer = layer
    note.memory_type = memory_type
    note.source_path = source_path
    note.target_section = target_section
    if keywords:
        note.keywords = list(dict.fromkeys(keywords))
    if context:
        note.context = context
    if tags:
        note.tags = list(dict.fromkeys(tags))
    if category:
        note.category = category
    return note


def touch_note(note: MemoryNoteState) -> None:
    note.retrieval_count += 1
    note.last_accessed = _now()


def add_links(note: MemoryNoteState, links: list[str]) -> None:
    note.links = list(dict.fromkeys([*note.links, *links]))


def append_evolution(note: MemoryNoteState, event: dict[str, Any]) -> None:
    payload = {"timestamp": _now(), **event}
    note.evolution_history.append(payload)


def apply_neighbor_updates(
    note: MemoryNoteState,
    *,
    context: str | None = None,
    tags: list[str] | None = None,
    reason: str = "",
) -> None:
    if context:
        note.context = context
    if tags:
        note.tags = list(dict.fromkeys(tags))
    append_evolution(
        note,
        {
            "action": "update_neighbor",
            "reason": reason,
            "context": note.context,
            "tags": note.tags,
        },
    )
