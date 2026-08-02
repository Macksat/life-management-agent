from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.agentic_memory.models import AgenticMemoryEntry, MemoryDecision
from tools.agentic_memory.writers import apply_memory_decision


def _write_memory_file(path: Path, title: str, section: str, bullets: list[str]) -> None:
    lines = [
        f"# {title}",
        "",
        "最終更新: 2026-07-01",
        "",
        f"## {section}",
        "",
    ]
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.extend(
        [
            "",
            "---",
            "",
            "## 変更履歴",
            "",
            "| 日付 | 変更内容 |",
            "|------|----------|",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class AgenticMemoryWritersTests(unittest.TestCase):
    def test_apply_memory_decision_updates_existing_bullet(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = base / "preferences.md"
            _write_memory_file(path, "Preferences", "技術的な好み", ["Python を主軸にする"])
            entry = AgenticMemoryEntry(
                content="Python を主軸にしつつ AI エージェント開発を重視する",
                memory_type="preferences",
                target_section="技術的な好み",
            )
            decision = MemoryDecision(
                action="update_existing",
                target_path=str(path),
                target_section="技術的な好み",
                reason="update",
                matched_entry_id="pref-1",
                matched_text="Python を主軸にする",
                updated_text=entry.content,
            )
            changed = apply_memory_decision(entry, decision, base_dir=base)
            self.assertTrue(changed)
            content = path.read_text(encoding="utf-8")
            self.assertIn(entry.content, content)
            self.assertNotIn("- Python を主軸にする\n", content)

    def test_apply_memory_decision_adds_new_bullet(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = base / "facts.md"
            _write_memory_file(path, "Facts", "基本情報", ["GitHub Issue を使っている"])
            entry = AgenticMemoryEntry(
                content="ユーザー提供メモを取り込んで運用している",
                memory_type="facts",
                target_section="基本情報",
            )
            decision = MemoryDecision(
                action="add_new",
                target_path=str(path),
                target_section="基本情報",
                reason="new fact",
                updated_text=entry.content,
            )
            changed = apply_memory_decision(entry, decision, base_dir=base)
            self.assertTrue(changed)
            content = path.read_text(encoding="utf-8")
            self.assertIn("- ユーザー提供メモを取り込んで運用している", content)


if __name__ == "__main__":
    unittest.main()
