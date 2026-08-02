"""Safe writers for A-MEM style source updates."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tools.llm_wiki.paths import REPO_ROOT

from .models import AgenticMemoryEntry, MemoryDecision

MEMORY_FILE_MAP = {
    "preferences": "preferences.md",
    "facts": "facts.md",
    "decisions": "decisions.md",
}


def _resolve_base_dir(base_dir: Path | str | None = None) -> Path:
    if base_dir is None:
        return REPO_ROOT / "data" / "llm_wiki" / "sources" / "memories"
    return Path(base_dir)


def _target_path_for_memory_type(memory_type: str, *, base_dir: Path | str | None = None) -> Path:
    filename = MEMORY_FILE_MAP.get(memory_type)
    if filename is None:
        raise ValueError(f"Unsupported memory_type: {memory_type}")
    return _resolve_base_dir(base_dir) / filename


def _resolve_source_path(source_path: str) -> Path:
    path = Path(source_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / source_path


def _replace_first_matching_bullet(lines: list[str], matched_text: str, replacement: str) -> bool:
    target = f"- {matched_text}"
    for idx, line in enumerate(lines):
        if line.strip() == target:
            lines[idx] = f"- {replacement}"
            return True
    return False


def _insert_bullet_under_section(lines: list[str], section_name: str, content: str) -> bool:
    section_header = f"## {section_name}"
    for idx, line in enumerate(lines):
        if line.strip() != section_header:
            continue
        insert_at = idx + 1
        while insert_at < len(lines):
            current = lines[insert_at].strip()
            if current.startswith("## "):
                break
            insert_at += 1
        while insert_at > idx + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines.insert(insert_at, f"- {content}")
        return True
    return False


def _update_last_updated(lines: list[str]) -> None:
    today = date.today().isoformat()
    for idx, line in enumerate(lines):
        if line.startswith("最終更新: "):
            lines[idx] = f"最終更新: {today}"
            return


def _append_history_row(lines: list[str], detail: str) -> None:
    today = date.today().isoformat()
    for idx, line in enumerate(lines):
        if line.strip() == "| 日付 | 変更内容 |":
            insert_at = idx + 2
            lines.insert(insert_at, f"| {today} | {detail} |")
            return


def _replace_markdown_section(lines: list[str], heading: str, replacement_lines: list[str]) -> bool:
    target = f"## {heading}"
    for idx, line in enumerate(lines):
        if line.strip() != target:
            continue
        end = idx + 1
        while end < len(lines) and not lines[end].startswith("## "):
            end += 1
        lines[idx + 1 : end] = [""] + replacement_lines + [""]
        return True
    return False


def _replace_session_block(lines: list[str], heading: str, replacement_lines: list[str]) -> bool:
    target = f"### {heading}"
    for idx, line in enumerate(lines):
        if line.strip() != target:
            continue
        end = idx + 1
        while end < len(lines) and not lines[end].startswith("### ") and not lines[end].startswith("## Day Summary"):
            end += 1
        lines[idx + 1 : end] = [""] + replacement_lines + [""]
        return True
    return False


def _insert_session_block(lines: list[str], heading: str, block_lines: list[str]) -> bool:
    for idx, line in enumerate(lines):
        if line.strip() != "## Sessions":
            continue
        insert_at = idx + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## Day Summary"):
            insert_at += 1
        payload = ["", f"### {heading}", ""] + block_lines + [""]
        lines[insert_at:insert_at] = payload
        return True
    return False


def _block_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.strip().splitlines()] if text.strip() else []


def _apply_second_brain_decision(entry: AgenticMemoryEntry, decision: MemoryDecision) -> bool:
    if decision.action == "add_new":
        if not entry.source_path:
            raise ValueError("source_path is required for second_brain add_new")
        path = _resolve_source_path(entry.source_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((decision.updated_text or entry.content).rstrip() + "\n", encoding="utf-8")
        return True

    path = _resolve_source_path(decision.target_path)
    if not path.exists():
        raise FileNotFoundError(f"Digest file not found: {path}")
    replacement_lines = _block_lines(decision.updated_text or entry.content)
    lines = path.read_text(encoding="utf-8").splitlines()
    if entry.target_section and _replace_markdown_section(lines, entry.target_section, replacement_lines):
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    path.write_text((decision.updated_text or entry.content).rstrip() + "\n", encoding="utf-8")
    return True


def _apply_conversation_decision(entry: AgenticMemoryEntry, decision: MemoryDecision) -> bool:
    target_path = entry.source_path or decision.target_path
    if not target_path:
        raise ValueError("source_path is required for conversation_memory writes")
    path = _resolve_source_path(target_path)
    if not path.exists():
        raise FileNotFoundError(f"Conversation memory file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    replacement_lines = _block_lines(decision.updated_text or entry.content)
    if decision.action == "update_existing":
        changed = _replace_session_block(lines, decision.target_section or entry.target_section, replacement_lines)
    else:
        changed = _insert_session_block(lines, decision.target_section or entry.target_section, replacement_lines)
    if not changed:
        raise ValueError(f"Could not apply conversation memory decision to section: {decision.target_section or entry.target_section}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def apply_memory_decision(
    entry: AgenticMemoryEntry,
    decision: MemoryDecision,
    *,
    base_dir: Path | str | None = None,
) -> bool:
    if decision.action in {"skip_duplicate", "strengthen_link", "update_neighbor"}:
        return False

    if entry.layer == "second_brain":
        return _apply_second_brain_decision(entry, decision)
    if entry.layer == "conversation_memory":
        return _apply_conversation_decision(entry, decision)

    path = _target_path_for_memory_type(entry.memory_type, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Memory file not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False

    if decision.action == "update_existing":
        replacement = decision.updated_text or entry.content
        changed = _replace_first_matching_bullet(lines, decision.matched_text, replacement)
        if not changed:
            changed = _insert_bullet_under_section(lines, decision.target_section or entry.target_section, replacement)
        detail = f"{entry.memory_type} の既存項目を更新: {decision.target_section or entry.target_section}"
    else:
        changed = _insert_bullet_under_section(lines, decision.target_section or entry.target_section, decision.updated_text or entry.content)
        detail = f"{entry.memory_type} に新規項目を追加: {decision.target_section or entry.target_section}"

    if not changed:
        raise ValueError(f"Could not apply decision to section: {decision.target_section or entry.target_section}")

    _update_last_updated(lines)
    _append_history_row(lines, detail)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True
