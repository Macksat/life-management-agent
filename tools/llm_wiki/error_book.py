"""Phase 3 Error Book utilities."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ValidationIssue

DEFAULT_CONSTRAINTS = {
    "require_issue_next_action": True,
    "require_issue_status": True,
    "require_evidence": True,
    "allow_weak_only_topics": False,
}


def error_book_dir(root: Path) -> Path:
    return root / "error_book"


def constraints_path(root: Path) -> Path:
    return error_book_dir(root) / "constraints.json"


def errors_path(root: Path) -> Path:
    return error_book_dir(root) / "errors.json"


def repair_log_path(root: Path) -> Path:
    return error_book_dir(root) / "repair_log.jsonl"


def load_constraints(root: Path) -> dict[str, Any]:
    path = constraints_path(root)
    if not path.exists():
        return dict(DEFAULT_CONSTRAINTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(DEFAULT_CONSTRAINTS)
    merged = dict(DEFAULT_CONSTRAINTS)
    merged.update(data)
    return merged


def save_constraints(root: Path, constraints: dict[str, Any]) -> Path:
    path = constraints_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(constraints, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_errors(root: Path, issues: list[ValidationIssue]) -> Path:
    path = errors_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(issue) for issue in issues]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_repair_log(
    root: Path,
    *,
    action: str,
    target: str,
    detail: str,
) -> Path:
    path = repair_log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "detail": detail,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path

