#!/usr/bin/env python3
"""Extract GitHub Issue candidates from second_brain digests."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DIGEST_ROOT = REPO_ROOT / "data" / "llm_wiki" / "sources" / "second_brain" / "digests"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "llm_wiki" / "sources" / "second_brain" / "issue_candidates" / "latest.json"

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
META_RE = re.compile(r"^- \*\*(.+?)\*\*:\s*(.+?)\s*$|^- \*\*(.+?):\*\*\s*(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^- \[\s\]\s+(.+?)\s*$")


@dataclass
class IssueCandidate:
    candidate_id: str
    title: str
    source_digest_path: str
    source_digest_title: str
    source_source_name: str
    source_date: str
    candidate_type: str
    risk_level: str
    why_issue: str
    goal: str
    next_action: str
    ideal: str
    current: str
    problem: str
    approach: str
    suggested_category: list[str]
    suggested_priority: str
    suggested_status: str
    approval_required: bool
    dedupe_query: str
    acceptance_criteria: list[str]
    context: str
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract GitHub Issue candidates from second_brain digests.")
    parser.add_argument("paths", nargs="*", help="Digest files or directories. Defaults to all digest markdown files.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write JSON candidates.")
    parser.add_argument("--limit", type=int, default=0, help="Max number of candidates to emit. 0 means no limit.")
    parser.add_argument("--print", action="store_true", dest="print_summary", help="Print a human summary.")
    return parser.parse_args()


def resolve_digest_paths(inputs: list[str]) -> list[Path]:
    if not inputs:
        return sorted(DIGEST_ROOT.glob("*.md"))

    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if path.is_dir():
            paths.extend(sorted(path.glob("*.md")))
        else:
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def parse_digest(path: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    meta: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current_section = "_preamble"
    sections[current_section] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
            continue
        meta_match = META_RE.match(line)
        if meta_match:
            key = meta_match.group(1) or meta_match.group(3)
            value = meta_match.group(2) or meta_match.group(4)
            meta[key.strip()] = value.strip()
            continue
        section_match = SECTION_RE.match(line)
        if section_match:
            current_section = section_match.group(1).strip()
            sections.setdefault(current_section, [])
            continue
        sections.setdefault(current_section, [])
        sections[current_section].append(line)
    return meta, sections


def extract_bullets(lines: Iterable[str], checkbox_only: bool = False) -> list[str]:
    items: list[str] = []
    for line in lines:
        if checkbox_only:
            match = CHECKBOX_RE.match(line)
            if match:
                items.append(match.group(1).strip())
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def choose_category(text: str) -> list[str]:
    lowered = text.lower()
    if any(word in text for word in ["運動", "脂肪", "飲酒", "ラン", "健康", "バーピー", "睡眠"]):
        return ["health"]
    if any(word in text for word in ["家事", "生活", "口座", "手続き", "研修", "入金", "精算"]):
        return ["life-admin"]
    if any(word in text for word in ["AI", "スマホ", "デバイス", "ガジェット"]):
        return ["gadget"]
    if any(word in text for word in ["残業", "仕事", "研修"]):
        return ["work"]
    if any(word in text for word in ["外食", "飲食", "映画", "寿司", "お好み焼き", "候補"]):
        return ["life-admin"]
    if any(word in lowered for word in ["issue", "workflow", "repo", "llm wiki"]):
        return ["meta-system"]
    return ["thinking"]


def choose_type(text: str, category: list[str]) -> str:
    if category == ["health"] and any(word in text for word in ["頻度", "運動", "飲酒", "見直す", "始め方"]):
        return "habit"
    if any(word in text for word in ["方針", "メモ", "整理"]):
        return "memo"
    if any(word in text for word in ["調べる", "確認", "方法"]):
        return "research"
    if any(word in text for word in ["改善", "増やす", "減らす", "見直す"]):
        return "improvement"
    return "task"


def choose_risk(text: str, category: list[str]) -> str:
    if any(word in text for word in ["口座", "入金", "送金", "精算", "金額", "支払い"]):
        return "high"
    if "パートナー" in text or category == ["relationship"]:
        return "medium"
    return "low"


def compress_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_goal(action: str) -> str:
    if action.endswith("を考える"):
        return f"{action[:-4]}方針と次の打ち手が整理されている状態にする"
    if action.endswith("を決める"):
        return f"{action[:-4]}内容を決めて実行に移せる状態にする"
    if action.endswith("を見直す"):
        return f"{action[:-5]}内容を見直し、次の改善行動が決まっている状態にする"
    return f"{action}こと"


def slugify(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-zぁ-んァ-ン一-龥]+", "-", text).strip("-").lower()
    return slug or "candidate"


def build_candidates_for_digest(path: Path) -> list[IssueCandidate]:
    meta, sections = parse_digest(path)
    title = meta.get("title", path.stem)
    actions = extract_bullets(sections.get("アクション項目", []), checkbox_only=True)
    insights = extract_bullets(sections.get("重要な洞察・気づき", []))
    facts = extract_bullets(sections.get("事実情報", []))
    decisions = extract_bullets(sections.get("意思決定・判断", []))

    candidates: list[IssueCandidate] = []
    for idx, action in enumerate(actions, start=1):
        if action in {"なし", "無し", "特になし"}:
            continue
        category = choose_category(f"{title} {action}")
        candidate_type = choose_type(action, category)
        risk = choose_risk(f"{title} {action}", category)
        insight = insights[min(idx - 1, len(insights) - 1)] if insights else ""
        fact = facts[min(idx - 1, len(facts) - 1)] if facts else ""
        decision = decisions[min(idx - 1, len(decisions) - 1)] if decisions else ""
        goal = build_goal(action)
        context_parts = [
            f"second_brain digest: {title}",
            f"source: {meta.get('ソース', path.name)}",
        ]
        if insight:
            context_parts.append(f"insight: {compress_text(insight)}")
        if decision:
            context_parts.append(f"decision: {compress_text(decision)}")

        if candidate_type in {"task", "improvement", "habit"}:
            ideal = goal
            current = fact or compress_text(f"{title} に関する会話の中で、まだ具体的な計画や運用が固まっていない。")
            problem = insight or compress_text(f"{goal} に対して、実行計画や判断基準が未整理なままになっている。")
            approach = action
        else:
            ideal = goal
            current = fact or ""
            problem = insight or ""
            approach = action

        acceptance = []
        if candidate_type in {"task", "improvement", "habit"}:
            acceptance = [
                f"{action}に関する next_action が 1 つ以上決まっている",
                "関連する判断や前提が Issue 本文に記録されている",
            ]

        candidate = IssueCandidate(
            candidate_id=f"{path.stem}-{idx}",
            title=action,
            source_digest_path=str(path.relative_to(REPO_ROOT)),
            source_digest_title=title,
            source_source_name=meta.get("ソース", path.name),
            source_date=meta.get("日時", ""),
            candidate_type=candidate_type,
            risk_level=risk,
            why_issue="second_brain のダイジェストに具体的な次の行動として記録されており、後で実行・追跡する価値があるため。",
            goal=goal,
            next_action=action,
            ideal=ideal,
            current=current,
            problem=problem,
            approach=approach,
            suggested_category=category,
            suggested_priority="P2-medium",
            suggested_status="inbox",
            approval_required=risk != "low",
            dedupe_query=compress_text(action),
            acceptance_criteria=acceptance,
            context=" / ".join(context_parts),
            notes=f"generated_from={path.name}",
        )
        candidates.append(candidate)
    return candidates


def main() -> int:
    args = parse_args()
    digest_paths = resolve_digest_paths(args.paths)
    candidates: list[IssueCandidate] = []
    for path in digest_paths:
        candidates.extend(build_candidates_for_digest(path))

    if args.limit > 0:
        candidates = candidates[: args.limit]

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(candidate) for candidate in candidates]
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.print_summary:
        print(f"Extracted {len(candidates)} candidates -> {output_path.relative_to(REPO_ROOT)}")
        for candidate in candidates:
            print(
                f"- [{candidate.risk_level}] {candidate.title} "
                f"(type={candidate.candidate_type}, category={','.join(candidate.suggested_category)})"
            )
    else:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
