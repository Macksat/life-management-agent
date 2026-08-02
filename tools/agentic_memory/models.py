"""Data models for A-MEM style source updates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

MemoryAction = Literal["add_new", "update_existing", "skip_duplicate", "strengthen_link", "update_neighbor"]


@dataclass
class AgenticMemoryEntry:
    """Incoming memory candidate before source write."""

    content: str
    memory_type: str
    target_section: str
    layer: str = "memories"
    source_path: str = ""
    source_refs: list[str] = field(default_factory=list)
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryCandidate:
    """Existing source entry considered for update."""

    entry_id: str
    layer: str
    source_path: str
    section_name: str
    text: str
    memory_type: str
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryDecision:
    """Final action selected for a new memory entry."""

    action: MemoryAction
    target_path: str
    target_section: str
    reason: str
    matched_entry_id: str = ""
    matched_text: str = ""
    updated_text: str = ""
    link_targets: list[str] = field(default_factory=list)
    metadata_updates: dict[str, Any] = field(default_factory=dict)
    similarity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryUpdateResult:
    """Outcome of a processed agentic memory update."""

    entry: AgenticMemoryEntry
    candidates: list[MemoryCandidate]
    decision: MemoryDecision
    changed: bool
    audit_path: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry": self.entry.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "decision": self.decision.to_dict(),
            "changed": self.changed,
            "audit_path": self.audit_path,
            "error": self.error,
        }
