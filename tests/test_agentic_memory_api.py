from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from tools.agentic_memory.api import preview_memory_entry, process_memory_entry
from tools.agentic_memory.models import AgenticMemoryEntry


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


class AgenticMemoryApiTests(unittest.TestCase):
    def test_preview_only_writes_audit_log(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "sources"
            base.mkdir(parents=True, exist_ok=True)
            _write_memory_file(base / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(base / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(base / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="Python を主軸にしつつ AI エージェント開発を重視する",
                memory_type="preferences",
                target_section="技術的な好み",
            )
            candidate_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]
            with patch(
                "tools.agentic_memory.retrieval.get_embeddings",
                side_effect=[candidate_embeddings, query_embedding],
            ):
                result = preview_memory_entry(entry, base_dir=base, root=Path(tmpdir), top_k=10)

            self.assertFalse(result.changed)
            self.assertTrue(Path(result.audit_path).exists())
            content = (base / "preferences.md").read_text(encoding="utf-8")
            self.assertNotIn(entry.content, content)

    def test_process_memory_entry_updates_file_and_logs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "sources"
            base.mkdir(parents=True, exist_ok=True)
            _write_memory_file(base / "preferences.md", "Preferences", "技術的な好み", ["Python を主軸にする"])
            _write_memory_file(base / "facts.md", "Facts", "基本情報", ["サンプル地域に住んでいる"])
            _write_memory_file(base / "decisions.md", "Decisions", "技術・設計", ["Issue 中心で運用する"])

            entry = AgenticMemoryEntry(
                content="Python を主軸にしつつ AI エージェント開発を重視する",
                memory_type="preferences",
                target_section="技術的な好み",
            )

            fake_candidate_embeddings = [
                np.array([1.0] + [0.0] * 1535, dtype=np.float32),
            ]
            query_embedding = [np.array([1.0] + [0.0] * 1535, dtype=np.float32)]

            def judge(_: AgenticMemoryEntry, candidates):
                return {
                    "action": "update_existing",
                    "matched_entry_id": candidates[0].entry_id,
                    "reason": "same topic, richer wording",
                    "updated_text": entry.content,
                }

            with patch(
                "tools.agentic_memory.retrieval.get_embeddings",
                side_effect=[fake_candidate_embeddings, query_embedding],
            ):
                result = process_memory_entry(
                    entry,
                    base_dir=base,
                    root=Path(tmpdir),
                    top_k=10,
                    judge=judge,
                )

            self.assertTrue(result.changed)
            updated = (base / "preferences.md").read_text(encoding="utf-8")
            self.assertIn(entry.content, updated)

            audit_path = Path(result.audit_path)
            records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(1, len(records))
            self.assertEqual("update_existing", records[0]["decision"]["action"])


if __name__ == "__main__":
    unittest.main()
