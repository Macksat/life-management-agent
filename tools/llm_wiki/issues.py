"""GitHub Issue snapshot loading and parsing for Phase 2."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import IssueSnapshot
from .paths import REPO_ROOT

DEFAULT_ISSUE_SNAPSHOT_PATH = REPO_ROOT / "data" / "github" / "open_issues.json"

_ISSUE_FIELDS = "number,title,body,labels,url,state"


def _normalize_section_key(key: str) -> str:
    normalized = key.strip().lower()
    normalized = normalized.replace("(", " ").replace(")", " ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace(":", " ")
    normalized = "_".join(part for part in normalized.split() if part)
    return normalized


def _parse_frontmatter(body: str) -> tuple[dict[str, str], str]:
    lines = body.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, body

    frontmatter: dict[str, str] = {}
    end_index = None
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == "---":
            end_index = idx
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[_normalize_section_key(key)] = value.strip()

    if end_index is None:
        return {}, body
    remaining = "\n".join(lines[end_index + 1 :]).strip()
    return frontmatter, remaining


def parse_issue_sections(body: str) -> dict[str, str]:
    frontmatter, body_without_frontmatter = _parse_frontmatter(body)
    sections: dict[str, list[str]] = {}
    current_key = "_preamble"
    sections[current_key] = []

    for raw_line in body_without_frontmatter.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current_key = _normalize_section_key(line[3:].strip())
            sections.setdefault(current_key, [])
            continue
        sections.setdefault(current_key, [])
        sections[current_key].append(line)

    normalized_sections = {
        key: "\n".join(lines).strip()
        for key, lines in sections.items()
        if "\n".join(lines).strip()
    }
    normalized_sections.update(frontmatter)
    return normalized_sections


def _normalize_issue_item(item: dict) -> IssueSnapshot:
    label_names = [label["name"] if isinstance(label, dict) else str(label) for label in item.get("labels", [])]
    body = item.get("body", "") or ""
    return IssueSnapshot(
        number=int(item["number"]),
        title=item.get("title", ""),
        body=body,
        state=item.get("state", ""),
        url=item.get("url", ""),
        labels=label_names,
        comments=list(item.get("comments", [])),
        sections=parse_issue_sections(body),
    )


def _fetch_issue_comments(number: int, comment_limit: int = 3) -> list[str]:
    cmd = [
        "gh",
        "issue",
        "view",
        str(number),
        "--json",
        "comments",
    ]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    comments = payload.get("comments", []) or []
    bodies = []
    for comment in comments[-comment_limit:]:
        body = (comment.get("body") or "").strip()
        if body:
            bodies.append(body)
    return bodies


def fetch_open_issues(
    limit: int = 200,
    *,
    include_comments: bool = False,
    comment_limit: int = 3,
) -> list[IssueSnapshot]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--limit",
        str(limit),
        "--json",
        _ISSUE_FIELDS,
    ]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    snapshots = [_normalize_issue_item(item) for item in payload]
    if include_comments:
        for snapshot in snapshots:
            try:
                snapshot.comments = _fetch_issue_comments(snapshot.number, comment_limit=comment_limit)
            except subprocess.CalledProcessError:
                snapshot.comments = []
    return snapshots


def load_issue_snapshot(path: Path | str | None = None) -> list[IssueSnapshot]:
    target = Path(path) if path else DEFAULT_ISSUE_SNAPSHOT_PATH
    if not target.exists():
        return []
    payload = json.loads(target.read_text(encoding="utf-8"))
    return [_normalize_issue_item(item) for item in payload]


def save_issue_snapshot(
    issues: list[IssueSnapshot],
    path: Path | str | None = None,
) -> Path:
    target = Path(path) if path else DEFAULT_ISSUE_SNAPSHOT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    serializable = [
        {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "url": issue.url,
            "labels": issue.labels,
            "comments": issue.comments,
        }
        for issue in issues
    ]
    target.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
