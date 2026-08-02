#!/usr/bin/env python3
"""Create GitHub Issues from extracted second_brain candidates."""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = REPO_ROOT / "data" / "llm_wiki" / "sources" / "second_brain" / "issue_candidates" / "latest.json"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.llm_wiki.issues import fetch_open_issues, load_issue_snapshot, save_issue_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create GitHub Issues from second_brain candidates.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES), help="Candidate JSON path.")
    parser.add_argument("--execute", action="store_true", help="Actually create GitHub Issues. Default is dry-run.")
    parser.add_argument("--refresh-issues", action="store_true", help="Refresh open issue snapshot with gh issue list.")
    parser.add_argument("--include-high-risk", action="store_true", help="Allow high-risk candidates to be created.")
    parser.add_argument("--limit", type=int, default=0, help="Max number of candidates to process. 0 means no limit.")
    parser.add_argument("--report-out", default="", help="Optional JSON report output path.")
    return parser.parse_args()


def load_candidates(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Candidate JSON must be an array")
    return payload


def normalize(text: str) -> str:
    text = text.lower()
    for ch in " 　-_:/()[]{}#.,。、「」・":
        text = text.replace(ch, "")
    return text


def find_duplicate(candidate: dict, issues: list) -> object | None:
    target = normalize(candidate["title"])
    query = normalize(candidate.get("dedupe_query", ""))
    for issue in issues:
        title_score = difflib.SequenceMatcher(None, target, normalize(issue.title)).ratio()
        if title_score >= 0.82:
            return issue
        hay = normalize(issue.title + "\n" + issue.body)
        if query and query in hay:
            return issue
    return None


def build_issue_body(candidate: dict) -> str:
    lines = []
    if candidate["candidate_type"] in {"task", "improvement", "habit"}:
        lines.extend(
            [
                "## 理想",
                candidate.get("ideal", candidate["goal"]),
                "",
                "## 現状",
                candidate.get("current", ""),
                "",
                "## 問題点",
                candidate.get("problem", ""),
                "",
                "## 方針",
                candidate.get("approach", candidate["next_action"]),
                "",
            ]
        )

    lines.extend(
        [
            "## Goal",
            candidate["goal"],
            "",
            "## Context",
            candidate.get("context", ""),
            "",
            "## Next Action",
            candidate["next_action"],
            "",
        ]
    )

    acceptance = candidate.get("acceptance_criteria") or []
    if acceptance:
        lines.append("## Acceptance Criteria")
        for item in acceptance:
            lines.append(f"- [ ] {item}")
        lines.append("")

    lines.extend(
        [
            "## Source",
            f"- digest: {candidate['source_digest_title']}",
            f"- path: {candidate['source_digest_path']}",
            f"- source_file: {candidate.get('source_source_name', '')}",
            f"- source_date: {candidate.get('source_date', '')}",
            "",
            "## Notes",
            candidate.get("notes", ""),
            "",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_labels(candidate: dict) -> list[str]:
    category = candidate["suggested_category"][0]
    return [
        f"category:{category}",
        f"type:{candidate['candidate_type']}",
        f"status:{candidate['suggested_status']}",
        f"priority:{candidate['suggested_priority']}",
    ]


def create_issue(candidate: dict) -> tuple[int, str]:
    body = build_issue_body(candidate)
    labels = build_labels(candidate)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        tmp.write(body)
        tmp_path = Path(tmp.name)

    try:
        cmd = ["gh", "issue", "create", "--title", candidate["title"], "--body-file", str(tmp_path)]
        for label in labels:
            cmd.extend(["--label", label])
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    url = result.stdout.strip().splitlines()[-1].strip()
    number = int(url.rstrip("/").split("/")[-1])
    return number, url


def append_issue_link_to_digest(candidate: dict, number: int, url: str) -> None:
    digest_path = REPO_ROOT / candidate["source_digest_path"]
    text = digest_path.read_text(encoding="utf-8")
    heading = "## 関連Issue"
    entry = f"- #{number} {candidate['title']} ({url})"
    if entry in text:
        return
    if heading in text:
        updated = text.rstrip() + "\n" + entry + "\n"
    else:
        updated = text.rstrip() + "\n\n" + heading + "\n\n" + entry + "\n"
    digest_path.write_text(updated, encoding="utf-8")


def maybe_refresh_issues(refresh: bool) -> list:
    if refresh:
        issues = fetch_open_issues()
        save_issue_snapshot(issues)
        return issues
    return load_issue_snapshot()


def main() -> int:
    args = parse_args()
    candidate_path = Path(args.candidates)
    if not candidate_path.is_absolute():
        candidate_path = REPO_ROOT / candidate_path

    candidates = load_candidates(candidate_path)
    if args.limit > 0:
        candidates = candidates[: args.limit]

    issues = maybe_refresh_issues(args.refresh_issues)
    report: list[dict] = []

    for candidate in candidates:
        if candidate["risk_level"] == "high" and not args.include_high_risk:
            report.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "title": candidate["title"],
                    "status": "skipped_high_risk",
                }
            )
            continue

        duplicate = find_duplicate(candidate, issues)
        if duplicate is not None:
            report.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "title": candidate["title"],
                    "status": "duplicate",
                    "duplicate_issue_number": duplicate.number,
                    "duplicate_issue_url": duplicate.url,
                }
            )
            continue

        if not args.execute:
            report.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "title": candidate["title"],
                    "status": "dry_run_ready",
                    "labels": build_labels(candidate),
                    "body_preview": build_issue_body(candidate),
                }
            )
            continue

        number, url = create_issue(candidate)
        candidate["created_issue_number"] = number
        candidate["created_issue_url"] = url
        append_issue_link_to_digest(candidate, number, url)
        report.append(
            {
                "candidate_id": candidate["candidate_id"],
                "title": candidate["title"],
                "status": "created",
                "issue_number": number,
                "issue_url": url,
            }
        )

    candidate_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.report_out:
        report_path = Path(args.report_out)
        if not report_path.is_absolute():
            report_path = REPO_ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for item in report:
        title = item["title"]
        status = item["status"]
        if status == "created":
            print(f"[created] {title} -> #{item['issue_number']} {item['issue_url']}")
        elif status == "duplicate":
            print(f"[duplicate] {title} -> #{item['duplicate_issue_number']} {item['duplicate_issue_url']}")
        elif status == "dry_run_ready":
            print(f"[dry-run] {title}")
        else:
            print(f"[{status}] {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
