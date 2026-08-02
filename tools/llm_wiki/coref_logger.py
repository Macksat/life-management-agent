"""Conversation-time co-reference logging for LLMWiki."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import CoReference
from .paths import DEFAULT_WIKI_ROOT

JST = timezone(timedelta(hours=9))
COREF_FILE = "co_references.jsonl"


def _coref_path(root: Path | str | None = None) -> Path:
    wiki_root = Path(root) if root else DEFAULT_WIKI_ROOT
    return wiki_root / "indexes" / COREF_FILE


def log_co_reference(
    pages: list[str],
    query_intent: str,
    conversation_id: str = "",
    root: Path | str | None = None,
) -> dict[str, str]:
    """Append a co-reference record to the JSONL log."""

    normalized_pages = sorted(set(pages))
    if len(normalized_pages) < 2:
        return {"status": "skipped", "reason": "2ページ以上の共起が必要"}

    now = datetime.now(JST)
    record = CoReference(
        pages=normalized_pages,
        query_intent=query_intent.strip(),
        timestamp=now.isoformat(),
        conversation_id=conversation_id or f"conv_{now.strftime('%Y%m%d_%H%M%S')}",
    )

    path = _coref_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    return {
        "status": "logged",
        "pages": str(len(record.pages)),
        "intent": record.query_intent,
    }


def load_co_references(root: Path | str | None = None) -> list[CoReference]:
    """Load all co-reference records."""

    path = _coref_path(root)
    if not path.exists():
        return []

    records: list[CoReference] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(CoReference.from_dict(json.loads(line)))
    return records
