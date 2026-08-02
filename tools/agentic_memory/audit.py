"""Append-only audit log for agentic memory decisions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.llm_wiki.paths import DEFAULT_WIKI_ROOT

from .models import AgenticMemoryEntry, MemoryCandidate, MemoryDecision

AUDIT_FILE = "agentic_memory_decisions.jsonl"


def audit_log_path(root: Path | str | None = None) -> Path:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    return wiki_root / "indexes" / AUDIT_FILE


def append_audit_log(
    *,
    entry: AgenticMemoryEntry,
    candidates: list[MemoryCandidate],
    decision: MemoryDecision,
    changed: bool,
    root: Path | str | None = None,
    error: str = "",
) -> Path:
    path = audit_log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changed": changed,
        "error": error,
        "entry": entry.to_dict(),
        "decision": decision.to_dict(),
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False))
        fh.write("\n")
    return path
